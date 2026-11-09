"""Ollama OpenAI-compatible structured LLM client (local dev)."""

from __future__ import annotations

import json
from typing import Any, TypeVar, cast

from openai import APIConnectionError, APITimeoutError, AsyncOpenAI
from pydantic import BaseModel, ValidationError

from agentic_crag.domain.exceptions import ProviderUnavailableError

T = TypeVar("T", bound=BaseModel)

_JSON_SYSTEM_SUFFIX = (
    "\n\nYou MUST respond with a single JSON object only. "
    "No markdown fences. No commentary. "
    "Match the required schema exactly.\n"
    "Example: {\"route\": \"rag\"}"
)


class OllamaClient:
    def __init__(
        self,
        *,
        base_url: str = "http://localhost:11434/v1",
        model: str = "qwen2.5:3b",
        api_key: str = "ollama",
        timeout_s: float = 180.0,
        client: AsyncOpenAI | None = None,
    ) -> None:
        self._model = model
        self._timeout_s = timeout_s
        # max_retries=0: SDK default (2) triples a local timeout on slow grades.
        self._client = client or AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout_s,
            max_retries=0,
        )

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[T],
        temperature: float = 0.0,
    ) -> T:
        schema = response_schema.model_json_schema()
        schema_hint = json.dumps(schema)
        system = (
            system_prompt
            + _JSON_SYSTEM_SUFFIX
            + f"\nJSON Schema:\n{schema_hint}"
        )
        # Ollama ≥0.5 enforces json_schema via grammar-constrained decoding.
        response_format: dict[str, Any] = {
            "type": "json_schema",
            "json_schema": {
                "name": response_schema.__name__,
                "schema": schema,
            },
        }
        try:
            completion = await self._client.chat.completions.create(
                model=self._model,
                temperature=temperature,
                response_format=cast(Any, response_format),
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except (
            ConnectionError,
            TimeoutError,
            OSError,
            APIConnectionError,
            APITimeoutError,
        ) as exc:
            if isinstance(exc, (APITimeoutError, TimeoutError)):
                raise ProviderUnavailableError(
                    f"Ollama timed out after {self._timeout_s:.0f}s on "
                    f"{self._model}. Raise OLLAMA_TIMEOUT_S or use a faster model.",
                    code="E02_PROVIDER_UNAVAILABLE",
                ) from exc
            raise ProviderUnavailableError(
                "Ollama unavailable. Start Ollama and pull "
                f"{self._model} (OLLAMA_BASE_URL must be reachable).",
                code="E02_PROVIDER_UNAVAILABLE",
            ) from exc

        text = completion.choices[0].message.content if completion.choices else None
        if not text:
            raise ProviderUnavailableError(
                "Ollama returned empty structured response",
                code="E02_PROVIDER_UNAVAILABLE",
            )
        try:
            return response_schema.model_validate_json(text)
        except ValidationError as exc:
            raise ProviderUnavailableError(
                f"Ollama returned invalid JSON for {response_schema.__name__}: {exc}",
                code="E02_PROVIDER_UNAVAILABLE",
            ) from exc
