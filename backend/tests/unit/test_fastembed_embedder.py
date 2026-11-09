from unittest.mock import MagicMock

import pytest

from agentic_crag.adapters.retrieval.fastembed_embedder import FastEmbedEmbedder


@pytest.mark.asyncio
async def test_fastembed_returns_configured_dims(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_model = MagicMock()

    def _fake_embed(texts: list[str]) -> object:
        return iter([[0.1] * 384 for _ in texts])

    fake_model.embed.side_effect = _fake_embed

    def _fake_text_embedding(*_a: object, **_k: object) -> MagicMock:
        return fake_model

    monkeypatch.setattr(
        "agentic_crag.adapters.retrieval.fastembed_embedder.TextEmbedding",
        _fake_text_embedding,
    )

    emb = FastEmbedEmbedder(model_name="BAAI/bge-small-en-v1.5", dims=384)
    docs = await emb.embed_documents(["a", "b"])
    assert len(docs) == 2
    assert len(docs[0]) == 384
    q = await emb.embed_query("q")
    assert len(q) == 384
