"""FastAPI dependency injection — graph ports from app.state."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request


def get_compiled_graph(request: Request) -> Any:
    graph = getattr(request.app.state, "graph", None)
    if graph is None:
        raise HTTPException(
            status_code=503,
            detail="Chat graph not configured (missing LLM/retriever wiring)",
        )
    return graph


def get_failover_buffer(request: Request) -> list[Any]:
    buf = getattr(request.app.state, "failover_events", None)
    if buf is None:
        buf = []
        request.app.state.failover_events = buf
    return buf
