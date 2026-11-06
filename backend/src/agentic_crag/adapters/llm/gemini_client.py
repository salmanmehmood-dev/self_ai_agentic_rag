"""Gemini structured-output adapter (primary LLM)."""

from __future__ import annotations

from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from agentic_crag.adapters.llm.errors import raise_mapped_provider_error

T = TypeVar("T", bound=BaseModel)


class GeminiClient:
    def __init__(
        self,
        api_key: str,
        *,
        model: str = "gemini-2.5-flash",
        client: genai.Client | None = None,
    ) -> None:
        self._model = model
        self._client = client or genai.Client(api_key=api_key)

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[T],
        temperature: float = 0.0,
    ) -> T:
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                ),
            )
        except Exception as exc:  # noqa: BLE001 — map then re-raise
            raise_mapped_provider_error(exc, provider="gemini")

        text = response.text
        if not text:
            msg = "Gemini returned empty structured response"
            raise RuntimeError(msg)
        return response_schema.model_validate_json(text)
