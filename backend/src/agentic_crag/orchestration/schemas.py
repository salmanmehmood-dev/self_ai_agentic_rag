"""Structured LLM schemas for graph nodes (not domain entities)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RouteSchema(BaseModel):
    route: Literal["direct", "rag", "blocked"]
    reason: str = ""


class ChunkEvaluation(BaseModel):
    chunk_id: str
    relevant: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""


class BatchGradeResult(BaseModel):
    evaluations: list[ChunkEvaluation]


class RewriteResult(BaseModel):
    new_query: str
    reason: str = ""


class SynthesisResult(BaseModel):
    answer: str


class VerifySchema(BaseModel):
    is_grounded: bool
    addresses_query: bool
    confidence_score: float = Field(ge=0.0, le=1.0)
    critique: str = ""
