"""Map LangGraph updates → typed SSE event strings."""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator, Callable
from typing import Any

from agentic_crag.api.sse import format_sse
from agentic_crag.domain.entities import DocumentChunk, GradedChunk, NodeExecutionEvent
from agentic_crag.domain.events import (
    ChunkEvaluationPayload,
    GradingVerdictData,
    NodeTransitionData,
    ProviderFailoverData,
    QueryRewrittenData,
    RetrievalChunkPayload,
    RetrievalResultsData,
    SystemWarningData,
    TokenChunkData,
    VerificationCompleteData,
)

_NODE_MAP = {
    "sanitize_and_route": "router",
    "hybrid_retrieve": "retriever",
    "grade_documents_batch": "grader",
    "rewrite_query": "rewriter",
    "web_search_fallback": "web_search",
    "synthesize_response": "synthesizer",
    "verify_response": "verifier",
    "direct_answer": "synthesizer",
}

DisconnectCheck = Callable[[], Any]


async def stream_chat_events(
    *,
    graph: Any,
    query: str,
    session_id: str | None,
    thread_id: str | None = None,
    provider_used: str = "gemini-2.5-flash",
    failover_events: list[ProviderFailoverData] | None = None,
    is_disconnected: DisconnectCheck | None = None,
) -> AsyncIterator[str]:
    started = time.perf_counter()
    sid = session_id or str(uuid.uuid4())
    tid = thread_id or sid
    initial = {
        "session_id": sid,
        "original_query": query,
        "rewrite_count": 0,
        "hallucination_retry_count": 0,
        "node_trace": [],
    }
    prev_query = query
    attempt = 0
    failovers = failover_events if failover_events is not None else []
    run_config = {"configurable": {"thread_id": tid}}

    try:
        async for update in graph.astream(
            initial, config=run_config, stream_mode="updates"
        ):
            if is_disconnected is not None and await is_disconnected():
                break
            if not isinstance(update, dict):
                continue
            for graph_node, partial in update.items():
                if not isinstance(partial, dict):
                    continue
                sse_node = _NODE_MAP.get(graph_node, "router")

                for ev in partial.get("node_trace") or []:
                    if isinstance(ev, NodeExecutionEvent):
                        yield format_sse(
                            "node_transition",
                            NodeTransitionData(
                                node=sse_node,  # type: ignore[arg-type]
                                status=ev.status,
                                latency_ms=ev.latency_ms,
                                summary=ev.summary,
                            ),
                        )

                while failovers:
                    fo = failovers.pop(0)
                    yield format_sse("provider_failover", fo)

                if graph_node == "hybrid_retrieve":
                    attempt += 1
                    chunks: list[DocumentChunk] = list(partial.get("retrieved_chunks") or [])
                    if attempt == 1 and len(chunks) == 0:
                        yield format_sse(
                            "system_warning",
                            SystemWarningData(
                                code="E01_EMPTY_CORPUS",
                                user_message=(
                                    "No documents matched yet. The agent may rewrite "
                                    "your query or search the web."
                                ),
                                developer_message=(
                                    "hybrid_retrieve returned 0 chunks on attempt 1; "
                                    "rewrite/web fallback may follow."
                                ),
                            ),
                        )
                    yield format_sse(
                        "retrieval_results",
                        RetrievalResultsData(
                            query_used=str(partial.get("active_query") or prev_query),
                            attempt=attempt,
                            chunks=[
                                RetrievalChunkPayload(
                                    chunk_id=c.chunk_id,
                                    source_file=c.source_file,
                                    section_header=c.section_header,
                                    rrf_score=float(c.rrf_score or 0.0),
                                    dense_rank=int(c.dense_rank or 0),
                                    sparse_rank=int(c.sparse_rank or 0),
                                    preview_text=c.text[:240],
                                )
                                for c in chunks
                            ],
                        ),
                    )

                if graph_node == "grade_documents_batch":
                    graded: list[GradedChunk] = list(partial.get("graded_chunks") or [])
                    yield format_sse(
                        "grading_verdict",
                        GradingVerdictData(
                            passed_count=len(graded),
                            rejected_count=0,
                            evaluations=[
                                ChunkEvaluationPayload(
                                    chunk_id=g.chunk_id,
                                    relevant=g.relevant,
                                    confidence=g.confidence,
                                    reasoning=g.reasoning,
                                )
                                for g in graded
                            ],
                        ),
                    )

                if graph_node == "rewrite_query":
                    new_q = str(partial.get("active_query") or prev_query)
                    yield format_sse(
                        "query_rewritten",
                        QueryRewrittenData(
                            previous_query=prev_query,
                            new_query=new_q,
                            reason="query rewrite",
                            rewrite_count=int(partial.get("rewrite_count") or 0),
                        ),
                    )
                    prev_query = new_q

                if graph_node in {"synthesize_response", "direct_answer"}:
                    draft = str(partial.get("draft_answer") or "")
                    step = 24
                    for i in range(0, len(draft), step):
                        if is_disconnected is not None and await is_disconnected():
                            return
                        yield format_sse(
                            "token_chunk",
                            TokenChunkData(delta=draft[i : i + step]),
                        )

                if graph_node == "verify_response":
                    # Skip intermediate "retry synth" so UI amber badge is final only.
                    traces = partial.get("node_trace") or []
                    if any(
                        getattr(ev, "summary", "") == "retry synth" for ev in traces
                    ):
                        continue
                    report = partial.get("verification_report")
                    if report is not None:
                        elapsed = int((time.perf_counter() - started) * 1000)
                        provider = provider_used or "gemini-2.5-flash"
                        status = getattr(report, "status", None) or (
                            "verified" if report.is_grounded else "partial_verification"
                        )
                        yield format_sse(
                            "verification_complete",
                            VerificationCompleteData(
                                is_grounded=bool(report.is_grounded),
                                addresses_query=bool(report.addresses_query),
                                confidence_score=float(report.confidence_score),
                                provider_used=provider,
                                total_latency_ms=elapsed,
                                status=status,  # type: ignore[arg-type]
                            ),
                        )
    except Exception as exc:  # noqa: BLE001 — surface to UI instead of ASGI 500
        yield format_sse(
            "system_warning",
            SystemWarningData(
                code="ERR_GRAPH_STREAM",
                user_message=(
                    "Couldn't finish that answer. Try again or rephrase your question."
                ),
                developer_message=f"{type(exc).__name__}: {exc}"[:800],
            ),
        )
