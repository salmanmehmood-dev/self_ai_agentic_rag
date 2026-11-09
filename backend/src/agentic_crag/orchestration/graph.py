"""Compile CRAG StateGraph (nodes 1–7 with loop ceilings)."""

from __future__ import annotations

from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from agentic_crag.domain.ports import HybridRetrieverPort, LLMClientPort, WebSearchPort
from agentic_crag.orchestration.edges import (
    route_after_grade,
    route_after_sanitize,
    route_after_verify,
)
from agentic_crag.orchestration.nodes import build_nodes
from agentic_crag.orchestration.state import GraphState


def build_crag_graph(
    llm: LLMClientPort,
    retriever: HybridRetrieverPort,
    web_search: WebSearchPort,
    *,
    checkpointer: Any | None = None,
) -> Any:
    nodes = build_nodes(llm, retriever, web_search)
    # cast: LangGraph stubs reject our NodeFn alias under strict mypy
    graph = cast(Any, StateGraph(GraphState))

    graph.add_node("sanitize_and_route", nodes["sanitize_and_route"])
    graph.add_node("hybrid_retrieve", nodes["hybrid_retrieve"])
    graph.add_node("grade_documents_batch", nodes["grade_documents_batch"])
    graph.add_node("rewrite_query", nodes["rewrite_query"])
    graph.add_node("web_search_fallback", nodes["web_search_fallback"])
    graph.add_node("synthesize_response", nodes["synthesize_response"])
    graph.add_node("verify_response", nodes["verify_response"])
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
    graph.add_edge("rewrite_query", "hybrid_retrieve")
    graph.add_edge("web_search_fallback", "synthesize_response")
    graph.add_edge("synthesize_response", "verify_response")
    graph.add_conditional_edges(
        "verify_response",
        route_after_verify,
        {
            "synthesize_response": "synthesize_response",
            "__end__": END,
        },
    )
    graph.add_edge("direct_answer", END)

    if checkpointer is not None:
        return graph.compile(checkpointer=checkpointer)
    return graph.compile()
