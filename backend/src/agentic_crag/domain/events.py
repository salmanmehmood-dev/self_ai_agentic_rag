from typing import Annotated, Literal

from pydantic import BaseModel, Field


class NodeTransitionData(BaseModel):
    node: Literal[
        "router", "retriever", "grader", "rewriter", "web_search", "synthesizer", "verifier"
    ]
    status: Literal["running", "completed", "skipped", "fallback"]
    latency_ms: int | None = None
    summary: str


class RetrievalChunkPayload(BaseModel):
    chunk_id: str
    source_file: str
    section_header: str
    rrf_score: float
    dense_rank: int
    sparse_rank: int
    preview_text: str


class RetrievalResultsData(BaseModel):
    query_used: str
    attempt: int
    chunks: list[RetrievalChunkPayload]


class ChunkEvaluationPayload(BaseModel):
    chunk_id: str
    relevant: bool
    confidence: float
    reasoning: str


class GradingVerdictData(BaseModel):
    passed_count: int
    rejected_count: int
    evaluations: list[ChunkEvaluationPayload]


class QueryRewrittenData(BaseModel):
    previous_query: str
    new_query: str
    reason: str
    rewrite_count: int


class TokenChunkData(BaseModel):
    delta: str


class VerificationCompleteData(BaseModel):
    is_grounded: bool
    addresses_query: bool
    confidence_score: float
    provider_used: Literal["gemini-2.5-flash", "groq-llama-3.3-70b"]
    total_latency_ms: int


class ProviderFailoverData(BaseModel):
    from_provider: str
    to_provider: str
    reason: str


class NodeTransitionEvent(BaseModel):
    event: Literal["node_transition"] = "node_transition"
    data: NodeTransitionData


class RetrievalResultsEvent(BaseModel):
    event: Literal["retrieval_results"] = "retrieval_results"
    data: RetrievalResultsData


class GradingVerdictEvent(BaseModel):
    event: Literal["grading_verdict"] = "grading_verdict"
    data: GradingVerdictData


class QueryRewrittenEvent(BaseModel):
    event: Literal["query_rewritten"] = "query_rewritten"
    data: QueryRewrittenData


class TokenChunkEvent(BaseModel):
    event: Literal["token_chunk"] = "token_chunk"
    data: TokenChunkData


class VerificationCompleteEvent(BaseModel):
    event: Literal["verification_complete"] = "verification_complete"
    data: VerificationCompleteData


class ProviderFailoverEvent(BaseModel):
    event: Literal["provider_failover"] = "provider_failover"
    data: ProviderFailoverData


AgentSSEEvent = Annotated[
    NodeTransitionEvent
    | RetrievalResultsEvent
    | GradingVerdictEvent
    | QueryRewrittenEvent
    | TokenChunkEvent
    | VerificationCompleteEvent
    | ProviderFailoverEvent,
    Field(discriminator="event"),
]
