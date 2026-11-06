"""Chunker behaviour: headers, contextual prefix, stable UUIDv5 ids."""

from agentic_crag.adapters.retrieval.chunker import chunk_markdown

_SAMPLE = """# Failover Policy

The system retries Gemini once on 429 then switches to Groq.

## Timeout Rules

Web search uses a four second timeout before degraded mode.
"""


def test_chunk_markdown_splits_on_headers_and_prefixes_source() -> None:
    chunks = chunk_markdown("sla.md", _SAMPLE)
    assert len(chunks) >= 2
    assert all(c.source_file == "sla.md" for c in chunks)
    assert all(c.text.startswith("[Source: sla.md | Section:") for c in chunks)
    assert chunks[0].section_header == "Failover Policy"


def test_chunk_markdown_ids_are_deterministic() -> None:
    a = chunk_markdown("sla.md", _SAMPLE)
    b = chunk_markdown("sla.md", _SAMPLE)
    assert [c.chunk_id for c in a] == [c.chunk_id for c in b]
