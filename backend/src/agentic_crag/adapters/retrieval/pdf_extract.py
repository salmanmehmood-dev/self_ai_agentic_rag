"""E06: validate PDF magic bytes + extract text via PyMuPDF."""

from __future__ import annotations

from typing import Any

import pymupdf

from agentic_crag.domain.exceptions import MalformedPdfError

PDF_MAGIC = b"%PDF-"
MIN_CHARS_PER_PAGE = 20

_open_pdf: Any = pymupdf.open


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
        doc = _open_pdf(stream=data, filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        raise MalformedPdfError(
            f"Unparseable PDF: {exc}",
            code="ERR_SCANNED_OR_EMPTY_PDF",
        ) from exc

    try:
        page_count = int(doc.page_count)
        if page_count < 1:
            raise MalformedPdfError("PDF has zero pages", code="ERR_SCANNED_OR_EMPTY_PDF")

        parts: list[str] = []
        for i in range(page_count):
            page = doc.load_page(i)
            text = str(page.get_text("text") or "").strip()
            if len(text) < MIN_CHARS_PER_PAGE:
                raise MalformedPdfError(
                    f"Page {i + 1} yielded < {MIN_CHARS_PER_PAGE} characters "
                    "(scanned or empty PDF)",
                    code="ERR_SCANNED_OR_EMPTY_PDF",
                )
            parts.append(text)
        return "\n\n".join(parts)
    finally:
        doc.close()
