"""POST /api/v1/chat/stream — typed SSE (E05 disconnect cancel)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from agentic_crag.api.dependencies import get_compiled_graph, get_failover_buffer
from agentic_crag.api.schemas import ChatRequest
from agentic_crag.api.streaming import stream_chat_events

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("/stream")
async def chat_stream(body: ChatRequest, request: Request) -> StreamingResponse:
    graph = get_compiled_graph(request)
    failovers = get_failover_buffer(request)

    async def event_gen() -> AsyncIterator[str]:
        async for chunk in stream_chat_events(
            graph=graph,
            query=body.query,
            session_id=body.session_id,
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
