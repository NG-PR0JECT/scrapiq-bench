#!/usr/bin/env python3
"""Scrapiq extraction benchmark — real pages, real tools, honest numbers.

Compares end-to-end "URL in -> clean markdown out" for:
  - raw      : raw HTML baseline (what you get with httpx.get().text)
  - trafilatura : library call on the fetched HTML (same core Scrapiq wraps)
  - scrapiq  : POST http://localhost:8001/v1/extract (format=markdown)
  - readability : readability-lxml + html2text
  - markitdown: MarkItDown on the fetched HTML

Per page/tool: wall-clock ms, chars, words, links, boilerplate-marker hits,
and stability (two runs -> identical output hash?).

Usage:
  python bench.py --set 1 --out results-2026-09-12.json
  python bench.py --set 2 --out results-2026-09-13-set2.json
"""
import argparse
import hashlib
import json
import re
import statistics
import time
from pathlib import Path

import httpx
import trafilatura
from bs4 import BeautifulSoup
from markitdown import MarkItDown
from readability import Document
import html2text

from pages import PAGE_SETS

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
SCRAPIQ = "http://localhost:8001/v1/extract"
OUT = Path(__file__).resolve().parent

# lowercase substrings that indicate site chrome leaked into the body
BOILER = [
    "cookie", "sign in", "sign up", "log in", "subscribe", "newsletter",
    "skip to", "privacy policy", "terms of service", "all rights reserved",
    "advertisement", "accept all", "manage preferences",
]
LINK_RE = re.compile(r"\]\(https?://")


def fetch(url: str) -> tuple[str, float, int]:
    t0 = time.perf_counter()
    r = httpx.get(url, headers={"User-Agent": UA}, timeout=30, follow_redirects=True)
    dt = (time.perf_counter() - t0) * 1000
    r.raise_for_status()
    return r.text, dt, len(r.content)


def md_metrics(text: str) -> dict:
    if not text:
        # an empty output contains no boilerplate markers and no links, by definition
        return {"chars": 0, "words": 0, "links": 0, "boiler": 0, "malformed": 0}
    low = text.lower()
    return {
        "chars": len(text),
        "words": len(text.split()),
        "links": len(LINK_RE.findall(text)) + low.count("](http://"),
        "boiler": sum(1 for b in BOILER if b in low),
        # nested '[' inside a link target => structurally broken markdown
        "malformed": len(re.findall(r"\]\([^)\s]*\[", text)),
    }


def run_tool(name, url, html, html_ms):
    """Return (content, elapsed_ms, note)."""
    if name == "raw":
        return html, html_ms, "baseline: raw HTML as fetched"
    if name == "trafilatura":
        # Called exactly the way Scrapiq calls it internally (src/extract.py),
        # so the comparison isolates what the API layer adds on top of the same
        # extraction core instead of counting option differences.
        t0 = time.perf_counter()
        txt = trafilatura.extract(
            html, include_links=True, include_images=False, include_tables=True,
            output_format="markdown", with_metadata=False,
        )
        return (txt or ""), (time.perf_counter() - t0) * 1000 + html_ms, "library on fetched HTML (same kwargs as Scrapiq)"
    if name == "readability":
        t0 = time.perf_counter()
        try:
            doc = Document(html)
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.body_width = 0
            txt = h.handle(doc.summary())
        except Exception as exc:  # noqa: BLE001
            txt = f"__error__ {exc}"
        return txt, (time.perf_counter() - t0) * 1000 + html_ms, "readability-lxml + html2text"
    if name == "markitdown":
        t0 = time.perf_counter()
        try:
            res = MarkItDown().convert_stream(
                __import__("io").BytesIO(html.encode("utf-8")),
                file_extension=".html",
            )
            txt = res.text_content
        except Exception as exc:  # noqa: BLE001
            txt = f"__error__ {exc}"
        return txt, (time.perf_counter() - t0) * 1000 + html_ms, "MarkItDown on fetched HTML"
    if name == "scrapiq":
        t0 = time.perf_counter()
        try:
            r = httpx.post(SCRAPIQ, json={"url": url, "format": "markdown"}, timeout=45)
            d = r.json()
            txt = d.get("content") or ""
        except Exception as exc:  # noqa: BLE001
            txt = f"__error__ {exc}"
        return txt, (time.perf_counter() - t0) * 1000, "hosted API: fetch + extract in one call"
    raise ValueError(name)


TOOLS = ["raw", "trafilatura", "readability", "markitdown", "scrapiq"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", type=int, default=1, choices=sorted(PAGE_SETS))
    ap.add_argument("--out", default=None, help="output json (default: results.json / results-set2.json)")
    ap.add_argument("--stamp", default=None, help="ISO date written into the json header")
    args = ap.parse_args()

    pages = PAGE_SETS[args.set]
    out_path = OUT / (args.out or ("results.json" if args.set == 1 else f"results-set{args.set}.json"))

    results = []
    for kind, url in pages:
        row = {"kind": kind, "url": url, "tools": {}}
        try:
            html, html_ms, raw_bytes = fetch(url)
            row["http"] = {"ok": True, "bytes": raw_bytes, "ms": round(html_ms)}
        except Exception as exc:  # noqa: BLE001
            row["http"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
            results.append(row)
            print(f"[HTTP FAIL] {url}: {exc}")
            continue
        print(f"[ok] {url} ({raw_bytes} B, {html_ms:.0f} ms fetch)")

        for tool in TOOLS:
            runs = []
            for _ in range(2):  # twice -> timing median + stability check
                content, ms, note = run_tool(tool, url, html, html_ms)
                runs.append((content, ms, note))
            texts = [r[0] for r in runs]
            m = md_metrics(texts[0])
            row["tools"][tool] = {
                "ms_median": round(statistics.median([r[1] for r in runs])),
                "ms_runs": [round(r[1]) for r in runs],
                "chars": m["chars"], "words": m["words"], "links": m["links"],
                "boiler": m["boiler"], "malformed": m["malformed"],
                "stable": hashlib.sha256(texts[0].encode()).hexdigest()
                == hashlib.sha256(texts[1].encode()).hexdigest(),
                "empty": m["chars"] < 200,
                "note": runs[0][2],
                "preview": texts[0][:180].replace("\n", " "),
            }
        results.append(row)

    payload = {
        "set": args.set,
        "stamp": args.stamp,
        "pages": [u for _, u in pages],
        "results": results,
    }
    out_path.write_text(json.dumps(payload, indent=1, ensure_ascii=False))
    print("\nwrote", out_path)
    return results


if __name__ == "__main__":
    main()
