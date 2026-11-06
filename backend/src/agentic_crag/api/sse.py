"""SSE wire encoding for AgentSSEEvent payloads."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel


def format_sse(event_name: str, data: BaseModel | dict[str, Any]) -> str:
    payload = data.model_dump() if isinstance(data, BaseModel) else data
    body = json.dumps({"event": event_name, "data": payload}, ensure_ascii=False)
    return f"event: {event_name}\ndata: {body}\n\n"
