"""Dense embedders: Gemini primary + deterministic hash stub for tests."""

from __future__ import annotations

import hashlib
import math

from google import genai
from google.genai import types

from agentic_crag.adapters.llm.errors import raise_mapped_provider_error


class HashEmbedder:
    """Deterministic dense vectors for unit tests (no network)."""

    def __init__(self, dims: int = 768) -> None:
        self._dims = dims

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._embed_one(text)

    def _embed_one(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        raw = [((digest[i % len(digest)] / 255.0) * 2 - 1) for i in range(self._dims)]
        norm = math.sqrt(sum(x * x for x in raw)) or 1.0
        return [x / norm for x in raw]


class GeminiEmbedder:
    """Gemini dense embedder.

    Spec HLD listed ``text-embedding-004`` (768-d); that model was shut down
    2026-01-14. Use ``gemini-embedding-001`` with ``output_dimensionality=768``
    so Qdrant collection size stays aligned with ``settings.embedding_dims``.
    """

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "gemini-embedding-001",
        dims: int = 768,
        client: genai.Client | None = None,
    ) -> None:
        self._model = model
        self._dims = dims
        # Embeddings live on v1beta; keep LLM generate on its own client.
        self._client = client or genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(api_version="v1beta"),
        )

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        try:
            result = await self._client.aio.models.embed_content(
                model=self._model,
                contents=texts,
                config=types.EmbedContentConfig(output_dimensionality=self._dims),
            )
        except Exception as exc:  # noqa: BLE001
            raise_mapped_provider_error(exc, provider="gemini-embed")
        embeddings = result.embeddings
        if embeddings is None:
            msg = "Gemini embedder returned no embeddings"
            raise RuntimeError(msg)
        vectors: list[list[float]] = []
        for item in embeddings:
            values = item.values
            if values is None:
                msg = "Gemini embedder returned empty values"
                raise RuntimeError(msg)
            vectors.append(list(values))
        return vectors

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self.embed_documents([text])
        return vectors[0]
