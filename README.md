# scrapiq-bench

A small, reproducible benchmark of **URL → clean markdown** for LLM/RAG ingestion,
run against real pages on the live web. It measures four tools plus a raw-HTML
baseline:

| tool | what it is |
|---|---|
| `raw HTML` | the baseline: what `httpx.get(url).text` gives you |
| `trafilatura` | `trafilatura.extract(...)`, called with **exactly the kwargs Scrapiq uses internally** |
| `Scrapiq API` | `POST /v1/extract` against a locally self-hosted Scrapiq (`v0.1.0`) |
| `readability-lxml` | `readability.Document` + `html2text` |
| `MarkItDown` | `MarkItDown().convert_stream(...)` on the fetched HTML |

Two page sets, 23 pages that answered:

- **set 1** — the original 12 (docs, encyclopedia, repo, package registry, blog
  index, forum, product docs, news front, book page, landing page). Ran on
  2026-09-12 **and again on 2026-09-13** as a reproducibility check.
- **set 2** — 12 more archetypes (licence text, a government organisation page, a
  preprint abstract, a Q&A page, an e-commerce product page, a language spec, a
  changelog, a static blog index, a source-repository landing page, tutorial docs,
  a long-form essay, a client-rendered docs site). One of the twelve
  (Stack Overflow) refused a plain fetch and is reported as a boundary, not a score.

Numbers live in **[RESULTS.md](RESULTS.md)** and the raw per-run JSON is committed
next to it (`results-2026-09-12.json`, `results-2026-09-13.json`,
`results-2026-09-13-set2.json`). Nothing is hand-transcribed: `bench.py` collects,
`emit_results.py` renders.

## Disclosure first: Scrapiq wraps trafilatura

