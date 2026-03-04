from __future__ import annotations

import re

CITE_RE = re.compile(r"\[(S\d+)\]")


def assign_tags(source_ids: list[int]) -> dict[int, str]:
    return {sid: f"S{i+1}" for i, sid in enumerate(source_ids)}


def validate_citations(text: str, allowed_tags: set[str]) -> list[str]:
    missing: list[str] = []
    for tag in CITE_RE.findall(text):
        if tag not in allowed_tags and tag not in missing:
            missing.append(tag)
    return missing
