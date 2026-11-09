from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel

from agentic_crag.adapters.llm.ollama_client import OllamaClient
from agentic_crag.domain.exceptions import ProviderUnavailableError


class _RouteOut(BaseModel):
    route: str


@pytest.mark.asyncio
async def test_ollama_parses_json_object() -> None:
    client = OllamaClient(base_url="http://localhost:11434/v1", model="qwen2.5:3b")
    mock_create = AsyncMock(
        return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"route":"rag"}'))]
        )
    )
    client._client = MagicMock()
    client._client.chat.completions.create = mock_create

    out = await client.generate_structured("sys", "user q", _RouteOut)
    assert out.route == "rag"
    kwargs = mock_create.await_args.kwargs
    assert kwargs["response_format"] == {"type": "json_object"}
    assert kwargs["model"] == "qwen2.5:3b"


@pytest.mark.asyncio
async def test_ollama_connection_error_maps_unavailable() -> None:
    client = OllamaClient(base_url="http://localhost:11434/v1", model="qwen2.5:3b")
    client._client = MagicMock()
    client._client.chat.completions.create = AsyncMock(
        side_effect=ConnectionError("refused")
    )
    with pytest.raises(ProviderUnavailableError):
        await client.generate_structured("sys", "user", _RouteOut)
