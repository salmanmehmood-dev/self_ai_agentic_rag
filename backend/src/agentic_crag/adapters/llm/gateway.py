"""Dual-provider LLM gateway: Gemini primary → Groq on 429/503 after one retry."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

from pydantic import BaseModel
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
    wait_none,
    wait_random,
)

from agentic_crag.domain.events import ProviderFailoverData
from agentic_crag.domain.exceptions import ProviderQuotaError, ProviderUnavailableError
from agentic_crag.domain.ports import LLMClientPort

T = TypeVar("T", bound=BaseModel)

FailoverCallback = Callable[[ProviderFailoverData], Awaitable[None] | None]

_TRANSIENT = (ProviderQuotaError, ProviderUnavailableError)


class FailoverLLMGateway:
    """Implements LLMClientPort with E02 retry + provider failover."""

    def __init__(
        self,
        primary: LLMClientPort,
        fallback: LLMClientPort,
        *,
        primary_name: str = "gemini-2.5-flash",
        fallback_name: str = "groq-gpt-oss-120b",
        on_failover: FailoverCallback | None = None,
        disable_retry_wait: bool = False,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._primary_name = primary_name
        self._fallback_name = fallback_name
        self._on_failover = on_failover
        self._wait = wait_none() if disable_retry_wait else (wait_fixed(2) + wait_random(0, 1))

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[T],
        temperature: float = 0.0,
    ) -> T:
        try:
            async for attempt in AsyncRetrying(
                retry=retry_if_exception_type(_TRANSIENT),
                stop=stop_after_attempt(2),
                wait=self._wait,
                reraise=True,
            ):
                with attempt:
                    return await self._primary.generate_structured(
                        system_prompt,
                        user_prompt,
                        response_schema,
                        temperature,
                    )
        except _TRANSIENT as exc:
            reason = str(exc)
            await self._emit_failover(reason)
            return await self._fallback.generate_structured(
                system_prompt,
                user_prompt,
                response_schema,
                temperature,
            )

        msg = "unreachable failover path"
        raise RuntimeError(msg)

    async def _emit_failover(self, reason: str) -> None:
        if self._on_failover is None:
            return
        payload = ProviderFailoverData(
            from_provider=self._primary_name,
            to_provider=self._fallback_name,
            reason=reason,
        )
        result = self._on_failover(payload)
        if result is not None:
            await result
