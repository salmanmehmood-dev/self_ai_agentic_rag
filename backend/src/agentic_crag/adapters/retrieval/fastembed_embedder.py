"""Local FastEmbed dense embedder (CPU).

Import of ``fastembed`` is deferred so cloud boots never load ONNX.
Sync inference runs in ``asyncio.to_thread`` so the event loop stays responsive.
BGE query vectors use ``query_embed`` (asymmetric retrieval).
"""

from __future__ import annotations

import asyncio
from typing import Any


def _import_text_embedding() -> Any:
    from fastembed import TextEmbedding

    return TextEmbedding


class FastEmbedEmbedder:
    def __init__(
        self,
        *,
        model_name: str = "BAAI/bge-small-en-v1.5",
        dims: int = 384,
    ) -> None:
        self._model_name = model_name
        self._dims = dims
        self._model: Any | None = None

    def _load_model(self) -> Any:
        if self._model is None:
            text_embedding = _import_text_embedding()
            self._model = text_embedding(model_name=self._model_name)
        return self._model

    def _vectors_from_raw(self, raw: Any) -> list[list[float]]:
        vectors: list[list[float]] = []
        for item in raw:
            vec = [float(x) for x in item]
            if len(vec) != self._dims:
                msg = f"FastEmbed returned {len(vec)} dims; expected {self._dims}"
                raise RuntimeError(msg)
            vectors.append(vec)
        return vectors

    def _embed_documents_sync(self, texts: list[str]) -> list[list[float]]:
        model = self._load_model()
        return self._vectors_from_raw(model.embed(texts))

    def _embed_query_sync(self, text: str) -> list[float]:
        model = self._load_model()
        # BGE is asymmetric: queries must use query_embed (instruction prefix).
        vectors = self._vectors_from_raw(model.query_embed([text]))
        return vectors[0]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return await asyncio.to_thread(self._embed_documents_sync, texts)

    async def embed_query(self, text: str) -> list[float]:
        return await asyncio.to_thread(self._embed_query_sync, text)
