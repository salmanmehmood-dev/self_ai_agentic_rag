"""Async sliding-window RPM + daily RPD limiter (client-side throttle).

Caller: LLMGateway, GeminiEmbedder, WebSearchAdapter, chat IP middleware.
Raises ProviderQuotaError when max_wait exceeded. User: LLM rate limiting.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from agentic_crag.adapters.llm.tier_presets import ProviderLimits
from agentic_crag.domain.exceptions import ProviderQuotaError

# Gemini RPD resets midnight Pacific per Google docs.
_PACIFIC = ZoneInfo("America/Los_Angeles")


def _pacific_day_key(now: float | None = None) -> str:
    dt = datetime.fromtimestamp(now or time.time(), tz=UTC).astimezone(_PACIFIC)
    return dt.date().isoformat()


class AsyncRateLimiter:
    """Process-local limiter: RPM (rolling 60s) + RPD (Pacific calendar day)."""

    def __init__(self, limits: ProviderLimits, *, name: str = "provider") -> None:
        self._limits = limits
        self._name = name
        self._lock = asyncio.Lock()
        self._rpm_times: deque[float] = deque()
        self._day_key = _pacific_day_key()
        self._day_count = 0
        self._last_call = 0.0

    @property
    def name(self) -> str:
        return self._name

    def _prune_rpm(self, now: float) -> None:
        cutoff = now - 60.0
        while self._rpm_times and self._rpm_times[0] < cutoff:
            self._rpm_times.popleft()

    def _roll_day(self, now: float) -> None:
        key = _pacific_day_key(now)
        if key != self._day_key:
            self._day_key = key
            self._day_count = 0

    async def acquire(self) -> None:
        """Block until a slot is available or raise ProviderQuotaError."""
        deadline = time.monotonic() + self._limits.max_wait_s
        while True:
            async with self._lock:
                now = time.time()
                mono = time.monotonic()
                self._roll_day(now)
                self._prune_rpm(now)

                if self._day_count >= self._limits.rpd:
                    raise ProviderQuotaError(
                        f"{self._name} daily RPD limit reached "
                        f"({self._limits.rpd}/day Pacific)",
                        code="E02_PROVIDER_QUOTA",
                    )

                wait_rpm = 0.0
                if len(self._rpm_times) >= self._limits.rpm:
                    wait_rpm = max(0.0, 60.0 - (now - self._rpm_times[0]))

                wait_gap = 0.0
                if self._last_call > 0:
                    wait_gap = max(
                        0.0, self._limits.min_interval_s - (now - self._last_call)
                    )

                wait = max(wait_rpm, wait_gap)
                if wait <= 0:
                    stamp = time.time()
                    self._rpm_times.append(stamp)
                    self._last_call = stamp
                    self._day_count += 1
                    return

                if mono + wait > deadline:
                    raise ProviderQuotaError(
                        f"{self._name} rate limit wait {wait:.1f}s exceeds "
                        f"max_wait={self._limits.max_wait_s}s "
                        f"(rpm={self._limits.rpm})",
                        code="E02_PROVIDER_QUOTA",
                    )

            await asyncio.sleep(min(wait, 1.0))


class AsyncIpRpmLimiter:
    """Per-key (usually client IP) RPM gate for HTTP chat endpoint."""

    def __init__(self, rpm: int, *, max_keys: int = 10_000) -> None:
        self._rpm = max(1, rpm)
        self._max_keys = max_keys
        self._lock = asyncio.Lock()
        self._buckets: dict[str, deque[float]] = {}

    async def allow(self, key: str) -> bool:
        async with self._lock:
            now = time.time()
            bucket = self._buckets.get(key)
            if bucket is None:
                if len(self._buckets) >= self._max_keys:
                    self._buckets.pop(next(iter(self._buckets)))
                bucket = deque()
                self._buckets[key] = bucket
            cutoff = now - 60.0
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self._rpm:
                return False
            bucket.append(now)
            return True
