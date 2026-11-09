"""GET /api/v1/benchmarks — serve committed golden/Ragas metrics snapshot.

Caller: FastAPI via main.py include_router; frontend EvalsDrawer fetches this.
User: Implement the plan as specified (1.5 benchmarks wire-up).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/benchmarks", tags=["benchmarks"])

_CANDIDATES = (
    Path(__file__).resolve().parents[4] / "evals" / "metrics_snapshot.json",
    Path(__file__).resolve().parents[2] / "data" / "metrics_snapshot.json",
)


def _load_snapshot() -> dict[str, Any]:
    for path in _CANDIDATES:
        if path.is_file():
            raw: Any = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                return dict(raw)
    return {
        "source": "missing_snapshot",
        "metrics": [],
        "golden_sample": [],
    }


@router.get("")
async def get_benchmarks() -> dict[str, Any]:
    return _load_snapshot()
