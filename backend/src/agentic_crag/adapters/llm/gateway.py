"""LLM gateway: rate-limit → Gemini → Groq → optional Routeway failover."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from pydantic import BaseModel
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
    wait_none,
)
from tenacity.wait import wait_base

from agentic_crag.adapters.llm.rate_limit import AsyncRateLimiter
from agentic_crag.domain.events import ProviderFailoverData
from agentic_crag.domain.exceptions import ProviderQuotaError, ProviderUnavailableError
from agentic_crag.domain.ports import LLMClientPort

T = TypeVar("T", bound=BaseModel)

FailoverCallback = Callable[[ProviderFailoverData], Awaitable[None] | None]

_TRANSIENT = (ProviderQuotaError, ProviderUnavailableError)


class LLMGateway:
    """Implements LLMClientPort with client-side RPM, E02 retry + failover chain."""

    def __init__(
        self,
        primary: LLMClientPort,
        fallback: LLMClientPort,
        *,
        primary_name: str = "gemini-2.5-flash",
        fallback_name: str = "groq-gpt-oss-120b",
        tertiary: LLMClientPort | None = None,
        tertiary_name: str = "routeway",
        on_failover: FailoverCallback | None = None,
        disable_retry_wait: bool = False,
        primary_limiter: AsyncRateLimiter | None = None,
        fallback_limiter: AsyncRateLimiter | None = None,
        tertiary_limiter: AsyncRateLimiter | None = None,
        retry_attempts: int = 2,
        retry_base_s: float = 1.0,
        retry_max_s: float = 16.0,
        request_timeout_s: float = 45.0,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._tertiary = tertiary
        self._primary_name = primary_name
        self._fallback_name = fallback_name
        self._tertiary_name = tertiary_name
        self._on_failover = on_failover
        self._primary_limiter = primary_limiter
        self._fallback_limiter = fallback_limiter
        self._tertiary_limiter = tertiary_limiter
        self._retry_attempts = max(1, retry_attempts)
        self._request_timeout_s = request_timeout_s
        wait: wait_base
        if disable_retry_wait:
            wait = wait_none()
        else:
            wait = wait_exponential_jitter(
                initial=retry_base_s,
                max=retry_max_s,
                jitter=1.0,
            )
        self._wait = wait

    async def _call(
        self,
        client: LLMClientPort,
        limiter: AsyncRateLimiter | None,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[T],
        temperature: float,
    ) -> T:
        if limiter is not None:
            await limiter.acquire()
        try:
            return await asyncio.wait_for(
                client.generate_structured(
                    system_prompt,
                    user_prompt,
                    response_schema,
                    temperature,
                ),
                timeout=self._request_timeout_s,
            )
        except TimeoutError as exc:
            raise ProviderUnavailableError(
                f"LLM request timed out after {self._request_timeout_s}s",
                code="E02_PROVIDER_UNAVAILABLE",
            ) from exc

    async def _call_with_retry(
        self,
        client: LLMClientPort,
        limiter: AsyncRateLimiter | None,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[T],
        temperature: float,
    ) -> T:
        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(_TRANSIENT),
            stop=stop_after_attempt(self._retry_attempts),
            wait=self._wait,
            reraise=True,
        ):
            with attempt:
                return await self._call(
                    client,
                    limiter,
                    system_prompt,
                    user_prompt,
                    response_schema,
                    temperature,
                )
        msg = "unreachable retry path"
        raise RuntimeError(msg)

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[T],
        temperature: float = 0.0,
    ) -> T:
        try:
            return await self._call_with_retry(
                self._primary,
                self._primary_limiter,
                system_prompt,
                user_prompt,
                response_schema,
                temperature,
            )
        except _TRANSIENT as primary_exc:
            await self._emit_failover(
                self._primary_name,
                self._fallback_name,
                str(primary_exc),
            )
            try:
                return await self._call_with_retry(
                    self._fallback,
                    self._fallback_limiter,
                    system_prompt,
                    user_prompt,
                    response_schema,
                    temperature,
                )
            except _TRANSIENT as fallback_exc:
                if self._tertiary is None:
                    raise fallback_exc
                await self._emit_failover(
                    self._fallback_name,
                    self._tertiary_name,
                    str(fallback_exc),
                )
                return await self._call(
                    self._tertiary,
                    self._tertiary_limiter,
                    system_prompt,
                    user_prompt,
                    response_schema,
                    temperature,
                )

    async def _emit_failover(self, from_provider: str, to_provider: str, reason: str) -> None:
        if self._on_failover is None:
            return
        payload = ProviderFailoverData(
            from_provider=from_provider,
            to_provider=to_provider,
            reason=reason,
        )
        result = self._on_failover(payload)
        if result is not None:
            await result


# Backward-compatible alias
FailoverLLMGateway = LLMGateway
