"""Qdrant hybrid dense + sparse retrieval with RRF fusion."""

from __future__ import annotations

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from agentic_crag.adapters.retrieval.sparse import text_to_sparse_vector
from agentic_crag.domain.entities import DocumentChunk
from agentic_crag.domain.ports import EmbedderPort

_DENSE = "dense"
_SPARSE = "sparse"


class QdrantHybridStore:
    def __init__(
        self,
        client: AsyncQdrantClient,
        embedder: EmbedderPort,
        *,
        collection_name: str = "crag_chunks",
        embedding_dims: int = 768,
    ) -> None:
        self._client = client
        self._embedder = embedder
        self._collection = collection_name
        self._dims = embedding_dims

    async def collection_exists(self) -> bool:
        names = await self._client.get_collections()
        return any(c.name == self._collection for c in names.collections)

    async def point_count(self) -> int:
        if not await self.collection_exists():
            return 0
        info = await self._client.get_collection(self._collection)
        return int(info.points_count or 0)

    async def ensure_collection(self) -> None:
        if await self.collection_exists():
            return
        await self._client.create_collection(
            collection_name=self._collection,
            vectors_config={
                _DENSE: qmodels.VectorParams(size=self._dims, distance=qmodels.Distance.COSINE),
            },
            sparse_vectors_config={
                _SPARSE: qmodels.SparseVectorParams(
                    index=qmodels.SparseIndexParams(on_disk=False),
                ),
            },
        )

    async def upsert_chunks(self, chunks: list[DocumentChunk]) -> int:
        if not chunks:
            return 0
        await self.ensure_collection()
        dense_vectors = await self._embedder.embed_documents([c.text for c in chunks])
        points = [
            qmodels.PointStruct(
                id=chunk.chunk_id,
                vector={
                    _DENSE: dense,
                    _SPARSE: text_to_sparse_vector(chunk.text),
                },
                payload={
                    "chunk_id": chunk.chunk_id,
                    "source_file": chunk.source_file,
                    "section_header": chunk.section_header,
                    "text": chunk.text,
                    "source_type": chunk.source_type,
                },
            )
            for chunk, dense in zip(chunks, dense_vectors, strict=True)
        ]
        await self._client.upsert(collection_name=self._collection, points=points)
        return len(points)

    async def retrieve_hybrid(self, query: str, top_k: int = 5) -> list[DocumentChunk]:
        if not await self.collection_exists():
            return []
        dense = await self._embedder.embed_query(query)
        sparse = text_to_sparse_vector(query)
        results = await self._client.query_points(
            collection_name=self._collection,
            prefetch=[
                qmodels.Prefetch(query=dense, using=_DENSE, limit=10),
                qmodels.Prefetch(query=sparse, using=_SPARSE, limit=10),
            ],
            query=qmodels.FusionQuery(fusion=qmodels.Fusion.RRF),
            limit=top_k,
            with_payload=True,
        )
        chunks: list[DocumentChunk] = []
        for rank, point in enumerate(results.points, start=1):
            payload = point.payload or {}
            chunks.append(
                DocumentChunk(
                    chunk_id=str(payload.get("chunk_id", point.id)),
                    source_file=str(payload.get("source_file", "")),
                    section_header=str(payload.get("section_header", "")),
                    text=str(payload.get("text", "")),
                    source_type="web" if payload.get("source_type") == "web" else "corpus",
                    rrf_score=float(point.score) if point.score is not None else None,
                    dense_rank=rank,
                    sparse_rank=rank,
                )
            )
        return chunks
