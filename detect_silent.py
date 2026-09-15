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

Usage:
  python detect_silent.py --set 1
  python detect_silent.py urls.txt --out silent-2026-09-15.json
  python detect_silent.py urls.txt --no-api          # skip the hosted Scrapiq column

One fetch per URL (not the benchmark's two), so this is cheap enough to run daily
in CI or on a sitemap sample.
"""
import argparse
import io
import json
import sys
from datetime import date
from pathlib import Path

import httpx
import trafilatura
from readability import Document
import html2text

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
    """Return (chars, error_or_none)."""
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
            return len((r.json().get("content") or "")), None
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
    rows, silent = [], []
    for url in url_list:
        row = {"url": url, "tools": {}}
        try:
            r, ct, nbytes = fetch(url)
            row["http"] = {"status": r.status_code, "content_type": ct, "bytes": nbytes,
                           "html": is_html(ct)}
            body = r.text
        except Exception as exc:  # noqa: BLE001
            row["http"] = {"error": f"{type(exc).__name__}: {exc}"}
            rows.append(row)
            print(f"[FETCH FAIL] {url}: {exc}")
            continue

        print(f"[{row['http']['status']}] {ct or 'no content-type':<24} {nbytes:>8} B  {url}")
        for t in tools:
            chars, err = extract(t, url, body)
            empty = chars < args.threshold and err is None
            row["tools"][t] = {"chars": chars, "empty": empty, "error": err}
            if empty:
                silent.append((url, t, ct, nbytes, row["http"]["status"]))
            flag = "  <-- SILENT EMPTY" if empty else ""
            print(f"        {t:<12} {chars:>7} chars{flag}")
        rows.append(row)

    payload = {
        "stamp": date.today().isoformat(),
        "threshold": args.threshold,
        "pages": url_list,
        "results": rows,
        "silent": [{"url": u, "tool": t, "content_type": ct, "bytes": b, "status": st}
                   for u, t, ct, b, st in silent],
    }
    out = Path(args.out) if args.out else Path(__file__).resolve().parent / f"silent-{payload['stamp']}.json"
    out.write_text(json.dumps(payload, indent=1, ensure_ascii=False))

    n_ok = sum(1 for r in rows if r.get("http", {}).get("ok", True) and "error" not in r.get("http", {}))
    print("\n--- summary ---")
    print(f"urls: {len(url_list)}  fetched: {n_ok}  threshold: <{args.threshold} chars")
    for t in tools:
        hits = [s for s in silent if s[1] == t]
        ok = [s for s in hits if 200 <= s[4] < 300]
        nonhtml = [s for s in ok if not is_html(s[2])]
        print(f"{t:<12} silent-empty on {len(hits)}/{len(url_list)} "
              f"({len(ok)} on 2xx responses, {len(nonhtml)} of those non-HTML)")
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
