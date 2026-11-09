"""Lifespan / runtime collection+dims contracts (mocked; no live Qdrant)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agentic_crag.adapters.retrieval.qdrant_hybrid import QdrantHybridStore
from agentic_crag.config import Settings
from agentic_crag.domain.exceptions import EmbeddingDimensionMismatchError


class _StubEmbedder:
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 384 for _ in texts]

    async def embed_query(self, text: str) -> list[float]:
        return [0.0] * 384


def test_local_vs_cloud_active_collection_and_dims() -> None:
    local = Settings(local_dev_mode=True, free_models_only=False)
    cloud = Settings(
        local_dev_mode=False,
        free_models_only=False,
        embedding_dims=768,
        qdrant_collection="crag_chunks",
    )
    assert local.active_qdrant_collection == "crag_chunks_local"
    assert local.active_embedding_dims == 384
    assert cloud.active_qdrant_collection == "crag_chunks"
    assert cloud.active_embedding_dims == 768


@pytest.mark.asyncio
async def test_boot_fails_on_dim_mismatch_when_collection_exists() -> None:
    """Mirrors lifespan: ensure_collection before sample bootstrap."""
    client = MagicMock()
    coll = MagicMock()
    coll.name = "crag_chunks_local"
    client.get_collections = AsyncMock(return_value=MagicMock(collections=[coll]))
    dense = MagicMock()
    dense.size = 768
    client.get_collection = AsyncMock(
        return_value=MagicMock(
            config=MagicMock(params=MagicMock(vectors={"dense": dense})),
            points_count=10,
        )
    )
    store = QdrantHybridStore(
        client,
        _StubEmbedder(),
        collection_name="crag_chunks_local",
        embedding_dims=384,
    )
    with pytest.raises(EmbeddingDimensionMismatchError) as ei:
        await store.ensure_collection()
    assert ei.value.code == "ERR_EMBED_DIM_MISMATCH"


def test_cloud_factory_does_not_bind_fastembed_at_import() -> None:
    import agentic_crag.adapters.runtime_factory as rf

    assert "FastEmbedEmbedder" not in rf.__dict__
