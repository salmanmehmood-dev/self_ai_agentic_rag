"""LLM / API tier presets (free vs paid) — swap via LLM_TIER env.

Caller: config.Settings.tier_limits() → rate_limit + gateway + chat throttle.
No prior presets module. User: "implement ratelimiting for llm and other best
practices for llms apis free and paid we can replace in production".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TierName = Literal["free", "paid"]


@dataclass(frozen=True, slots=True)
class ProviderLimits:
    rpm: int
    rpd: int
    min_interval_s: float
    max_wait_s: float = 60.0


@dataclass(frozen=True, slots=True)
class TierLimits:
    gemini: ProviderLimits
    groq: ProviderLimits
    routeway: ProviderLimits
    embed: ProviderLimits
    tavily: ProviderLimits
    chat_per_ip_rpm: int
    retry_base_s: float
    retry_max_s: float
    retry_attempts: int


# Free: under Groq freeRows (~30 RPM / 1K RPD for gpt-oss); Gemini AI Studio
# free varies (~5–15 RPM); Routeway free models (:free) ~5 RPM / 200 RPD.
_FREE = TierLimits(
    gemini=ProviderLimits(rpm=8, rpd=200, min_interval_s=7.0, max_wait_s=90.0),
    groq=ProviderLimits(rpm=20, rpd=800, min_interval_s=3.0, max_wait_s=60.0),
    routeway=ProviderLimits(rpm=5, rpd=200, min_interval_s=12.0, max_wait_s=90.0),
    embed=ProviderLimits(rpm=8, rpd=200, min_interval_s=7.0, max_wait_s=90.0),
    tavily=ProviderLimits(rpm=15, rpd=800, min_interval_s=4.0, max_wait_s=30.0),
    chat_per_ip_rpm=6,
    retry_base_s=1.0,
    retry_max_s=16.0,
    retry_attempts=2,
)

_PAID = TierLimits(
    gemini=ProviderLimits(rpm=120, rpd=10_000, min_interval_s=0.2, max_wait_s=30.0),
    groq=ProviderLimits(rpm=200, rpd=50_000, min_interval_s=0.1, max_wait_s=20.0),
    routeway=ProviderLimits(rpm=60, rpd=10_000, min_interval_s=0.5, max_wait_s=30.0),
    embed=ProviderLimits(rpm=120, rpd=10_000, min_interval_s=0.2, max_wait_s=30.0),
    tavily=ProviderLimits(rpm=60, rpd=5_000, min_interval_s=0.5, max_wait_s=20.0),
    chat_per_ip_rpm=60,
    retry_base_s=0.5,
    retry_max_s=8.0,
    retry_attempts=2,
)

_PRESETS: dict[TierName, TierLimits] = {"free": _FREE, "paid": _PAID}


def get_tier_limits(tier: TierName) -> TierLimits:
    return _PRESETS[tier]
