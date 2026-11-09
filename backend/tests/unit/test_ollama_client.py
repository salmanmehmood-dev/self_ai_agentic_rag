from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from openai import APIConnectionError, APITimeoutError
from pydantic import BaseModel

from agentic_crag.adapters.llm.ollama_client import OllamaClient
from agentic_crag.domain.exceptions import ProviderUnavailableError


class _RouteOut(BaseModel):
    route: str


@pytest.mark.asyncio
async def test_ollama_uses_json_schema_response_format() -> None:
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
    assert kwargs["model"] == "qwen2.5:3b"
    rf = kwargs["response_format"]
    assert rf["type"] == "json_schema"
    assert rf["json_schema"]["name"] == "_RouteOut"
    assert "properties" in rf["json_schema"]["schema"]


@pytest.mark.asyncio
async def test_ollama_connection_error_maps_unavailable() -> None:
    client = OllamaClient(base_url="http://localhost:11434/v1", model="qwen2.5:3b")
    client._client = MagicMock()
    client._client.chat.completions.create = AsyncMock(
        side_effect=ConnectionError("refused")
    )
    with pytest.raises(ProviderUnavailableError):
        await client.generate_structured("sys", "user", _RouteOut)


@pytest.mark.asyncio
async def test_ollama_api_connection_error_maps_unavailable() -> None:
    client = OllamaClient(base_url="http://localhost:11434/v1", model="qwen2.5:3b")
    client._client = MagicMock()
    client._client.chat.completions.create = AsyncMock(
        side_effect=APIConnectionError(request=httpx.Request("GET", "http://x"))
    )
    with pytest.raises(ProviderUnavailableError):
        await client.generate_structured("sys", "user", _RouteOut)


@pytest.mark.asyncio
async def test_ollama_api_timeout_error_maps_unavailable() -> None:
    client = OllamaClient(
        base_url="http://localhost:11434/v1",
        model="qwen2.5:3b",
        timeout_s=180.0,
    )
    client._client = MagicMock()
    client._client.chat.completions.create = AsyncMock(
        side_effect=APITimeoutError(request=httpx.Request("GET", "http://x"))
    )
    with pytest.raises(ProviderUnavailableError, match="timed out after 180s"):
        await client.generate_structured("sys", "user", _RouteOut)


def test_ollama_client_disables_sdk_retries() -> None:
    client = OllamaClient(base_url="http://localhost:11434/v1", model="qwen2.5:3b")
    assert client._client.max_retries == 0
    assert client._timeout_s == 180.0
