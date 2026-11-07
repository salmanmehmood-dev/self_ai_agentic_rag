"""Mocked tests for FailoverLLMGateway (no live LLM calls)."""

from __future__ import annotations

from typing import TypeVar
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel

from agentic_crag.adapters.llm.errors import raise_mapped_provider_error
from agentic_crag.adapters.llm.gateway import FailoverLLMGateway
from agentic_crag.domain.events import ProviderFailoverData
from agentic_crag.domain.exceptions import ProviderQuotaError, ProviderUnavailableError

T = TypeVar("T", bound=BaseModel)


class _RouteOut(BaseModel):
    route: str


class _FakeClient:
    def __init__(self, side_effect: object | None = None, result: _RouteOut | None = None) -> None:
        self.generate_structured = AsyncMock(side_effect=side_effect, return_value=result)


def test_raise_mapped_provider_error_429() -> None:
    class _Err(Exception):
        status_code = 429

    with pytest.raises(ProviderQuotaError):
        raise_mapped_provider_error(_Err("quota"), provider="gemini")


def test_raise_mapped_provider_error_503() -> None:
    class _Err(Exception):
        status_code = 503

    with pytest.raises(ProviderUnavailableError):
        raise_mapped_provider_error(_Err("down"), provider="gemini")


@pytest.mark.asyncio
async def test_gateway_uses_primary_on_success() -> None:
    primary = _FakeClient(result=_RouteOut(route="rag"))
    fallback = _FakeClient(result=_RouteOut(route="direct"))
    gateway = FailoverLLMGateway(primary, fallback, disable_retry_wait=True)

    out = await gateway.generate_structured("sys", "user", _RouteOut)

    assert out.route == "rag"
    primary.generate_structured.assert_awaited_once()
    fallback.generate_structured.assert_not_awaited()


@pytest.mark.asyncio
async def test_gateway_retries_then_failovers_on_429() -> None:
    primary = _FakeClient(side_effect=ProviderQuotaError("429 RESOURCE_EXHAUSTED"))
    fallback = _FakeClient(result=_RouteOut(route="fallback"))
    events: list[ProviderFailoverData] = []

    async def on_failover(data: ProviderFailoverData) -> None:
        events.append(data)

    gateway = FailoverLLMGateway(
        primary,
        fallback,
        on_failover=on_failover,
        disable_retry_wait=True,
    )

    out = await gateway.generate_structured("sys", "user", _RouteOut)

    assert out.route == "fallback"
    assert primary.generate_structured.await_count == 2
    fallback.generate_structured.assert_awaited_once()
    assert len(events) == 1
    assert events[0].from_provider == "gemini-2.5-flash"
    assert events[0].to_provider == "groq-gpt-oss-120b"
