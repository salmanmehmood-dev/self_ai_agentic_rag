"""Compile CRAG StateGraph for Phase 3 (nodes 1–3 + stubs)."""

from __future__ import annotations

from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from agentic_crag.domain.ports import HybridRetrieverPort, LLMClientPort
from agentic_crag.orchestration.edges import route_after_grade, route_after_sanitize
from agentic_crag.orchestration.nodes import build_nodes
from agentic_crag.orchestration.state import GraphState


def build_crag_graph(llm: LLMClientPort, retriever: HybridRetrieverPort) -> Any:
    nodes = build_nodes(llm, retriever)
    # cast: LangGraph stubs reject our NodeFn alias under strict mypy
    graph = cast(Any, StateGraph(GraphState))

    graph.add_node("sanitize_and_route", nodes["sanitize_and_route"])
    graph.add_node("hybrid_retrieve", nodes["hybrid_retrieve"])
    graph.add_node("grade_documents_batch", nodes["grade_documents_batch"])
    graph.add_node("rewrite_query", nodes["rewrite_query"])
    graph.add_node("web_search_fallback", nodes["web_search_fallback"])
    graph.add_node("synthesize_response", nodes["synthesize_response"])
    graph.add_node("direct_answer", nodes["direct_answer"])

    graph.add_edge(START, "sanitize_and_route")
    graph.add_conditional_edges(
        "sanitize_and_route",
        route_after_sanitize,
        {
            "hybrid_retrieve": "hybrid_retrieve",
            "direct_answer": "direct_answer",
            "__end__": END,
        },
    )
    graph.add_edge("hybrid_retrieve", "grade_documents_batch")
    graph.add_conditional_edges(
        "grade_documents_batch",
        route_after_grade,
        {
            "synthesize_response": "synthesize_response",
            "rewrite_query": "rewrite_query",
            "web_search_fallback": "web_search_fallback",
        },
    )
    # Loop ceiling enforced in route_after_grade via rewrite_count
    graph.add_edge("rewrite_query", "hybrid_retrieve")
    graph.add_edge("web_search_fallback", "synthesize_response")
    graph.add_edge("synthesize_response", END)
    graph.add_edge("direct_answer", END)

    return graph.compile()
