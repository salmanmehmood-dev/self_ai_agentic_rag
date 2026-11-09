"""Optional Phoenix OTEL registration.

Caller: agentic_crag.api.main lifespan via setup_phoenix_tracing().
No other tracing module exists under adapters/. User: Implement the plan.
"""

from __future__ import annotations

import importlib
import logging

_log = logging.getLogger("agentic_crag.phoenix")


def setup_phoenix_tracing(
    *,
    endpoint: str | None,
    project_name: str = "agentic-crag",
) -> bool:
    """Register Phoenix OTEL exporter. Returns True if enabled."""
    if not endpoint:
        return False
    try:
        phoenix_otel = importlib.import_module("phoenix.otel")
    except ImportError:
        _log.warning("arize-phoenix-otel not installed; skipping Phoenix tracing")
        return False

    register = phoenix_otel.register
    register(
        project_name=project_name,
        endpoint=endpoint,
        batch=True,
        auto_instrument=True,
    )
    _log.info("Phoenix tracing enabled endpoint=%s project=%s", endpoint, project_name)
    return True
