"""HTTP request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(min_length=2, max_length=2000)
    session_id: str | None = None
