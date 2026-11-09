"""Ingest markdown corpus into hybrid Qdrant store."""

from __future__ import annotations

from agentic_crag.adapters.retrieval.chunker import chunk_markdown
from agentic_crag.adapters.retrieval.qdrant_hybrid import QdrantHybridStore


class MarkdownIngestService:
    def __init__(self, store: QdrantHybridStore) -> None:
        self._store = store

    async def ingest_markdown(self, source_file: str, markdown: str) -> int:
        chunks = chunk_markdown(source_file, markdown)
        return await self._store.upsert_chunks(chunks)

    async def point_count(self) -> int:
        return await self._store.point_count()

    async def collection_exists(self) -> bool:
        return await self._store.collection_exists()

    async def reset_collection(self) -> None:
        # Caller: sample_bootstrap.ensure_sample_corpus(force=True). User chat fix.
        await self._store.reset_collection()
