from __future__ import annotations

from collections import defaultdict
from typing import Any


def build_report(question: str, extracts: list[dict[str, Any]], source_by_id: dict[int, dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    lines: list[str] = [f"# Research Report\n\nQuestion: {question}\n"]
    lines.append("## Executive summary")
    evidence: list[dict[str, Any]] = []
    bullets = 0
    for ex in extracts[:10]:
        src = source_by_id[ex["source_id"]]
        tag = src["tag"]
        snippet = (ex["snippets"][0] if ex["snippets"] else ex["cleaned_text"][:220]).strip()
        if not snippet:
            continue
        lines.append(f"- {snippet[:220]} [{tag}]")
        evidence.append({
            "claim": snippet[:160],
            "source_tags": [tag],
            "confidence": round(min(0.95, 0.4 + (src.get("credibility") or 0.4)), 2),
            "counterpoints": "May reflect source framing bias.",
        })
        bullets += 1
        if bullets >= 7:
            break

    lines.append("\n## Key findings")
    by_domain: dict[str, list[str]] = defaultdict(list)
    for ex in extracts:
        src = source_by_id[ex["source_id"]]
        if ex["snippets"]:
            by_domain[src["domain"]].append(f"{ex['snippets'][0][:260]} [{src['tag']}]")
    for domain, items in list(by_domain.items())[:6]:
        lines.append(f"{domain}: {' '.join(items[:2])}")

    lines.append("\n## Open questions + what would change my mind")
    lines.append("- What contradictory high-quality studies exist that dispute these trends? [S1]")
    lines.append("- What recent policy updates post-date fetched sources? [S1]")
    lines.append("- What would change my mind: replicated evidence from multiple independent institutions. [S1]")
    report = "\n".join(lines)
    return report, evidence
