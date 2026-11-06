"""Groq structured-output adapter (failover LLM)."""

from __future__ import annotations

from typing import TypeVar

from groq import AsyncGroq
from pydantic import BaseModel

from agentic_crag.adapters.llm.errors import raise_mapped_provider_error

T = TypeVar("T", bound=BaseModel)

_GROQ_MODEL = "llama-3.3-70b-versatile"


class GroqClient:
    def __init__(
        self,
        api_key: str,
        *,
        model: str = _GROQ_MODEL,
        client: AsyncGroq | None = None,
    ) -> None:
        self._model = model
        self._client = client or AsyncGroq(api_key=api_key)

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
            raise_mapped_provider_error(exc, provider="groq")

        content = completion.choices[0].message.content
        if not content:
            msg = "Groq returned empty structured response"
            raise RuntimeError(msg)
        return response_schema.model_validate_json(content)
