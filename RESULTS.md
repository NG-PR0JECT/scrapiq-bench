# Results

Every number below is generated from the time-stamped JSON sitting next to this
file: `bench.py` collects, `emit_results.py` renders. Nothing is transcribed by hand.

| run | set | date | pages that answered | pages that blocked a plain fetch |
|---|---|---|---:|---:|
| set 1, day 1 | 1 | 2026-09-12 | 12 | 0 |
| set 1, day 2 (re-run) | 1 | 2026-09-13 | 12 | 0 |
| set 2, day 1 | 2 | 2026-09-13 | 11 | 1 |

All runs: one machine in Europe/Paris, against the live web and a locally
self-hosted Scrapiq API (`v0.1.0`, `http://localhost:8001`). Every tool runs twice
per page: the first run supplies the content, both runs supply the latency, and the
two outputs are hashed against each other for the stability column.

Pages that did not answer a plain fetch, and are therefore excluded from every
table below rather than scored zero (this is a boundary of a fetch-based
approach, not a comparative result):

- `stackoverflow.com/questions/11227809/why-is-processi` — HTTPStatusError: Client error '403 Forbidden'

## Reproducibility: set 1 run twice, 24 hours apart

Same 12 URLs, same machine, same tool versions.

| tool | day 1 median ms | day 2 median ms | day 1 median chars | day 2 median chars |
|---|---:|---:|---:|---:|
| raw HTML | 75 | 113 | 119,682 | 119,682 |
| trafilatura (same kwargs) | 188 | 470 | 3,840 | 4,146 |
| Scrapiq API | 424 | 526 | 5,158 | 5,590 |
| readability-lxml | 168 | 250 | 2,383 | 2,806 |
| MarkItDown | 352 | 416 | 24,354 | 24,354 |

Scrapiq's extracted text is **byte-for-byte identical across the two days on 7/12 pages**. The 5 that moved are pages whose underlying
content changed between the runs — four of them are live front/index pages
(Wikipedia edits, Hacker News front page, a blog index, a news front) and one is
our own repository page, which we edited the day before:

- `en.wikipedia.org/wiki/Retrieval-augmented_generation` — 22,737 → 23,322 chars
- `github.com/NG-PR0JECT/scrapiq` — 3,669 → 4,531 chars
- `simonwillison.net` — 27,152 → 26,915 chars
- `news.ycombinator.com` — 6,970 → 7,124 chars
- `www.theguardian.com/international` — 2,620 → 4,068 chars

So the *tool comparison* reproduces; the *content of dated index pages* does not,
and no extraction tool can change that. The ranking of the tools is identical on
both days.

Latency is the noisy part: day 2 is slower across the board for every tool and
every page (network conditions, not code). Read the cold-call table further down
as one measurement, not as a constant.

## Set 2 — twelve archetypes set 1 did not cover

Chosen to test the cases a pipeline actually meets rather than more docs pages:
licence text, a government organisation page, a preprint abstract, a Q&A page,
an e-commerce product page, a language spec, a changelog, a static blog index, a
source-repository landing page, tutorial docs, a long-form essay, and a modern
client-rendered docs site.

