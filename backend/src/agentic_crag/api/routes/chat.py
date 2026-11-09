"""POST /api/v1/chat/stream — typed SSE (E05 disconnect cancel)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from agentic_crag.adapters.llm.rate_limit import AsyncIpRpmLimiter
from agentic_crag.api.dependencies import get_compiled_graph, get_failover_buffer
from agentic_crag.api.error_envelope import http_error
from agentic_crag.api.schemas import ChatRequest
from agentic_crag.api.streaming import stream_chat_events
from agentic_crag.config import settings

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"


@router.post("/stream")
async def chat_stream(body: ChatRequest, request: Request) -> StreamingResponse:
    limiter = getattr(request.app.state, "chat_ip_limiter", None)
    if isinstance(limiter, AsyncIpRpmLimiter):
        allowed = await limiter.allow(_client_ip(request))
        if not allowed:
            raise http_error(
                status_code=429,
                code="ERR_CHAT_RATE_LIMIT",
                developer_message=(
                    f"chat_per_ip_rpm exceeded for {_client_ip(request)} "
                    f"(tier={settings.llm_tier})"
                ),
                user_message=(
                    "Too many chat requests from your network. "
                    "Wait a minute and try again."
                ),
                expose_developer=settings.expose_developer_errors,
            )

    graph = get_compiled_graph(request)
    failovers = get_failover_buffer(request)

    async def event_gen() -> AsyncIterator[str]:
        async for chunk in stream_chat_events(
            graph=graph,
            query=body.query,
            session_id=body.session_id,
            thread_id=body.thread_id or body.session_id,
            failover_events=failovers,
            is_disconnected=request.is_disconnected,
        ):
            yield chunk

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def attach_graph(app: Any, graph: Any) -> None:
    app.state.graph = graph
    app.state.failover_events = []
