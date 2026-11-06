"""Conditional edge routers with explicit loop ceilings."""

from __future__ import annotations

from typing import Literal

from agentic_crag.orchestration.constants import MAX_QUERY_REWRITES
from agentic_crag.orchestration.state import GraphState

RouteAfterRouter = Literal["hybrid_retrieve", "direct_answer", "__end__"]
RouteAfterGrade = Literal["synthesize_response", "rewrite_query", "web_search_fallback"]


def route_after_sanitize(state: GraphState) -> RouteAfterRouter:
    decision = state.get("route_decision")
    if decision == "rag":
        return "hybrid_retrieve"
    if decision == "direct":
        return "direct_answer"
    return "__end__"


def route_after_grade(state: GraphState) -> RouteAfterGrade:
    graded = state.get("graded_chunks") or []
    if len(graded) >= 1:
        return "synthesize_response"
    rewrite_count = int(state.get("rewrite_count") or 0)
    if rewrite_count < MAX_QUERY_REWRITES:
        return "rewrite_query"
    return "web_search_fallback"
