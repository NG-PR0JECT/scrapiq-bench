#!/usr/bin/env python3
"""Why trafilatura returns 0 chars on the Apache licence page — content-type check.

The bench reports "the bare library call returns 0 characters with no error" on
https://www.apache.org/licenses/LICENSE-2.0. Before quoting that as a parser failure,
establish the cause: what does the server actually serve, and does the same text
extract fine once it is presented as HTML?
"""
import httpx
import trafilatura

URL = "https://www.apache.org/licenses/LICENSE-2.0"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")

r = httpx.get(URL, headers={"User-Agent": UA}, timeout=30, follow_redirects=True)
ct = r.headers.get("content-type", "")
print(f"HTTP {r.status_code} | content-type: {ct} | body: {len(r.text)} chars")

bench_kwargs = dict(include_links=True, include_images=False, include_tables=True,
                    output_format="markdown", with_metadata=False)

plain = trafilatura.extract(r.text, **bench_kwargs)
print(f"\n1. trafilatura(r.text)                        -> {len(plain or '')} chars")

wrapped = f"<html><body><pre>{r.text}</pre></body></html>"
w_html = trafilatura.extract(wrapped, **bench_kwargs)
print(f"2. trafilatura(same text wrapped in <pre>)     -> {len(w_html or '')} chars")

wrapped_p = "<html><body>" + "".join(
    f"<p>{chunk.strip()}</p>" for chunk in r.text.split("\n\n") if chunk.strip()
) + "</body></html>"
w_p = trafilatura.extract(wrapped_p, **bench_kwargs)
print(f"3. trafilatura(same text as <p> blocks)        -> {len(w_p or '')} chars")

api = httpx.post("https://scrapiq.io/v1/extract",
                 json={"url": URL, "format": "markdown"}, timeout=45)
d = api.json() if api.status_code == 200 else {}
md = (d.get("content") or d.get("markdown") or "") if isinstance(d, dict) else ""
print(f"4. Scrapiq API                                 -> HTTP {api.status_code}, {len(md)} chars")
if md:
    print(f"   head: {md[:160].replace(chr(10), ' / ')}")

# Same URL forced through an HTML-only path: is it the content-type or the page?
print("\n--- does a text/plain twin exist that IS html? ---")
for alt in ("https://www.apache.org/licenses/LICENSE-2.0.html",
            "https://www.apache.org/licenses/LICENSE-2.0.txt"):
    try:
        rr = httpx.get(alt, headers={"User-Agent": UA}, timeout=20, follow_redirects=True)
        print(f"{alt} -> HTTP {rr.status_code} | {rr.headers.get('content-type','?')} | {len(rr.text)} chars")
    except Exception as exc:  # noqa: BLE001
        print(f"{alt} -> ERROR {exc}")
