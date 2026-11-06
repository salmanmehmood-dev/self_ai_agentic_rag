"""Mocked Qdrant hybrid store + markdown ingest (no live Qdrant)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from agentic_crag.adapters.retrieval.embedder import HashEmbedder
from agentic_crag.adapters.retrieval.ingest import MarkdownIngestService
from agentic_crag.adapters.retrieval.qdrant_hybrid import QdrantHybridStore
from agentic_crag.domain.entities import DocumentChunk


def _mock_client(*, exists: bool = False, points: list[object] | None = None) -> AsyncMock:
    client = AsyncMock()
    collections = MagicMock()
    collections.collections = [SimpleNamespace(name="crag_chunks")] if exists else []
    client.get_collections.return_value = collections
    info = MagicMock()
    info.points_count = 2 if exists else 0
    client.get_collection.return_value = info
    client.create_collection = AsyncMock()
    client.upsert = AsyncMock()
    query = MagicMock()
    query.points = points or []
    client.query_points.return_value = query
    return client


@pytest.mark.asyncio
async def test_upsert_chunks_creates_collection_and_writes_points() -> None:
    client = _mock_client(exists=False)
    store = QdrantHybridStore(client, HashEmbedder(dims=8), embedding_dims=8)
    chunks = [
        DocumentChunk(
            chunk_id="11111111-1111-4111-8111-111111111111",
            source_file="a.md",
            section_header="A",
            text="[Source: a.md | Section: A]\nAlpha failover content here.",
        )
    ]

    written = await store.upsert_chunks(chunks)

    assert written == 1
    client.create_collection.assert_awaited_once()
    client.upsert.assert_awaited_once()


@pytest.mark.asyncio
async def test_retrieve_hybrid_maps_payloads() -> None:
    point = SimpleNamespace(
        id="11111111-1111-4111-8111-111111111111",
        score=0.91,
        payload={
            "chunk_id": "11111111-1111-4111-8111-111111111111",
            "source_file": "a.md",
            "section_header": "A",
            "text": "Alpha text about failover",
            "source_type": "corpus",
        },
    )
    client = _mock_client(exists=True, points=[point])
    store = QdrantHybridStore(client, HashEmbedder(dims=8), embedding_dims=8)

    results = await store.retrieve_hybrid("failover", top_k=5)

    assert len(results) == 1
    assert results[0].source_file == "a.md"
    assert results[0].rrf_score == 0.91
    client.query_points.assert_awaited_once()


@pytest.mark.asyncio
async def test_markdown_ingest_service_chunks_then_upserts() -> None:
    client = _mock_client(exists=True)
    store = QdrantHybridStore(client, HashEmbedder(dims=8), embedding_dims=8)
    service = MarkdownIngestService(store)

    count = await service.ingest_markdown(
        "sla.md",
        "# Policy\n\nRetries happen after quota exhaustion on the primary provider.\n",
    )

    assert count >= 1
    client.upsert.assert_awaited_once()
