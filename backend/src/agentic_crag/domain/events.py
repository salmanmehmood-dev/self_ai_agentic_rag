from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator


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
    provider_used: str
    total_latency_ms: int
    status: Literal["verified", "partial_verification"] = "verified"


class ProviderFailoverData(BaseModel):
    from_provider: str
    to_provider: str
    reason: str


class SystemWarningData(BaseModel):
    code: str
    user_message: str
    developer_message: str
    # Alias of user_message for older clients / FE fallbacks
    message: str = ""
    layer: Literal["backend"] = "backend"

    @model_validator(mode="after")
    def _sync_message(self) -> SystemWarningData:
        if not self.message:
            self.message = self.user_message
        return self


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


class SystemWarningEvent(BaseModel):
    event: Literal["system_warning"] = "system_warning"
    data: SystemWarningData


AgentSSEEvent = Annotated[
    NodeTransitionEvent
    | RetrievalResultsEvent
    | GradingVerdictEvent
    | QueryRewrittenEvent
    | TokenChunkEvent
    | VerificationCompleteEvent
    | ProviderFailoverEvent
    | SystemWarningEvent,
    Field(discriminator="event"),
]