This is the honest starting point, and it's why the benchmark calls the
trafilatura baseline with the same options Scrapiq passes
(`include_links=True, include_images=False, include_tables=True,
output_format="markdown", with_metadata=False` — see
[`src/extract.py`](https://github.com/NG-PR0JECT/scrapiq/blob/main/src/extract.py)).

So this is not "Scrapiq's parser beats trafilatura's parser". It's the same
parser. The delta measured here is what the API layer adds on top of it — plus a
BeautifulSoup fallback that runs when trafilatura returns empty, and a
link-recovery pass over anchors the extractor dropped.

## What the numbers say

Medians over the 23 pages that answered (full per-page tables in
[RESULTS.md](RESULTS.md)):

| tool | cold ms | median chars | median links | avg boilerplate markers | broken link targets | near-empty pages |
|---|---:|---:|---:|---:|---:|---:|
| raw HTML | 97 | 105,845 | 0 | 2.1 | 0 | 0/23 |
| trafilatura | 253 | 4,449 | 5 | 0.2 | 2 | 1/23 |
| Scrapiq API | 411 | 6,648 | 6 | 0.3 | 2 | 0/23 |
| readability-lxml | 217 | 3,814 | 1 | 0.2 | 0 | **2/23** |
| MarkItDown | 414 | 17,205 | 34 | 1.9 | 8 | 0/23 |

1. **The bare library call silently returns nothing on 1 of 23 pages.** On the
   Apache licence page, `trafilatura.extract(...)` with these exact kwargs returns
   **0 characters** — no error, no warning. Scrapiq returns **9,354** because its
   BeautifulSoup fallback fires. Same call, same input, and one of them gives you
   an empty document that looks like a successful extraction.
2. **readability-lxml returned under 200 characters on 2/23 pages** — a forum front
   page (**1 char**) and a news front (181 chars) — and never raised an error. It
   is the second-fastest tool and the one that fails without telling you.
3. **MarkItDown keeps the chrome with the content.** 4/23 pages carry 4+ boilerplate
   markers (`cookie`, `sign in`, `subscribe`, `privacy policy`, …) in its output,
   against 0 for Scrapiq — e.g. 8 markers and 58,237 chars on a news front vs 0
   markers and 4,068 chars for Scrapiq. It also produced 8 structurally broken link
   targets across the set, against 2 for trafilatura and 2 for Scrapiq.
4. **Scrapiq returned at least as much text as the same-kwargs library on 23/23
   pages, and strictly more on 17/23** (median +70 characters, largest +9,354). The
   useful framing is not "more text is better" — it is that on the pages where the
   parser gives up, the API still hands you the page.
5. **The API layer costs roughly +0.16 s of median latency** over the library path
   (411 ms cold vs 253 ms), which is the HTTP round trip plus the server-side fetch.
   Raw HTML is ~24× the size of the cleaned output (105,845 → 6,648 median chars);
   at ~4 chars/token that is the difference between ~26k and ~1.7k tokens per page,
   before any chunking.
6. **All tools produced byte-identical output across their two runs on all 23
   pages**, so run-to-run instability was not observable here (single machine,
   within a minute, no A/B deploys in flight — not proof of long-term stability).

## Reproducibility: the same 12 pages, 24 hours apart

Set 1 was run twice. On 7/12 pages Scrapiq's output was byte-for-byte identical the
next day. The five that moved are pages whose *content* changed overnight: four live
front/index pages (Wikipedia edits, Hacker News, a blog index, a news front) and
this project's own repository page, which we edited the day before. The ranking of
the tools was identical on both days.

Latency, on the other hand, is the noisy part: day 2 was slower across the board for
every tool (e.g. trafilatura 188 → 470 ms median), which is network conditions, not
code. Treat the latency tables as one measurement, not as a constant. Full day-1 vs
day-2 comparison in [RESULTS.md](RESULTS.md).

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
~23,000 chars of clean markdown with 0 broken link targets, and the case is pinned
by regression tests.

## When to use what

- **You want the article text only, fast, and you're fine with a dependency:**
  trafilatura. It is the best boilerplate remover in this comparison, and it is
  what Scrapiq runs underneath — but check that you got something back, because on
  the licence page above it returned nothing at all.
- **You want the page's link structure preserved:** MarkItDown keeps 34 links
  median vs 6 for Scrapiq — at the price of the surrounding chrome (1.9 boilerplate
  markers per page vs 0.3).
- **You want a fast main-article read on generic pages:** readability is the
  quickest, but verify the output — it silently returned ~nothing on 2/23 pages here.
- **You want one deterministic call from a pipeline, with metadata and a stable
  contract:** Scrapiq. It adds a metadata block (title/description/author/publish
  date/language/canonical/word count), schema-constrained JSON output, timeouts,
  size limits, retries, a fallback when the parser returns empty, and it self-hosts
  with one Docker command — which matters when the alternative is running extraction
  inside every service that needs a page. Cost: roughly +0.16 s and one network hop.

## Reproduce it

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install trafilatura readability-lxml markitdown html2text httpx

# start a Scrapiq instance (or point SCRAPIQ at a hosted one) and make sure
# POST http://localhost:8001/v1/extract answers /health first
python bench.py --set 1 --stamp 2026-09-13 --out results-2026-09-13.json
python bench.py --set 2 --stamp 2026-09-13 --out results-2026-09-13-set2.json
python emit_results.py   # renders RESULTS.md from the committed JSON
```

`pages.py` holds both page sets (`PAGE_SET_1`, `PAGE_SET_2`) and `bench.py` holds
the boilerplate-marker heuristic — edit both to benchmark your own URLs.
`retry_page.py <results.json> <url> [replacement_url]` re-measures a single page
(e.g. one that timed out) without re-running the whole set.

## Caveats

- **23 pages, one machine, two dates.** Treat it as a spot check, not a ranking.
  The pages are deliberately mixed across archetypes, but they are not a random
  sample of the web.
- **Everything is fetch-based.** No tool here executes JavaScript, so JS-only pages
  are thin for all of them. Stack Overflow refused the plain fetch outright (403)
  and is reported as a refusal rather than scored zero — anti-bot behaviour is a
  real boundary of this approach and nothing here claims to solve it.
- **`boilerplate markers` is a crude heuristic** (a lowercased substring count of
  `cookie`, `sign in`, `subscribe`, `privacy policy`, …). It flags chrome leaking
  into the body. It is not a content-quality score.
- **Bigger is not better.** A tool that keeps 17k chars is not three times better
  than one that keeps 6k; it mostly means less was thrown away. Read the per-page
  table, not just the medians.
- **Latency numbers include network fetch time**, which varies with the target site,
  the machine and the day — the day-1/day-2 table shows how much. Run it on your
  own hardware if the timing matters to you.
- **The Scrapiq column is measured with the API's cache in play for the second of
  the two runs per page.** `RESULTS.md` reports the first (cold) call separately for
  that reason.

Scrapiq is MIT-licensed: https://github.com/NG-PR0JECT/scrapiq
