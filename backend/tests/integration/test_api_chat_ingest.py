"""ASGI integration: SSE chat + PDF ingest E06 + benchmarks (mocked graph).

Callers: pytest. Factory: create_app(lifespan_override=...).
User: "Implement the plan as specified" (1.7 integration tests).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from agentic_crag.adapters.llm.rate_limit import AsyncIpRpmLimiter
from agentic_crag.api.main import create_app
from agentic_crag.domain.entities import DocumentChunk
from agentic_crag.orchestration.graph import build_crag_graph
from agentic_crag.orchestration.schemas import (
    BatchGradeResult,
    ChunkEvaluation,
    RouteSchema,
    SynthesisResult,
    VerifySchema,
)


class _ScriptedLLM:
    def __init__(self, responses: list[Any]) -> None:
        self._responses = list(responses)
        self.calls = 0

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[Any],
        temperature: float = 0.0,
    ) -> Any:
        del system_prompt, user_prompt, temperature
        self.calls += 1
        item = self._responses.pop(0)
        assert isinstance(item, response_schema)
        return item


_CHUNK = DocumentChunk(
    chunk_id="c1",
    source_file="sla.md",
    section_header="Failover",
    text="[Source: sla.md | Section: Failover]\nRetries on 429 then Groq failover.",
)


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    llm = _ScriptedLLM(
        [
            RouteSchema(route="rag", reason="kb"),
            BatchGradeResult(
                evaluations=[
                    ChunkEvaluation(
                        chunk_id="c1", relevant=True, confidence=0.92, reasoning="ok"
                    )
                ]
            ),
            SynthesisResult(answer="Failover retries then Groq. [1]"),
            VerifySchema(
                is_grounded=True, addresses_query=True, confidence_score=0.9
            ),
        ]
    )
    retriever = AsyncMock()
    retriever.retrieve_hybrid = AsyncMock(return_value=[_CHUNK])
    web = AsyncMock()
    graph = build_crag_graph(llm, retriever, web)

    ingest = MagicMock()
    ingest.collection_exists = AsyncMock(return_value=True)
    ingest.point_count = AsyncMock(return_value=12)
    ingest.ingest_markdown = AsyncMock(return_value=3)

    @asynccontextmanager
    async def _lifespan(app: Any) -> AsyncIterator[None]:
        app.state.graph = graph
        app.state.failover_events = []
        app.state.ingest = ingest
        app.state.qdrant = None
        app.state.checkpoint_conn = None
        app.state.chat_ip_limiter = AsyncIpRpmLimiter(rpm=1000)
        yield

    app = create_app(lifespan_override=_lifespan)
    transport = ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_benchmarks_snapshot(client: AsyncClient) -> None:
    res = await client.get("/api/v1/benchmarks")
    assert res.status_code == 200
    body = res.json()
    assert body.get("source") in {"golden_offline", "missing_snapshot"}
    assert "metrics" in body


@pytest.mark.asyncio
async def test_ingest_status(client: AsyncClient) -> None:
    res = await client.get("/api/v1/ingest/status")
    assert res.status_code == 200
    assert res.json()["points"] == 12


@pytest.mark.asyncio
async def test_chat_stream_sse(client: AsyncClient) -> None:
    res = await client.post(
        "/api/v1/chat/stream",
        json={"query": "How does failover work?", "session_id": "it-1"},
    )
    assert res.status_code == 200
    text = res.text
    assert "node_transition" in text or "verification_complete" in text or "token_chunk" in text


@pytest.mark.asyncio
async def test_pdf_reject_non_magic(client: AsyncClient) -> None:
    res = await client.post(
        "/api/v1/ingest/pdf",
        files={"file": ("bad.pdf", b"not-a-pdf", "application/pdf")},
    )
    assert res.status_code == 422
    detail = res.json().get("detail") or {}
    assert detail.get("code") == "ERR_SCANNED_OR_EMPTY_PDF"
    assert detail.get("user_message")
    assert detail.get("developer_message")
    assert detail.get("layer") == "backend"
