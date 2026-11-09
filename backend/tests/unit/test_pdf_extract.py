"""E06 PDF magic + sparse-page rejection (PyMuPDF)."""

from __future__ import annotations

import pymupdf
import pytest

from agentic_crag.adapters.retrieval.pdf_extract import extract_pdf_text
from agentic_crag.domain.exceptions import MalformedPdfError


def test_rejects_non_pdf_magic() -> None:
    with pytest.raises(MalformedPdfError) as exc:
        extract_pdf_text(b"not-a-pdf")
    assert exc.value.code == "ERR_SCANNED_OR_EMPTY_PDF"


def test_rejects_empty_page_pdf() -> None:
    doc = pymupdf.open()
    doc.new_page()
    data = doc.tobytes()
    doc.close()
    with pytest.raises(MalformedPdfError) as exc:
        extract_pdf_text(data)
    assert "ERR_SCANNED_OR_EMPTY_PDF" in exc.value.code


def test_extracts_text_page() -> None:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Gemini failover retries then switches to Groq.")
    data = doc.tobytes()
    doc.close()
    text = extract_pdf_text(data)
    assert "failover" in text.lower()
