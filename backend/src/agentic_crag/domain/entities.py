from typing import Literal

from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    chunk_id: str
    source_file: str
    section_header: str = ""
    text: str
    source_type: Literal["corpus", "web"] = "corpus"
    rrf_score: float | None = None
    dense_rank: int | None = None
    sparse_rank: int | None = None


class GradedChunk(DocumentChunk):
    relevant: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""


class CitationItem(BaseModel):
    index: int
    chunk_id: str
    source_file: str
    preview_text: str
    confidence: float | None = None


class VerificationResult(BaseModel):
    is_grounded: bool
    addresses_query: bool
    confidence_score: float = Field(ge=0.0, le=1.0)
    status: Literal["verified", "partial_verification"] = "verified"


class NodeExecutionEvent(BaseModel):
    node: str
    status: Literal["running", "completed", "skipped", "fallback"]
    latency_ms: int | None = None
    summary: str = ""
