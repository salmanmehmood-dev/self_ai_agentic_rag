"""SSE chat stream endpoint with mocked graph ports."""

from __future__ import annotations

from typing import TypeVar
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

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

T = TypeVar("T", bound=BaseModel)

_CHUNK = DocumentChunk(
    chunk_id="c1",
    source_file="sla.md",
    section_header="Failover",
    text="[Source: sla.md | Section: Failover]\nRetries on 429 then Groq failover.",
    rrf_score=0.8,
    dense_rank=1,
    sparse_rank=1,
)


class _ScriptedLLM:
    def __init__(self, responses: list[BaseModel]) -> None:
        self._responses = list(responses)

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[T],
        temperature: float = 0.0,
    ) -> T:
        item = self._responses.pop(0)
        assert isinstance(item, response_schema)
        return item  # type: ignore[return-value]


@pytest.fixture
def client() -> TestClient:
    llm = _ScriptedLLM(
        [
            RouteSchema(route="rag", reason="kb"),
            BatchGradeResult(
                evaluations=[
                    ChunkEvaluation(
                        chunk_id="c1", relevant=True, confidence=0.9, reasoning="ok"
                    )
                ]
            ),
            SynthesisResult(answer="Failover uses Groq after Gemini quota. [1]"),
            VerifySchema(
                is_grounded=True,
                addresses_query=True,
                confidence_score=0.95,
            ),
        ]
    )
    retriever = AsyncMock()
    retriever.retrieve_hybrid = AsyncMock(return_value=[_CHUNK])
    web = AsyncMock()
    graph = build_crag_graph(llm, retriever, web)

    app = create_app()
    with TestClient(app) as test_client:
        # Lifespan may clear graph when keys missing — attach mocked graph after.
        app.state.graph = graph
        app.state.failover_events = []
        yield test_client


def test_chat_stream_emits_node_transition_and_tokens(client: TestClient) -> None:
    with client.stream(
        "POST",
        "/api/v1/chat/stream",
        json={"query": "How does failover work?"},
    ) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        body = "".join(response.iter_text())

    assert "event: node_transition" in body
    assert "event: retrieval_results" in body
    assert "event: grading_verdict" in body
    assert "event: token_chunk" in body
    assert "event: verification_complete" in body


def test_chat_rejects_oversized_query(client: TestClient) -> None:
    response = client.post(
        "/api/v1/chat/stream",
        json={"query": "x" * 2001},
    )
    assert response.status_code == 422


def test_health_still_ok(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert "graph_ready" in body
    assert "runtime" in body
