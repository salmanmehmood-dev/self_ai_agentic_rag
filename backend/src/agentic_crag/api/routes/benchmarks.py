"""GET /api/v1/benchmarks — precomputed Ragas shell (Phase 9+ live fill)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/benchmarks", tags=["benchmarks"])

# Shell metrics — same shape as frontend EvalsDrawer until live Ragas lands.
_SHELL: dict[str, Any] = {
    "metrics": [
        {"key": "Context Precision", "naive": 0.62, "agentic": 0.84},
        {"key": "Context Recall", "naive": 0.71, "agentic": 0.88},
        {"key": "Faithfulness", "naive": 0.68, "agentic": 0.91},
        {"key": "Answer Relevance", "naive": 0.74, "agentic": 0.89},
    ],
    "golden_sample": [
        {"id": 1, "query": "Gemini→Groq failover after 429", "latency_ms": 1840, "pass": True},
        {"id": 2, "query": "Hybrid RRF dense+sparse fusion", "latency_ms": 1520, "pass": True},
        {"id": 3, "query": "Ambiguous SLA rewrite path", "latency_ms": 3210, "pass": True},
        {"id": 4, "query": "Out-of-corpus web fallback", "latency_ms": 4100, "pass": True},
        {"id": 5, "query": "Empty collection cold start", "latency_ms": 890, "pass": False},
        {"id": 6, "query": "Citation index bounds strip", "latency_ms": 2010, "pass": True},
    ],
    "source": "shell",
}


@router.get("")
async def get_benchmarks() -> dict[str, Any]:
    return _SHELL
