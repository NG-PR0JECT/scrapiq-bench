# Results

Run: 2026-09-12, from a single machine in Europe/Paris, against the live web
(12 URLs) and a locally self-hosted Scrapiq API (`v0.1.0`, `http://localhost:8001`).
Every tool ran twice per page: the first run supplies the content, both runs
supply the latency, and the two outputs are hashed against each other for the
stability column.

## Content size and latency

| page | kind | raw HTML | raw HTML chars · ms | trafilatura (same kwargs) chars · ms | Scrapiq API chars · ms | readability-lxml chars · ms | MarkItDown chars · ms |
|---|---|---:|---:|---:|---:|---:|---:|
| `docs.python.org/3/library/json.html` | docs | 111,909 B | 111,760 · 115 | 28,792 · 285 | 28,862 · 621 | 4,402 · 184 | 37,406 · 478 |
| `developer.mozilla.org/en-US/docs/Web/HTTP/Methods/GE` | docs | 213,761 B | 213,630 · 61 | 2,896 · 109 | 3,261 · 263 | 1,148 · 97 | 45,932 · 293 |
| `doc.rust-lang.org/book/ch01-00-getting-started.html` | docs | 22,877 B | 22,865 · 44 | 315 · 50 | 315 · 73 | 383 · 51 | 565 · 110 |
| `en.wikipedia.org/wiki/Retrieval-augmented_generation` | encyclopedia | 240,835 B | 240,046 · 89 | 22,434 · 251 | 22,737 · 515 | 22,470 · 216 | 79,075 · 426 |
| `github.com/NG-PR0JECT/scrapiq` | repo | 297,371 B | 297,243 · 34 | 3,587 · 95 | 3,669 · 264 | 2,969 · 97 | 12,570 · 218 |
| `pypi.org/project/trafilatura` | registry | 127,668 B | 127,604 · 31 | 10,209 · 126 | 10,347 · 381 | 9,819 · 97 | 33,535 · 236 |
| `simonwillison.net` | blog | 80,988 B | 80,920 · 48 | 26,781 · 103 | 27,152 · 216 | 27,969 · 153 | 47,601 · 165 |
| `news.ycombinator.com` | forum | 34,704 B | 34,697 · 548 | 4,094 · 707 | 6,970 · 858 | 1 · 592 | 10,398 · 649 |
| `stripe.com/docs/api` | product | 1,363,583 B | 1,332,183 · 923 | 6,610 · 1008 | 6,648 · 1178 | 4,167 · 995 | 15,173 · 1079 |
| `www.theguardian.com/international` | news | 1,402,692 B | 1,401,647 · 205 | 2,431 · 785 | 2,620 · 1096 | 181 · 397 | 60,473 · 560 |
| `www.gutenberg.org/ebooks/1342` | book | 24,848 B | 24,825 · 348 | 2,389 · 373 | 2,416 · 466 | 719 · 362 | 5,158 · 411 |
| `scrapiq.io` | landing | 10,232 B | 9,609 · 43 | 1,697 · 56 | 1,697 · 134 | 1,797 · 56 | 2,839 · 109 |

## Aggregates

| tool | median ms | median chars | median links | avg boilerplate markers | malformed link targets | unstable outputs | near-empty (<200 c) |
|---|---:|---:|---:|---:|---:|---:|---:|
| raw HTML | 75 | 119,682 | 0 | 2.4 | 0 | 0/12 | 0/12 |
| trafilatura (same kwargs) | 188 | 3,840 | 4 | 0.2 | 0 | 0/12 | 0/12 |
| Scrapiq API | 424 | 5,158 | 8 | 0.2 | 0 | 0/12 | 0/12 |
| readability-lxml | 168 | 2,383 | 0 | 0.2 | 0 | 0/12 | 2/12 |
| MarkItDown | 352 | 24,354 | 54 | 2.2 | 0 | 0/12 | 0/12 |

## Scrapiq API vs trafilatura library, called with identical kwargs

This is the interesting one: Scrapiq's service layer runs the very same
`trafilatura.extract(...)` call the baseline uses, so the delta below is what
the API adds on top of the library — not an option difference.

| page | trafilatura chars | Scrapiq chars | delta | trafilatura links | Scrapiq links | trafilatura ms | Scrapiq ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| `docs.python.org/3/library/json.html` | 28,792 | 28,862 | +70 | 14 | 15 | 285 | 621 |
| `developer.mozilla.org/en-US/docs/Web/HTTP/Methods/GE` | 2,896 | 3,261 | +365 | 1 | 1 | 109 | 263 |
| `doc.rust-lang.org/book/ch01-00-getting-started.html` | 315 | 315 | +0 | 0 | 0 | 50 | 73 |
| `en.wikipedia.org/wiki/Retrieval-augmented_generation` | 22,434 | 22,737 | +303 | 66 | 71 | 251 | 515 |
| `github.com/NG-PR0JECT/scrapiq` | 3,587 | 3,669 | +82 | 6 | 6 | 95 | 264 |
| `pypi.org/project/trafilatura` | 10,209 | 10,347 | +138 | 35 | 35 | 126 | 381 |
| `simonwillison.net` | 26,781 | 27,152 | +371 | 89 | 91 | 103 | 216 |
| `news.ycombinator.com` | 4,094 | 6,970 | +2,876 | 0 | 32 | 707 | 858 |
| `stripe.com/docs/api` | 6,610 | 6,648 | +38 | 10 | 11 | 1008 | 1178 |
| `www.theguardian.com/international` | 2,431 | 2,620 | +189 | 0 | 2 | 785 | 1096 |
| `www.gutenberg.org/ebooks/1342` | 2,389 | 2,416 | +27 | 2 | 2 | 373 | 466 |
| `scrapiq.io` | 1,697 | 1,697 | +0 | 0 | 0 | 56 | 134 |

Scrapiq returned at least as much text as the bare library on **12/12** pages;
the biggest recovery is the forum front page (**+2,876 chars, +32 links**), where
trafilatura drops the comment list and the link-recovery pass puts it back.

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
- No page in this set blocked any of the tools, so this table says nothing
  about anti-bot behaviour.