| page | kind | raw HTML | raw HTML chars · ms | trafilatura (same kwargs) chars · ms | Scrapiq API chars · ms | readability-lxml chars · ms | MarkItDown chars · ms |
|---|---|---:|---:|---:|---:|---:|---:|
| `www.apache.org/licenses/LICENSE-2.0` | license text | 11,358 B | 11,358 · 64 | 0 · 65 | 9,354 · 166 | 10,232 · 67 | 10,221 · 123 |
| `www.gov.uk/government/organisations/hm-revenue-custo` | government | 131,984 B | 131,946 · 267 | 4,956 · 351 | 5,175 · 350 | 219 · 314 | 20,255 · 450 |
| `arxiv.org/abs/1706.03762` | preprint abstract | 43,644 B | 43,644 · 76 | 3,915 · 118 | 4,007 · 180 | 2,046 · 99 | 9,453 · 183 |
| `books.toscrape.com/catalogue/a-light-in-the-attic_10` | e-commerce product | 9,279 B | 9,275 · 336 | 1,474 · 343 | 1,508 · 369 | 1,422 · 342 | 1,777 · 402 |
| `peps.python.org/pep-0008` | language spec | 121,592 B | 121,327 · 54 | 45,262 · 198 | 45,367 · 462 | 39,194 · 182 | 53,826 · 327 |
| `keepachangelog.com/en/1.1.0` | changelog | 26,341 B | 26,130 · 31 | 15,734 · 54 | 15,734 · 116 | 7,580 · 48 | 17,205 · 101 |
| `danluu.com` | static blog index | 22,559 B | 22,555 · 43 | 17,248 · 82 | 17,248 · 203 | 17,653 · 79 | 17,482 · 130 |
| `github.com/pallets/flask` | repo page | 292,307 B | 292,273 · 470 | 1,347 · 607 | 1,365 · 670 | 1,399 · 532 | 12,047 · 701 |
| `fastapi.tiangolo.com/tutorial` | tutorial docs | 105,932 B | 105,845 · 90 | 7,286 · 133 | 7,318 · 279 | 7,342 · 123 | 19,337 · 232 |
| `paulgraham.com/greatwork.html` | essay | 79,767 B | 79,767 · 772 | 67,121 · 822 | 67,121 · 724 | 68,611 · 861 | 67,770 · 886 |
| `react.dev` | client-rendered docs | 272,438 B | 272,408 · 452 | 3,820 · 602 | 3,820 · 502 | 2,972 · 575 | 15,964 · 704 |

### Set 2 aggregates

| tool | median ms | median chars | median links | avg boilerplate markers | broken link targets | unstable outputs | near-empty (<200 c) |
|---|---:|---:|---:|---:|---:|---:|---:|
| raw HTML | 90 | 79,767 | 0 | 1.7 | 0 | 0/11 | 0/11 |
| trafilatura (same kwargs) | 198 | 4,956 | 5 | 0.2 | 2 | 0/11 | 1/11 |
| Scrapiq API | 350 | 7,318 | 5 | 0.2 | 2 | 0/11 | 0/11 |
| readability-lxml | 182 | 7,342 | 4 | 0.2 | 0 | 0/11 | 0/11 |
| MarkItDown | 327 | 17,205 | 22 | 1.5 | 8 | 0/11 | 0/11 |

## What the two sets together show

**1. The library-only call silently returns nothing on 1/23 pages while the API returns the page — and the cause is the response type, not the extractor.**
Scrapiq runs `trafilatura.extract(...)` with these exact kwargs; when that
returns empty it falls back to a BeautifulSoup pass before giving up. The
empty result is not a parser defect: it is an HTML extractor handed a
response that is not HTML. On these pages the bare library call produces
nothing at all, with no error:

- `www.apache.org/licenses/LICENSE-2.0` (license text) — trafilatura **0 chars**, Scrapiq **9,354**

Reproduced 2026-09-14 (trafilatura 2.2.0, `verify_ct_license.py`): the Apache
licence URL is served as `Content-Type: text/plain` — 11,358 characters of
licence text, no markup. Wrapping the same characters in `<pre>` makes the
library return 11,332, and the page's HTML twin (`LICENSE-2.0.html`) extracts
fine, so nothing is wrong with the extraction itself. The finding is therefore
narrow and testable: a pipeline that pipes whatever the server returned into
an HTML extractor gets an empty document that looks like a successful
extraction whenever the response is `text/plain`, JSON or XML.

**2. readability-lxml returned under 200 characters on 2/23 pages**, while never raising an error:

- `news.ycombinator.com` — 1 chars
- `www.theguardian.com/international` — 181 chars

**3. MarkItDown keeps the chrome with the content** — 4/23 pages carry 4+ boilerplate markers
(`cookie`, `sign in`, `subscribe`, `privacy policy`, …) in its output, against
0 for Scrapiq:

- `github.com/NG-PR0JECT/scrapiq` — MarkItDown 4 markers vs Scrapiq 0, 13,447 vs 4,531 chars
- `www.theguardian.com/international` — MarkItDown 8 markers vs Scrapiq 0, 58,237 vs 4,068 chars
- `github.com/pallets/flask` — MarkItDown 4 markers vs Scrapiq 0, 12,047 vs 1,365 chars
- `fastapi.tiangolo.com/tutorial` — MarkItDown 4 markers vs Scrapiq 0, 19,337 vs 7,318 chars

