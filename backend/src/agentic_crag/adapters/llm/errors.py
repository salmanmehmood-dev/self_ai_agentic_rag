"""Map provider SDK exceptions into domain provider errors."""

from __future__ import annotations

from agentic_crag.domain.exceptions import ProviderQuotaError, ProviderUnavailableError


def raise_mapped_provider_error(exc: BaseException, *, provider: str) -> None:
    """Re-raise *exc* as a domain error when it looks like 429/503; else re-raise as-is."""
    status = _extract_status(exc)
    message = f"{provider} error: {exc}"
    if status == 429:
        raise ProviderQuotaError(message) from exc
    if status == 402:
        # Routeway / OpenAI-compatible: insufficient credits
        raise ProviderQuotaError(message) from exc
    if status == 503:
        raise ProviderUnavailableError(message) from exc
    raise exc


def _extract_status(exc: BaseException) -> int | None:
    for attr in ("status_code", "code", "status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    text = str(exc).upper()
    if "429" in text or "RESOURCE_EXHAUSTED" in text:
        return 429
    if "402" in text or "INSUFFICIENT FUNDS" in text or "INSUFFICIENT_QUOTA" in text:
        return 402
    if "503" in text or "UNAVAILABLE" in text:
        return 503
    return None
