"""Markdown-aware chunker with contextual headers and deterministic UUIDv5 IDs."""

from __future__ import annotations

import hashlib
import re
import uuid

from agentic_crag.domain.entities import DocumentChunk

_HEADER_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)


def chunk_markdown(
    source_file: str,
    markdown: str,
    *,
    max_chars: int = 1200,
) -> list[DocumentChunk]:
    """Split markdown on headers; prepend `[Source | Section]` to each chunk body."""
    doc_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    sections = _split_sections(markdown)
    chunks: list[DocumentChunk] = []
    index = 0
    for section_header, body in sections:
        for piece in _split_long(body, max_chars):
            text = piece.strip()
            if len(text) < 20:
                continue
            header = section_header or "Document"
            contextual = f"[Source: {source_file} | Section: {header}]\n{text}"
            chunk_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{doc_hash}:{index}"))
            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    source_file=source_file,
                    section_header=header,
                    text=contextual,
                    source_type="corpus",
                )
            )
            index += 1
    return chunks


def _split_sections(markdown: str) -> list[tuple[str, str]]:
    matches = list(_HEADER_RE.finditer(markdown))
    if not matches:
        return [("", markdown)]

    sections: list[tuple[str, str]] = []
    if matches[0].start() > 0:
        preamble = markdown[: matches[0].start()].strip()
        if preamble:
            sections.append(("", preamble))

    for i, match in enumerate(matches):
        header = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        body = markdown[start:end].strip()
        sections.append((header, body))
    return sections


def _split_long(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text] if text else []
    parts: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            split_at = text.rfind("\n\n", start, end)
            if split_at <= start:
                split_at = text.rfind(" ", start, end)
            if split_at > start:
                end = split_at
        parts.append(text[start:end])
        start = end
    return parts
