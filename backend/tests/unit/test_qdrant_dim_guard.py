from unittest.mock import AsyncMock, MagicMock

import pytest

from agentic_crag.adapters.retrieval.qdrant_hybrid import QdrantHybridStore
from agentic_crag.domain.exceptions import EmbeddingDimensionMismatchError


class _StubEmbedder:
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 384 for _ in texts]

    async def embed_query(self, text: str) -> list[float]:
        return [0.0] * 384


@pytest.mark.asyncio
async def test_ensure_collection_raises_on_dim_mismatch() -> None:
    client = MagicMock()
    coll = MagicMock()
    coll.name = "crag_chunks_local"
    client.get_collections = AsyncMock(return_value=MagicMock(collections=[coll]))
    dense = MagicMock()
    dense.size = 768
    params = MagicMock()
    params.vectors = {"dense": dense}
    client.get_collection = AsyncMock(
        return_value=MagicMock(config=MagicMock(params=params), points_count=1)
    )

    store = QdrantHybridStore(
        client,
        _StubEmbedder(),
        collection_name="crag_chunks_local",
        embedding_dims=384,
    )
    with pytest.raises(EmbeddingDimensionMismatchError):
        await store.ensure_collection()
