"""Ingest routes: sample bootstrap, status, PDF upload (E06)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from agentic_crag.adapters.retrieval.pdf_extract import extract_pdf_text
from agentic_crag.adapters.retrieval.sample_bootstrap import ensure_sample_corpus
from agentic_crag.domain.exceptions import MalformedPdfError

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


@router.post("/pdf")
async def ingest_pdf(
    request: Request,
    file: Annotated[UploadFile, File()],
) -> dict[str, Any]:
    ingest = getattr(request.app.state, "ingest", None)
    if ingest is None:
        raise HTTPException(
            status_code=503,
            detail="Ingest service not configured (graph/store not wired).",
        )

    content_type = (file.content_type or "").lower()
    filename = file.filename or "upload.pdf"
    allowed_mime = {"application/pdf", "application/x-pdf", ""}
    if content_type not in allowed_mime and not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "ERR_SCANNED_OR_EMPTY_PDF",
                "message": f"Unsupported MIME type: {content_type or 'unknown'}",
            },
        )

    data = await file.read()
    try:
        text = extract_pdf_text(data)
    except MalformedPdfError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": getattr(exc, "code", "ERR_SCANNED_OR_EMPTY_PDF"), "message": str(exc)},
        ) from exc

    # Wrap plain PDF text as markdown so the header-aware chunker can split.
    markdown = f"# {filename}\n\n{text}"
    count = await ingest.ingest_markdown(filename, markdown)
    return {"status": "ingested", "source_file": filename, "chunks": count}
