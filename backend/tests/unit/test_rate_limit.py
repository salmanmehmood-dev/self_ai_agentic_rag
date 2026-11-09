"""Behaviour: client-side RPM/RPD throttle + IP chat gate.

Modules: rate_limit.py, tier_presets.py. Existing tests: none for these.
User: "implement ratelimiting for llm ... free and paid we can replace in production".
"""

from __future__ import annotations

import pytest

from agentic_crag.adapters.llm.rate_limit import AsyncIpRpmLimiter, AsyncRateLimiter
from agentic_crag.adapters.llm.tier_presets import ProviderLimits, get_tier_limits
from agentic_crag.domain.exceptions import ProviderQuotaError


@pytest.mark.asyncio
async def test_rpm_blocks_then_allows() -> None:
    lim = AsyncRateLimiter(
        ProviderLimits(rpm=2, rpd=100, min_interval_s=0.0, max_wait_s=2.0),
        name="test",
    )
    await lim.acquire()
    await lim.acquire()
    with pytest.raises(ProviderQuotaError):
        await lim.acquire()


@pytest.mark.asyncio
async def test_ip_limiter() -> None:
    ip = AsyncIpRpmLimiter(rpm=2)
    assert await ip.allow("1.1.1.1")
    assert await ip.allow("1.1.1.1")
    assert not await ip.allow("1.1.1.1")
    assert await ip.allow("2.2.2.2")


def test_paid_tier_higher_than_free() -> None:
    free = get_tier_limits("free")
    paid = get_tier_limits("paid")
    assert paid.gemini.rpm > free.gemini.rpm
    assert paid.chat_per_ip_rpm > free.chat_per_ip_rpm
