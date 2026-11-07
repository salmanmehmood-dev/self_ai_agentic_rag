"""E06 PDF magic + sparse-page rejection."""

from __future__ import annotations

import io

import pytest
from pypdf import PdfWriter

from agentic_crag.adapters.retrieval.pdf_extract import extract_pdf_text
from agentic_crag.domain.exceptions import MalformedPdfError


def test_rejects_non_pdf_magic() -> None:
    with pytest.raises(MalformedPdfError) as exc:
        extract_pdf_text(b"not-a-pdf")
    assert exc.value.code == "ERR_SCANNED_OR_EMPTY_PDF"


def test_rejects_empty_page_pdf() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    with pytest.raises(MalformedPdfError) as exc:
        extract_pdf_text(buf.getvalue())
    assert "ERR_SCANNED_OR_EMPTY_PDF" in exc.value.code
