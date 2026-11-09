"""Routeway OpenAI-compatible structured-output adapter (tertiary LLM).

Caller: api.main lifespan when ROUTEWAY_API_KEY set.
Docs: https://docs.routeway.ai/guides/chat-completions/structured-outputs
Base URL: https://api.routeway.ai/v1
"""

from __future__ import annotations

from typing import TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel

from agentic_crag.adapters.llm.errors import raise_mapped_provider_error

T = TypeVar("T", bound=BaseModel)

_DEFAULT_BASE_URL = "https://api.routeway.ai/v1"
# Portfolio default: free-tier model (5 RPM / 200 RPD). Override via ROUTEWAY_MODEL.
_DEFAULT_MODEL = "deepseek-v4.1-flash:free"


class RoutewayClient:
    """LLMClientPort via Routeway's OpenAI-compatible chat completions API."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = _DEFAULT_MODEL,
        base_url: str = _DEFAULT_BASE_URL,
        client: AsyncOpenAI | None = None,
        timeout_s: float = 45.0,
    ) -> None:
        self._model = model
        self._client = client or AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_s,
        )

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[T],
        temperature: float = 0.0,
    ) -> T:
        schema = response_schema.model_json_schema()
        try:
            completion = await self._client.chat.completions.create(
                model=self._model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": response_schema.__name__,
                        "schema": schema,
                    },
                },
            )
        except Exception as exc:  # noqa: BLE001 — map then re-raise
            raise_mapped_provider_error(exc, provider="routeway")

        content = completion.choices[0].message.content
        if not content:
            msg = "Routeway returned empty structured response"
            raise RuntimeError(msg)
        return response_schema.model_validate_json(content)
