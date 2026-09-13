#!/usr/bin/env python3
"""Page sets for the Scrapiq extraction benchmark.

Set 1 — the original 12 pages (2026-09-12), used again on 2026-09-13 as a
reproducibility re-run.
Set 2 — 12 additional pages (2026-09-13) chosen to cover archetypes set 1 does
not: license text, a government organisation page, a preprint abstract, a Q&A
page, an e-commerce product page, a language spec, a changelog, a static blog
index, a source-repository landing page, framework tutorial docs, a philosophy
essay, and a modern client-rendered docs site.

The mix is deliberate and still not a random sample of the web — see the
Caveats section of README.md.
"""

PAGE_SET_1 = [
    ("docs", "https://docs.python.org/3/library/json.html"),
    ("docs", "https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/GET"),
    ("docs", "https://doc.rust-lang.org/book/ch01-00-getting-started.html"),
    ("encyclopedia", "https://en.wikipedia.org/wiki/Retrieval-augmented_generation"),
    ("repo", "https://github.com/NG-PR0JECT/scrapiq"),
    ("registry", "https://pypi.org/project/trafilatura/"),
    ("blog", "https://simonwillison.net/"),
    ("forum", "https://news.ycombinator.com/"),
    ("product", "https://stripe.com/docs/api"),
    ("news", "https://www.theguardian.com/international"),
    ("book", "https://www.gutenberg.org/ebooks/1342"),
    ("landing", "https://scrapiq.io/"),
]

PAGE_SET_2 = [
    ("license", "https://www.apache.org/licenses/LICENSE-2.0"),
    ("government", "https://www.gov.uk/government/organisations/hm-revenue-customs"),
    ("preprint", "https://arxiv.org/abs/1706.03762"),
    ("q-and-a", "https://stackoverflow.com/questions/11227809/why-is-processing-a-sorted-array-faster-than-processing-an-unsorted-array"),
    ("ecommerce", "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"),
    ("spec", "https://peps.python.org/pep-0008/"),
    ("changelog", "https://keepachangelog.com/en/1.1.0/"),
    ("blog-index", "https://danluu.com/"),
    ("repo", "https://github.com/pallets/flask"),
    ("tutorial", "https://fastapi.tiangolo.com/tutorial/"),
    ("essay", "https://paulgraham.com/greatwork.html"),
    ("client-rendered", "https://react.dev/"),
]

PAGE_SETS = {1: PAGE_SET_1, 2: PAGE_SET_2}

KIND_LABEL = {
    # set 1
    "docs": "docs", "encyclopedia": "encyclopedia", "repo": "repo page",
    "registry": "package registry", "blog": "blog index", "forum": "forum",
    "product": "product docs", "news": "news front", "book": "book page",
    "landing": "landing page",
    # set 2
    "license": "license text", "government": "government", "preprint": "preprint abstract",
    "q-and-a": "Q&A", "ecommerce": "e-commerce product", "spec": "language spec",
    "changelog": "changelog", "blog-index": "static blog index",
    "tutorial": "tutorial docs", "essay": "essay",
    "client-rendered": "client-rendered docs",
}
