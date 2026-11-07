"""POST /api/v1/ingest/sample — re-run E01 sample corpus bootstrap."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from agentic_crag.adapters.retrieval.sample_bootstrap import ensure_sample_corpus

router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])


@router.post("/sample")
async def ingest_sample(request: Request) -> dict[str, Any]:
    ingest = getattr(request.app.state, "ingest", None)
    if ingest is None:
        raise HTTPException(
            status_code=503,
            detail="Ingest service not configured (graph/store not wired).",
        )
    return await ensure_sample_corpus(ingest)


@router.get("/status")
async def ingest_status(request: Request) -> dict[str, Any]:
    ingest = getattr(request.app.state, "ingest", None)
    if ingest is None:
        raise HTTPException(status_code=503, detail="Ingest service not configured.")
    exists = await ingest.collection_exists()
    count = await ingest.point_count()
    return {"collection_exists": exists, "points": count}
