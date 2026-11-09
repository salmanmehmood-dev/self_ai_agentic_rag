"""Composition-root factory: local Ollama/FastEmbed vs cloud LLMGateway/Gemini."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from agentic_crag.adapters.llm.gateway import LLMGateway
from agentic_crag.adapters.llm.gemini_client import GeminiClient
from agentic_crag.adapters.llm.groq_client import GroqClient
from agentic_crag.adapters.llm.ollama_client import OllamaClient
from agentic_crag.adapters.llm.rate_limit import AsyncRateLimiter
from agentic_crag.adapters.llm.routeway_client import RoutewayClient
from agentic_crag.adapters.retrieval.embedder import GeminiEmbedder
from agentic_crag.config import Settings
from agentic_crag.domain.ports import EmbedderPort, LLMClientPort

FailoverCb = Callable[..., Awaitable[None] | None]


def build_llm(
    settings: Settings,
    *,
    on_failover: FailoverCb | None = None,
) -> LLMClientPort:
    if settings.local_dev_mode:
        return OllamaClient(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout_s=settings.ollama_timeout_s,
        )

    has_fallback = bool(settings.groq_api_key or settings.routeway_api_key)
    if not settings.gemini_api_key or not has_fallback:
        missing = [
            name
            for name, val in (
                ("GEMINI_API_KEY", settings.gemini_api_key),
                ("GROQ_API_KEY|ROUTEWAY_API_KEY", has_fallback or None),
            )
            if not val
        ]
        raise ValueError(
            "Cloud runtime requires API keys; missing: " + ", ".join(missing)
        )

    limits = settings.tier_limits()
    gemini_lim = AsyncRateLimiter(limits.gemini, name="gemini")
    primary = GeminiClient(settings.gemini_api_key, model=settings.gemini_model)
    primary_name = settings.gemini_model

    tertiary: RoutewayClient | None = None
    tertiary_lim: AsyncRateLimiter | None = None
    tertiary_name = f"routeway-{settings.routeway_model}"
    if settings.routeway_api_key:
        tertiary = RoutewayClient(
            settings.routeway_api_key,
            model=settings.routeway_model,
            base_url=settings.routeway_base_url,
            timeout_s=settings.llm_request_timeout_s,
        )
        tertiary_lim = AsyncRateLimiter(limits.routeway, name="routeway")

    if settings.groq_api_key:
        fallback: LLMClientPort = GroqClient(
            settings.groq_api_key, model=settings.groq_model
        )
        fallback_name = f"groq-{settings.groq_model}"
        fallback_lim: AsyncRateLimiter | None = AsyncRateLimiter(
            limits.groq, name="groq"
        )
        gateway_tertiary = tertiary
        gateway_tertiary_lim = tertiary_lim
        gateway_tertiary_name = tertiary_name
    else:
        assert tertiary is not None  # has_fallback guarantees Routeway
        fallback = tertiary
        fallback_name = tertiary_name
        fallback_lim = tertiary_lim
        gateway_tertiary = None
        gateway_tertiary_lim = None
        gateway_tertiary_name = tertiary_name

    return LLMGateway(
        primary,
        fallback,
        primary_name=primary_name,
        fallback_name=fallback_name,
        tertiary=gateway_tertiary,
        tertiary_name=gateway_tertiary_name,
        on_failover=on_failover,
        primary_limiter=gemini_lim,
        fallback_limiter=fallback_lim,
        tertiary_limiter=gateway_tertiary_lim,
        retry_attempts=limits.retry_attempts,
        retry_base_s=limits.retry_base_s,
        retry_max_s=limits.retry_max_s,
        request_timeout_s=settings.llm_request_timeout_s,
    )


def build_embedder(settings: Settings) -> EmbedderPort:
    if settings.local_dev_mode:
        # Lazy import: cloud boots must not load fastembed/ONNX.
        from agentic_crag.adapters.retrieval.fastembed_embedder import (
            FastEmbedEmbedder,
        )

        return FastEmbedEmbedder(
            model_name=settings.local_embed_model,
            dims=settings.local_embedding_dims,
        )

    if not settings.gemini_api_key:
        raise ValueError("Cloud runtime requires API keys; missing: GEMINI_API_KEY")

    limits = settings.tier_limits()
    embed_lim = AsyncRateLimiter(limits.embed, name="gemini-embed")
    return GeminiEmbedder(
        settings.gemini_api_key,
        dims=settings.embedding_dims,
        model=settings.embed_model,
        rate_limiter=embed_lim,
    )
