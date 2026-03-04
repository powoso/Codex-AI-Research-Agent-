from __future__ import annotations

import re
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from typing import Any

try:
    import trafilatura  # type: ignore
except Exception:  # noqa: BLE001
    trafilatura = None


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.in_title = False
        self.title = ""

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        if tag == "title":
            self.in_title = True

    def handle_endtag(self, tag: str) -> None:  # type: ignore[override]
        if tag == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:  # type: ignore[override]
        txt = data.strip()
        if txt:
            self.parts.append(txt)
            if self.in_title and not self.title:
                self.title = txt


def extract_document(html: str, url: str = "") -> dict[str, Any]:
    if trafilatura:
        md = trafilatura.extract_metadata(html)
        title = md.title if md else None
        text = trafilatura.extract(html, include_links=False, include_formatting=False) or ""
    else:
        p = _TextParser()
        p.feed(html)
        title = p.title
        text = " ".join(p.parts)
    cleaned = re.sub(r"\s+", " ", unescape(text)).strip()
    snippets = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if len(s.strip()) > 60][:8]
    published_at = _guess_date(html)
    return {
        "title": title or (url[:120] if url else "Untitled"),
        "raw_text": text,
        "cleaned_text": cleaned,
        "snippets": snippets,
        "published_at": published_at,
    }


def _guess_date(html: str) -> str | None:
    m = re.search(r"(20\d{2}-\d{2}-\d{2})", html)
    if not m:
        return None
    try:
        datetime.fromisoformat(m.group(1))
        return m.group(1)
    except ValueError:
        return None
