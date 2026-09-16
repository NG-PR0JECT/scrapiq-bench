#!/usr/bin/env python3
"""detect_silent.py — find the extractions that look successful and are empty.

Point it at your own URL list (or at the benchmark's page sets) and it reports,
per URL and per tool: HTTP status, response Content-Type, response bytes, and how
many characters the tool returned. The interesting row is the one where the fetch
succeeded (2xx) and the extractor produced almost nothing *without raising*.

That combination is the failure mode this repo keeps running into: nothing in the
logs, no exception, an empty document downstream.

What it is NOT: a verdict on any library. An HTML extractor handed a non-HTML
response (text/plain, JSON, PDF) will legitimately return nothing — the finding is
that the *pipeline* has no way to notice. See README "Silent failures" and
verify_ct_license.py for the worked example.

Two counting rules, both added 2026-09-16 after the first run of this script
over-counted (see RESULTS.md "Correction"):

  1. A URL whose fetch did not return 2xx is *skipped*, not counted as a silent
     empty for any tool. A 403 challenge page has no content to extract, so
     "the extractor returned 41 chars" says nothing about the extractor.
  2. For the hosted Scrapiq column, an error response (the API answers a blocked
     target with an explicit `{"detail": "HTTP 403 from target"}`) is recorded as
     an explicit error, never as an empty. That distinction is the whole point of
     the exercise: explicit failure is fine, silence is not.

Usage:
  python detect_silent.py --set 1
  python detect_silent.py urls.txt --out silent-2026-09-16.json
  python detect_silent.py urls.txt --no-api          # skip the hosted Scrapiq column
  python detect_silent.py urls.txt --include-non-2xx # old behaviour: extract anyway

One fetch per URL (not the benchmark's two), so this is cheap enough to run daily
in CI or on a sitemap sample.
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

import html2text
import httpx
import trafilatura
from readability import Document

try:
    from pages import PAGE_SETS
except ImportError:  # standalone use
    PAGE_SETS = {}

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
SCRAPIQ = "http://localhost:8001/v1/extract"

# Below this many characters we call the extraction silent-but-successful.
EMPTY_THRESHOLD = 200


def fetch(url: str):
    r = httpx.get(url, headers={"User-Agent": UA}, timeout=30, follow_redirects=True)
    ct = (r.headers.get("content-type") or "").split(";")[0].strip().lower()
    return r, ct, len(r.content)


def extract(tool: str, url: str, body: str):
    """Return (chars, error_or_none). An error string means the tool said so."""
    if tool == "trafilatura":
        try:
            txt = trafilatura.extract(
                body, include_links=True, include_images=False, include_tables=True,
                output_format="markdown", with_metadata=False,
            )
            return len(txt or ""), None
        except Exception as exc:  # noqa: BLE001
            return 0, f"{type(exc).__name__}: {exc}"
    if tool == "readability":
        try:
            doc = Document(body)
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.body_width = 0
            return len(h.handle(doc.summary())), None
        except Exception as exc:  # noqa: BLE001
            return 0, f"{type(exc).__name__}: {exc}"
    if tool == "scrapiq":
        try:
            r = httpx.post(SCRAPIQ, json={"url": url, "format": "markdown"}, timeout=45)
            try:
                payload = r.json()
            except ValueError:
                payload = {}
            if r.status_code >= 400 or (isinstance(payload, dict) and payload.get("detail")):
                detail = payload.get("detail") if isinstance(payload, dict) else None
                return 0, f"HTTP {r.status_code}: {detail or r.text[:120]}"
            return len(((payload or {}).get("content") or "")), None
        except Exception as exc:  # noqa: BLE001
            return 0, f"{type(exc).__name__}: {exc}"
    raise ValueError(tool)


def is_html(ct: str) -> bool:
    return ct in ("text/html", "application/xhtml+xml") or ct.endswith("+html")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url_file", nargs="?", help="file with one URL per line")
    ap.add_argument("--set", type=int, choices=sorted(PAGE_SETS), help="use the benchmark's page set N")
    ap.add_argument("--no-api", action="store_true", help="skip the hosted Scrapiq column")
    ap.add_argument("--threshold", type=int, default=EMPTY_THRESHOLD)
    ap.add_argument("--include-non-2xx", action="store_true",
                    help="extract from non-2xx bodies too (pre-2026-09-16 behaviour)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if args.set is not None and args.set in PAGE_SETS:
        url_list = [u for _, u in PAGE_SETS[args.set]]
    elif args.url_file:
        url_list = [l.strip() for l in Path(args.url_file).read_text().splitlines() if l.strip()]
    else:
        ap.error("give a URL file or --set")
        return 2

    tools = ["trafilatura", "readability"] + ([] if args.no_api else ["scrapiq"])
    rows, silent, fetch_errors, explicit = [], [], [], []
    counted = 0

    for url in url_list:
        row = {"url": url, "tools": {}}
        try:
            r, ct, nbytes = fetch(url)
            row["http"] = {"status": r.status_code, "content_type": ct, "bytes": nbytes,
                           "html": is_html(ct)}
            body = r.text
        except Exception as exc:  # noqa: BLE001
            row["http"] = {"error": f"{type(exc).__name__}: {exc}"}
            row["skipped"] = "fetch raised"
            fetch_errors.append({"url": url, "why": f"{type(exc).__name__}: {exc}"})
            rows.append(row)
            print(f"[FETCH FAIL] {url}: {exc}")
            continue

        ok = 200 <= row["http"]["status"] < 300
        print(f"[{row['http']['status']}] {ct or 'no content-type':<24} {nbytes:>8} B  {url}")
        if not ok and not args.include_non_2xx:
            row["skipped"] = f"non-2xx fetch ({row['http']['status']}) — nothing to extract"
            fetch_errors.append({"url": url, "why": f"HTTP {row['http']['status']}", "content_type": ct})
            print("        skipped: non-2xx fetch, no extractor run")
            rows.append(row)
            continue

        counted += 1
        for t in tools:
            chars, err = extract(t, url, body)
            empty = chars < args.threshold and err is None
            row["tools"][t] = {"chars": chars, "empty": empty, "error": err}
            if err:
                explicit.append({"url": url, "tool": t, "error": err})
                print(f"        {t:<12} {chars:>7} chars  error: {err[:80]}")
                continue
            if empty:
                silent.append({"url": url, "tool": t, "content_type": ct,
                               "bytes": nbytes, "status": row["http"]["status"]})
            flag = "  <-- SILENT EMPTY" if empty else ""
            print(f"        {t:<12} {chars:>7} chars{flag}")
        rows.append(row)

    payload = {
        "stamp": date.today().isoformat(),
        "threshold": args.threshold,
        "pages": url_list,
        "counted": counted,
        "results": rows,
        "silent": silent,
        "explicit_errors": explicit,
        "fetch_errors": fetch_errors,
    }
    out = Path(args.out) if args.out else Path(__file__).resolve().parent / f"silent-{payload['stamp']}.json"
    out.write_text(json.dumps(payload, indent=1, ensure_ascii=False))

    print("\n--- summary ---")
    print(f"urls: {len(url_list)}  counted (2xx): {counted}  "
          f"skipped: {len(fetch_errors)}  threshold: <{args.threshold} chars")
    for t in tools:
        hits = [s for s in silent if s["tool"] == t]
        errs = [e for e in explicit if e["tool"] == t]
        nonhtml = [s for s in hits if not is_html(s["content_type"])]
        print(f"{t:<12} silent-empty on {len(hits)}/{counted} "
              f"({len(nonhtml)} of those non-HTML) · explicit errors: {len(errs)}")
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
