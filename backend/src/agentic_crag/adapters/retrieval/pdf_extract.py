"""E06: validate PDF magic bytes + extract text (reject scanned/empty pages)."""

from __future__ import annotations

import io

from pypdf import PdfReader

from agentic_crag.domain.exceptions import MalformedPdfError

PDF_MAGIC = b"%PDF-"
MIN_CHARS_PER_PAGE = 20


def assert_pdf_magic(data: bytes) -> None:
    if not data.startswith(PDF_MAGIC):
        raise MalformedPdfError(
            "Invalid PDF magic bytes (expected %PDF-)",
            code="ERR_SCANNED_OR_EMPTY_PDF",
        )


def extract_pdf_text(data: bytes) -> str:
    """Return concatenated page text; raise if any page has < 20 extractable chars."""
    assert_pdf_magic(data)
    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:  # noqa: BLE001
        raise MalformedPdfError(
            f"Unparseable PDF: {exc}",
            code="ERR_SCANNED_OR_EMPTY_PDF",
        ) from exc

    if not reader.pages:
        raise MalformedPdfError("PDF has zero pages", code="ERR_SCANNED_OR_EMPTY_PDF")

    parts: list[str] = []
    for i, page in enumerate(reader.pages):
        text = (page.extract_text() or "").strip()
        if len(text) < MIN_CHARS_PER_PAGE:
            raise MalformedPdfError(
                f"Page {i + 1} yielded < {MIN_CHARS_PER_PAGE} characters "
                "(scanned or empty PDF)",
                code="ERR_SCANNED_OR_EMPTY_PDF",
            )
        parts.append(text)
    return "\n\n".join(parts)
