"""Local hashed TF sparse vectors (BM25-shaped) — no FastEmbed download in CI."""

from __future__ import annotations

import re
from collections import Counter

from qdrant_client.http import models as qmodels

_TOKEN_RE = re.compile(r"[a-z0-9_]+", re.IGNORECASE)
_SPARSE_MODULUS = 2_097_152


def text_to_sparse_vector(text: str) -> qmodels.SparseVector:
    tokens = _TOKEN_RE.findall(text.lower())
    counts = Counter(tokens)
    if not counts:
        return qmodels.SparseVector(indices=[0], values=[1.0])

    indices: list[int] = []
    values: list[float] = []
    for token, tf in sorted(counts.items()):
        idx = (hash(token) % _SPARSE_MODULUS + _SPARSE_MODULUS) % _SPARSE_MODULUS
        indices.append(idx)
        # shortcut: hashed TF not true BM25, upgrade to Qdrant/bm25 FastEmbed later
        values.append(float(1.0 + tf))
    return qmodels.SparseVector(indices=indices, values=values)