## Scrapiq API vs the trafilatura library, called with identical kwargs

Scrapiq's service layer runs the very same `trafilatura.extract(...)` call the
baseline uses, so this delta is what the API layer adds on top of the library —
not an option difference. Across all 23 pages that answered:

| metric | value |
|---|---:|
| pages where Scrapiq returned >= the library | 23/23 |
| pages where Scrapiq returned strictly more | 17/23 |
| median extra characters | +70 |
| median extra links | +0 |
| largest recovery | +9,354 chars on `www.apache.org/licenses/LICENSE-2.0` |

The honest reading: on most pages the extractor is doing the work and the API
layer adds a little (or nothing), which is expected — it is the same parser. The
API layer earns its keep on the pages where the parser returns nothing (finding 1
above) and on the metadata, schema, retry and self-hosting side, not on raw
character counts.

### Latency: first (cold) call vs the two-run median

`bench.py` calls each tool twice back-to-back per page. For `scrapiq` that second
call can hit the API's own cache, so the two-run median blends a cold and a warm
call. The cold column is the first call only:

| tool | cold ms (first call) | two-run median ms |
|---|---:|---:|
| raw HTML | 97 | 97 |
| trafilatura (same kwargs) | 253 | 251 |
| Scrapiq API | 411 | 369 |
| readability-lxml | 217 | 221 |
| MarkItDown | 414 | 402 |

## Silent-failure sweep, 2026-09-15 and the corrected re-run, 2026-09-16

`detect_silent.py` (one fetch per URL, three extractors, `SILENT EMPTY` =
2xx fetch **and** under 200 characters out **and** no error raised) ran over both
page sets on 2026-09-15, and again on 2026-09-16 on the same pages.

| tool | 2026-09-15 | 2026-09-16 |
|---|---|---|
| trafilatura | 1/23 | 1/23 — `www.apache.org/licenses/LICENSE-2.0`, 0 chars, `Content-Type: text/plain` |
| readability-lxml | 2/23 | 2/23 — `news.ycombinator.com` 1 char, `theguardian.com/international` 195 → 123 chars |
| Scrapiq API | 0/23 | 0/23 |

Both silent faults are sticky in the direction that matters: the same two pages,
the same tools, two days apart. The Guardian page moved from 195 to 123 characters
between runs — a live front page, so the number moves, but it stays an order of
magnitude below what the same response yields through trafilatura (2,548 chars) and
below the 200-character line both days.

The Stack Overflow Q&A page is excluded from every column on both days: it answers
a plain fetch with HTTP 403 and a challenge page, so there is no content to
attribute to any extractor. Against the hosted API that URL returns
`{"detail": "HTTP 403 from target"}` — an explicit failure, which is the correct
outcome and the one the benchmark is arguing for.

**Correction.** The 2026-09-15 table in README.md read `Scrapiq 1/24`. That entry
was this 403 page: the first version of the script extracted from the blocked body
and counted "fewer than 200 chars, no exception" as silence without ever checking
whether the fetch had succeeded, and it scored the API's explicit error response as
an empty document. The script now skips non-2xx fetches and treats an API error as
an error (`--include-non-2xx` restores the old behaviour, for anyone who wants to
see the difference). Raw runs: `silent-2026-09-15-set{1,2}.json`,
`silent-2026-09-16-set{1,2}.json`.

## Notes on the method

- Everything is fetch-based. Neither Scrapiq nor any baseline in this table
  executes JavaScript, so JS-only pages come back thin for all of them.
- `boilerplate markers` is a crude lowercased substring count
  (`cookie`, `sign in`, `subscribe`, `privacy policy`, …). It indicates site
  chrome leaking into the body; it is not a content-quality score.
- `malformed link targets` counts `](` targets containing a nested `[`,
  i.e. structurally broken markdown.
- Latency includes the network fetch for `raw`, `trafilatura`, `readability`
  and `markitdown` (measured separately, then added to the in-process extract
  time) and the full round trip for `scrapiq`, whose server does its own fetch.
- Set 1 is 12 pages, set 2 is 12 more, one of which refused the fetch. 23 scored
  pages is still a spot check, not a ranking of the whole web.
- One URL that refuses the fetch is a result about that URL, not about any
  extractor. It is counted separately everywhere in this repo since 2026-09-16.

