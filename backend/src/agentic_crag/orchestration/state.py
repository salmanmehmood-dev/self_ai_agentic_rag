"""LangGraph state — immutable updates via reducers (E10)."""

from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

from agentic_crag.domain.entities import (
    CitationItem,
    DocumentChunk,
    GradedChunk,
    NodeExecutionEvent,
    VerificationResult,
)


class GraphState(TypedDict, total=False):
    session_id: str
    original_query: str
    sanitized_query: str
    active_query: str
    route_decision: Literal["direct", "rag", "blocked"]
    retrieved_chunks: list[DocumentChunk]
    graded_chunks: list[GradedChunk]
    rewrite_count: int
    hallucination_retry_count: int
    web_fallback_triggered: bool
    degraded_mode: bool
    draft_answer: str
    verification_report: VerificationResult
    citations: list[CitationItem]
    node_trace: Annotated[list[NodeExecutionEvent], operator.add]
