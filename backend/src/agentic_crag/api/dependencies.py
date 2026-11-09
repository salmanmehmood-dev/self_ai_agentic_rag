"""FastAPI dependency injection — graph ports from app.state."""

from __future__ import annotations

from typing import Any

from fastapi import Request

from agentic_crag.api.error_envelope import http_error
from agentic_crag.config import settings


def get_compiled_graph(request: Request) -> Any:
    graph = getattr(request.app.state, "graph", None)
    if graph is None:
        raise http_error(
            status_code=503,
            code="ERR_GRAPH_NOT_READY",
            developer_message=(
                "app.state.graph is None — set GEMINI_API_KEY and GROQ_API_KEY "
                "in repo-root .env (or backend/.env), then restart uvicorn."
            ),
            expose_developer=settings.expose_developer_errors,
        )
    return graph


def get_failover_buffer(request: Request) -> list[Any]:
    buf = getattr(request.app.state, "failover_events", None)
    if buf is None:
        buf = []
        request.app.state.failover_events = buf
    return buf
