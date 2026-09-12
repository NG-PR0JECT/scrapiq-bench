# scrapiq-bench

A small, reproducible benchmark of **URL → clean markdown** for LLM/RAG ingestion,
run against 12 real pages. It measures four tools plus a raw-HTML baseline:

| tool | what it is |
|---|---|
| `raw HTML` | the baseline: what `httpx.get(url).text` gives you |
| `trafilatura` | `trafilatura.extract(...)`, called with **exactly the kwargs Scrapiq uses internally** |
| `Scrapiq API` | `POST /v1/extract` against a locally self-hosted Scrapiq (`v0.1.0`) |
| `readability-lxml` | `readability.Document` + `html2text` |
| `MarkItDown` | `MarkItDown().convert_stream(...)` on the fetched HTML |

Numbers live in **[RESULTS.md](RESULTS.md)** and the raw per-run JSON is in
`results.json`. Nothing is hand-transcribed: `bench.py` collects, `emit_results.py`
renders the tables.

## Disclosure first: Scrapiq wraps trafilatura

This is the honest starting point, and it's why the benchmark calls the
trafilatura baseline with the same options Scrapiq passes
(`include_links=True, include_images=False, include_tables=True,
output_format="markdown", with_metadata=False` — see
[`src/extract.py`](https://github.com/NG-PR0JECT/scrapiq/blob/main/src/extract.py)).

So this is not "Scrapiq's parser beats trafilatura's parser". It's the same
parser. The delta measured here is what the API layer adds on top of it.

## What the numbers say

Medians over the 12 pages (full tables in [RESULTS.md](RESULTS.md)):

| tool | median ms | median chars | median links | avg boilerplate markers | broken link targets | near-empty pages |
|---|---:|---:|---:|---:|---:|---:|
| raw HTML | 75 | 119,682 | 0 | 2.4 | 0 | 0/12 |
| trafilatura | 188 | 3,840 | 4 | 0.2 | 0 | 0/12 |
| Scrapiq API | 424 | 5,158 | 8 | 0.2 | 0 | 0/12 |
| readability-lxml | 168 | 2,383 | 0 | 0.2 | 0 | **2/12** |
| MarkItDown | 352 | 24,354 | 54 | 2.2 | 0 | 0/12 |

1. **Scrapiq returned at least as much text as the bare library on 12/12 pages.**
   The biggest recovery is a forum front page: **+2,876 chars and +32 links** that
   trafilatura dropped, because Scrapiq re-attaches anchors the extractor skipped.
2. **The cost of the service layer is ~0.24 s of median latency** (424 ms vs
   188 ms), which is the HTTP round trip plus the server-side fetch.
3. **readability-lxml returned nothing useful on 2/12 pages** (1 char on a forum
   front page, 181 chars on a news front). It is the fastest, and also the one
   that silently fails.
4. **MarkItDown keeps the most text and the most chrome** — 24k median chars and
   2.2 boilerplate markers per page (`cookie`, `sign in`, `subscribe`, …) against
   0.2 for trafilatura/Scrapiq/readability. It is a document converter doing a
   web page's job; the structure comes through, the nav does too.
5. **All four tools produced byte-identical output across two runs** on all 12
   pages, so run-to-run instability was not observable here (single machine,
   within a minute, no A/B deploys in flight — not proof of long-term stability).
6. **Raw HTML is ~23× the size of the cleaned output** (119,682 → 5,158 median
   chars). At ~4 chars/token that is roughly the difference between 30k and 1.3k
   tokens per page, before any chunking.

## The benchmark found a real bug in Scrapiq

The first run, before any fix, produced this from the Wikipedia article on RAG:

```
# R[e](h[t](https://en.wikipedia.org/wiki/Template_talk:Artificial_intelligence_navbox)tps://en.wikipedia.org/wiki/Special:EditPage/...
```

79 structurally broken link targets on that page alone. Root cause: Wikipedia's
navbox anchors carry 1–3 character labels (`R`, `e`, `AI`, `t`), and Scrapiq's
markdown link-recovery pass matched them as substrings **inside** already-correct
links and URLs, then spliced them with `str.replace`.

Fixed the same day
([`7775cca`](https://github.com/NG-PR0JECT/scrapiq/commit/7775cca)) by refusing to
inject labels shorter than 4 chars and refusing to inject at any position that
falls inside an existing `[label](url)` or bare URL. The same page now returns
22,737 chars of clean markdown with 0 broken link targets, and the case is pinned
by regression tests. This is the main reason `malformed link targets` reads 0 in
the tables above — before the fix it read 79.

## When to use what

- **You want the article text only, fast, and you're fine with a dependency:**
  trafilatura. It is the best boilerplate remover in this comparison, and it is
  what Scrapiq runs underneath.
- **You want the page's link structure preserved:** MarkItDown keeps 54 links
  median vs 8 for Scrapiq's markdown — at the price of the surrounding chrome.
- **You want a fast main-article read on generic pages:** readability is the
  quickest, but check that you got something — it silently returned ~nothing on
  2/12 pages here.
- **You want one deterministic call from a pipeline, with metadata and a stable
  contract:** Scrapiq. It adds a metadata block (title/description/author/
  publish date/language/canonical/word count), schema-constrained JSON output,
  timeouts, size limits, retries, and it self-hosts with one Docker command —
  which matters when the alternative is running extraction inside every service
  that needs a page. Cost: roughly +0.24 s and one network hop per page.

## Reproduce it

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install trafilatura readability-lxml markitdown html2text httpx

# start a Scrapiq instance (or point SCRAPIQ at a hosted one) and make sure
# POST http://localhost:8001/v1/extract answers /health first
python bench.py          # writes results.json
python emit_results.py   # renders RESULTS.md from results.json
```

`bench.py` holds the page list and the boilerplate-marker heuristic — edit both
to benchmark your own URLs.

## Caveats

- **12 pages, one machine, one hour, one date.** Treat it as a spot check, not a
  ranking. The pages are deliberately mixed (docs, encyclopedia, repo, registry,
  blog, forum, product docs, news front, book page, landing page) but they are
  not a random sample of the web.
- **Everything is fetch-based.** No tool here executes JavaScript, so JS-only
  pages are thin for all of them, and nothing here measures anti-bot behaviour —
  none of these 12 pages blocked any tool.
- **`boilerplate markers` is a crude heuristic** (a lowercased substring count of
  `cookie`, `sign in`, `subscribe`, `privacy policy`, …). It flags chrome leaking
  into the body. It is not a content-quality score.
- **Bigger is not better.** A tool that keeps 24k chars is not four times better
  than one that keeps 5k; it mostly means less was thrown away. Read the
  per-page table, not just the medians.
- Latency numbers include network fetch time, which varies with the target site
  and the machine. Run it on your own hardware if the timing matters to you.

Scrapiq is MIT-licensed: https://github.com/NG-PR0JECT/scrapiq
