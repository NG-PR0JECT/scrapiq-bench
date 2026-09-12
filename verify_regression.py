#!/usr/bin/env python3
"""Prove the new regression test catches the OLD injection logic (simulated)."""
import os, sys, re
sys.path.insert(0, os.environ.get("SCRAPIQ_SRC", "../scrapiq"))
from bs4 import BeautifulSoup


def old_inject(text: str, html: bytes) -> str:
    """Verbatim logic from the pre-fix src/extract.py (str.replace version)."""
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        link_text = a.get_text(strip=True)
        if not link_text or href in text:
            continue
        if link_text in text:
            idx = text.find(link_text)
            if idx >= 0:
                after = text[idx + len(link_text): idx + len(link_text) + 2]
                if not after.startswith("]("):
                    text = text.replace(link_text, f"[{link_text}]({href})", 1)
    return text


# exact fixture from tests/test_extract.py::TestLinkInjectionGuards
text = (
    "# Retrieval-augmented generation\n\n"
    "**Retrieval-augmented generation** (**RAG**) is a technique that enables "
    "[large language models](https://en.wikipedia.org/wiki/Large_language_model) "
    "to retrieve and incorporate new information.\n"
)
html = (
    b'<nav><a href="/wiki/Template:AI">AI</a>'
    b'<a href="/wiki/Template:R">R</a>'
    b'<a href="/wiki/Template:Gen">e</a>'
    b'<a href="/wiki/Template:GenAI">t</a></nav>'
)

out = old_inject(text, html)
print("OLD output:", repr(out[:220]))
assert out == text, "old code CHANGED the text -> bug reproduced"
print("? old code left text unchanged (bug NOT reproduced with this fixture)")

# real captured case: what the Wikipedia page produced
wiki_text = (
    "# Retrieval-augmented generation\n\n**Retrieval-augmented generation** (**RAG**) is a technique "
    "that enables [large language models](https://en.wikipedia.org/wiki/Large_language_model) to retrieve.\n"
)
wiki_html = (
    b'<div class="navbox"><a href="/wiki/Template:Artificial_intelligence_navbox">R</a>'
    b'<a href="/wiki/Template:Generative_AI">e</a>'
    b'<a href="/wiki/Google_AI">AI</a>'
    b'<a href="/wiki/Special:EditPage/Template:Generative_AI">t</a></div>'
)
old_out = old_inject(wiki_text, wiki_html)
print("OLD wiki-case:", repr(old_out[:220]))
print("mangled?", old_out != wiki_text)
