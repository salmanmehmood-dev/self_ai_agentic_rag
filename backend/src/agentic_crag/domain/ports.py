from typing import Protocol, TypeVar

from pydantic import BaseModel

from agentic_crag.domain.entities import DocumentChunk

T = TypeVar("T", bound=BaseModel)


class LLMClientPort(Protocol):
    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[T],
        temperature: float = 0.0,
    ) -> T: ...


class HybridRetrieverPort(Protocol):
    async def retrieve_hybrid(self, query: str, top_k: int = 5) -> list[DocumentChunk]: ...


class WebSearchPort(Protocol):
    async def search(self, query: str, max_results: int = 5) -> list[DocumentChunk]: ...


class EmbedderPort(Protocol):
    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...


class DocumentIngestPort(Protocol):
    async def ingest_markdown(self, source_file: str, markdown: str) -> int: ...

    async def point_count(self) -> int: ...

    async def collection_exists(self) -> bool: ...
