"""Local FastEmbed dense embedder (CPU)."""

from __future__ import annotations

from fastembed import TextEmbedding


class FastEmbedEmbedder:
    def __init__(
        self,
        *,
        model_name: str = "BAAI/bge-small-en-v1.5",
        dims: int = 384,
    ) -> None:
        self._model_name = model_name
        self._dims = dims
        self._model: TextEmbedding | None = None

    def _get_model(self) -> TextEmbedding:
        if self._model is None:
            self._model = TextEmbedding(model_name=self._model_name)
        return self._model

    def _embed_sync(self, texts: list[str]) -> list[list[float]]:
        raw = self._get_model().embed(texts)
        vectors: list[list[float]] = []
        for item in raw:
            vec = [float(x) for x in item]
            if len(vec) != self._dims:
                msg = f"FastEmbed returned {len(vec)} dims; expected {self._dims}"
                raise RuntimeError(msg)
            vectors.append(vec)
        return vectors

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._embed_sync(texts)

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self.embed_documents([text])
        return vectors[0]
