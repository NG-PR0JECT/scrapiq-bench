#!/usr/bin/env python3
"""Retry a page within an existing results json and merge the row in.

Usage: python retry_page.py <results.json> <url> [replacement_url]
With a replacement_url, the failing row for <url> is re-measured against
<replacement_url> and takes that url (used when a page is simply unreachable
from this machine).
Exits non-zero if the page still fails (nothing written).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bench import TOOLS, fetch, md_metrics, run_tool  # noqa: E402

import hashlib  # noqa: E402
import statistics  # noqa: E402


def main() -> int:
    path = Path(sys.argv[1])
    url = sys.argv[2]
    target = sys.argv[3] if len(sys.argv) > 3 else url
    payload = json.loads(path.read_text())
    rows = payload["results"]
    row = next((r for r in rows if r["url"] == url), None)
    if row is None:
        print(f"url not in {path}: {url}")
        return 2

    kind = row["kind"]
    url = target
    try:
        html, html_ms, raw_bytes = fetch(url)
    except Exception as exc:  # noqa: BLE001
        print(f"[still failing] {url}: {type(exc).__name__}: {exc}")
        return 1

    new = {"kind": kind, "url": url, "tools": {},
           "http": {"ok": True, "bytes": raw_bytes, "ms": round(html_ms)}}
    print(f"[ok] {url} ({raw_bytes} B, {html_ms:.0f} ms fetch)")
    for tool in TOOLS:
        runs = []
        for _ in range(2):
            content, ms, note = run_tool(tool, url, html, html_ms)
            runs.append((content, ms, note))
        texts = [r[0] for r in runs]
        m = md_metrics(texts[0])
        new["tools"][tool] = {
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
    rows[rows.index(row)] = new
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False))
    print(f"merged into {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
