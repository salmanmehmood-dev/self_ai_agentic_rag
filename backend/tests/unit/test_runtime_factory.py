import pytest

from agentic_crag.adapters.llm.gateway import LLMGateway
from agentic_crag.adapters.llm.ollama_client import OllamaClient
from agentic_crag.adapters.retrieval.embedder import GeminiEmbedder
from agentic_crag.adapters.retrieval.fastembed_embedder import FastEmbedEmbedder
from agentic_crag.adapters.runtime_factory import build_embedder, build_llm
from agentic_crag.config import Settings


def _local_settings() -> Settings:
    return Settings(
        local_dev_mode=True,
        free_models_only=False,
    )


def _cloud_settings(
    *,
    gemini_api_key: str | None = "gemini-key",
    groq_api_key: str | None = "groq-key",
    routeway_api_key: str | None = None,
) -> Settings:
    return Settings(
        local_dev_mode=False,
        free_models_only=False,
        gemini_api_key=gemini_api_key,
        groq_api_key=groq_api_key,
        routeway_api_key=routeway_api_key,
    )


def test_build_llm_local_returns_ollama() -> None:
    llm = build_llm(_local_settings())
    assert isinstance(llm, OllamaClient)
    assert not isinstance(llm, LLMGateway)


def test_build_embedder_local_returns_fastembed() -> None:
    embedder = build_embedder(_local_settings())
    assert isinstance(embedder, FastEmbedEmbedder)


def test_build_llm_cloud_returns_gateway() -> None:
    llm = build_llm(_cloud_settings())
    assert isinstance(llm, LLMGateway)


def test_build_embedder_cloud_returns_gemini() -> None:
    embedder = build_embedder(_cloud_settings())
    assert isinstance(embedder, GeminiEmbedder)


def test_build_llm_cloud_routeway_only_fallback() -> None:
    llm = build_llm(
        _cloud_settings(groq_api_key=None, routeway_api_key="route-key")
    )
    assert isinstance(llm, LLMGateway)


def test_build_llm_cloud_missing_gemini_raises() -> None:
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        build_llm(_cloud_settings(gemini_api_key=None))


def test_build_llm_cloud_missing_fallback_raises() -> None:
    with pytest.raises(ValueError, match="GROQ_API_KEY|ROUTEWAY_API_KEY"):
        build_llm(_cloud_settings(groq_api_key=None, routeway_api_key=None))


def test_build_embedder_cloud_missing_gemini_raises() -> None:
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        build_embedder(_cloud_settings(gemini_api_key=None))
