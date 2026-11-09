"""Structured API / SSE errors: user-safe copy + developer detail.

Callers: api/dependencies.py, api/routes/ingest.py, api/streaming.py, api/main.py
handlers. No prior envelope module. Schema: ApiErrorBody JSON. User instruction:
"backend should also give meaning full errors msg to frontend and errors for
developers".
"""

from __future__ import annotations

from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field, model_validator

Layer = Literal["backend"]


class ApiErrorBody(BaseModel):
    """JSON body for HTTP errors and SSE system_warning payloads."""

    code: str
    user_message: str
    developer_message: str
    layer: Layer = "backend"
    message: str = Field(
        default="",
        description="Alias of user_message for older clients",
    )

    @model_validator(mode="after")
    def _sync_message(self) -> ApiErrorBody:
        if not self.message:
            self.message = self.user_message
        return self


_USER_COPY: dict[str, str] = {
    "ERR_GRAPH_NOT_READY": (
        "The assistant isn't ready yet. Try again in a moment."
    ),
    "ERR_GRAPH_STREAM": (
        "Couldn't finish that answer. Try again or rephrase your question."
    ),
    "E01_EMPTY_CORPUS": (
        "No documents matched yet. The agent may rewrite your query or search the web."
    ),
    "ERR_SCANNED_OR_EMPTY_PDF": (
        "That PDF couldn't be read. Upload a text-based PDF (not a scan)."
    ),
    "ERR_INGEST_UNAVAILABLE": (
        "Document ingest isn't available right now. Check that the API started with keys."
    ),
    "ERR_VALIDATION": (
        "That request wasn't accepted. Check your input and try again."
    ),
    "ERR_INTERNAL": ("Something went wrong on the server. Please try again."),
    "ERR_CHAT_RATE_LIMIT": (
        "Too many chat requests from your network. Wait a minute and try again."
    ),
    "E02_PROVIDER_QUOTA": (
        "The AI provider is rate-limited. Wait a few seconds and try again."
    ),
}


def user_message_for(code: str, fallback: str | None = None) -> str:
    return _USER_COPY.get(code) or fallback or "Something went wrong. Please try again."


def build_error_body(
    *,
    code: str,
    developer_message: str,
    user_message: str | None = None,
    expose_developer: bool = True,
    correlation_id: str | None = None,
) -> ApiErrorBody:
    user = user_message or user_message_for(code)
    if expose_developer:
        dev = developer_message
        if correlation_id:
            dev = f"{developer_message} (correlation_id={correlation_id})"
    else:
        dev = f"Developer detail suppressed. correlation_id={correlation_id or 'n/a'}"
    return ApiErrorBody(
        code=code,
        user_message=user,
        developer_message=dev,
        message=user,
        layer="backend",
    )


def http_error(
    *,
    status_code: int,
    code: str,
    developer_message: str,
    user_message: str | None = None,
    expose_developer: bool = True,
    correlation_id: str | None = None,
) -> HTTPException:
    body = build_error_body(
        code=code,
        developer_message=developer_message,
        user_message=user_message,
        expose_developer=expose_developer,
        correlation_id=correlation_id,
    )
    return HTTPException(status_code=status_code, detail=body.model_dump())
