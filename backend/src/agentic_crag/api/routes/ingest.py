"""Ingest routes: sample bootstrap, status, PDF upload (E06)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, File, Request, UploadFile

from agentic_crag.adapters.retrieval.pdf_extract import extract_pdf_text
from agentic_crag.adapters.retrieval.sample_bootstrap import ensure_sample_corpus
from agentic_crag.api.error_envelope import http_error
from agentic_crag.config import settings
from agentic_crag.domain.exceptions import MalformedPdfError

router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])


def _ingest_or_503(request: Request) -> Any:
    ingest = getattr(request.app.state, "ingest", None)
    if ingest is None:
        raise http_error(
            status_code=503,
            code="ERR_INGEST_UNAVAILABLE",
            developer_message=(
                "app.state.ingest is None — graph/store not wired "
                "(missing GEMINI/GROQ keys or boot failure)."
            ),
            expose_developer=settings.expose_developer_errors,
        )
    return ingest


@router.post("/sample")
async def ingest_sample(
    request: Request,
    force: bool = False,
) -> dict[str, Any]:
    ingest = _ingest_or_503(request)
    return await ensure_sample_corpus(ingest, force=force)


@router.get("/status")
async def ingest_status(request: Request) -> dict[str, Any]:
    ingest = _ingest_or_503(request)
    exists = await ingest.collection_exists()
    count = await ingest.point_count()
    return {"collection_exists": exists, "points": count}


@router.post("/pdf")
async def ingest_pdf(
    request: Request,
    file: Annotated[UploadFile, File()],
) -> dict[str, Any]:
    ingest = _ingest_or_503(request)

    content_type = (file.content_type or "").lower()
    filename = file.filename or "upload.pdf"
    allowed_mime = {"application/pdf", "application/x-pdf", ""}
    if content_type not in allowed_mime and not filename.lower().endswith(".pdf"):
        raise http_error(
            status_code=422,
            code="ERR_SCANNED_OR_EMPTY_PDF",
            developer_message=f"Unsupported MIME type: {content_type or 'unknown'}",
            expose_developer=settings.expose_developer_errors,
        )

    data = await file.read()
    try:
        text = extract_pdf_text(data)
    except MalformedPdfError as exc:
        raise http_error(
            status_code=422,
            code=getattr(exc, "code", "ERR_SCANNED_OR_EMPTY_PDF"),
            developer_message=str(exc),
            expose_developer=settings.expose_developer_errors,
        ) from exc

    markdown = f"# {filename}\n\n{text}"
    count = await ingest.ingest_markdown(filename, markdown)
    return {"status": "ingested", "source_file": filename, "chunks": count}
