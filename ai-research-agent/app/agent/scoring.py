from __future__ import annotations

import math
import re
from collections import Counter

TOKEN_RE = re.compile(r"[a-zA-Z]{3,}")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


def keyword_overlap_score(query: str, doc: str) -> float:
    q = set(tokenize(query))
    if not q:
        return 0.0
    d = Counter(tokenize(doc))
    return sum(d.get(tok, 0) for tok in q) / len(q)


def _tfidf_cosine(query: str, docs: list[str]) -> list[float]:
    token_docs = [tokenize(query)] + [tokenize(d) for d in docs]
    vocab = sorted({t for doc in token_docs for t in doc})
    if not vocab:
        return [0.0 for _ in docs]
    idf = {}
    n = len(token_docs)
    for t in vocab:
        df = sum(1 for d in token_docs if t in d)
        idf[t] = math.log((1 + n) / (1 + df)) + 1

    def vec(tokens: list[str]) -> list[float]:
        c = Counter(tokens)
        return [c.get(t, 0) * idf[t] for t in vocab]

    qv = vec(token_docs[0])

    def cos(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        return dot / (na * nb) if na and nb else 0.0

    return [cos(qv, vec(d)) for d in token_docs[1:]]


def rank_urls(query: str, urls: list[str]) -> list[tuple[str, float]]:
    docs = [u.replace("https://", "").replace("http://", "").replace("/", " ") for u in urls]
    overlap = [keyword_overlap_score(query, d) for d in docs]
    cos = _tfidf_cosine(query, docs)
    ranked = []
    for i, u in enumerate(urls):
        score = 0.35 * overlap[i] + 0.65 * float(cos[i])
        ranked.append((u, score))
    ranked.sort(key=lambda x: (-x[1], x[0]))
    return ranked
