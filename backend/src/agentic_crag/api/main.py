from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from qdrant_client import AsyncQdrantClient

from agentic_crag.adapters.llm.gateway import FailoverLLMGateway
from agentic_crag.adapters.llm.gemini_client import GeminiClient
from agentic_crag.adapters.llm.groq_client import GroqClient
from agentic_crag.adapters.retrieval.embedder import GeminiEmbedder, HashEmbedder
from agentic_crag.adapters.retrieval.qdrant_hybrid import QdrantHybridStore
from agentic_crag.adapters.search.web_search import WebSearchAdapter
from agentic_crag.api.routes import chat as chat_routes
from agentic_crag.config import settings
from agentic_crag.domain.events import ProviderFailoverData
from agentic_crag.orchestration.graph import build_crag_graph


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    failover_buf: list[ProviderFailoverData] = []
    app.state.failover_events = failover_buf

    async def on_failover(data: ProviderFailoverData) -> None:
        failover_buf.append(data)

    qdrant: AsyncQdrantClient | None = None
    graph: Any | None = None

    if settings.gemini_api_key and settings.groq_api_key:
        primary = GeminiClient(settings.gemini_api_key)
        fallback = GroqClient(settings.groq_api_key)
        llm = FailoverLLMGateway(primary, fallback, on_failover=on_failover)
        embedder: Any
        if settings.gemini_api_key:
            embedder = GeminiEmbedder(settings.gemini_api_key)
        else:
            embedder = HashEmbedder(dims=settings.embedding_dims)
        qdrant = AsyncQdrantClient(url=settings.qdrant_url)
        store = QdrantHybridStore(
            qdrant,
            embedder,
            collection_name=settings.qdrant_collection,
            embedding_dims=settings.embedding_dims,
        )
        web = WebSearchAdapter()
        graph = build_crag_graph(llm, store, web)

    app.state.graph = graph
    app.state.qdrant = qdrant
    yield
    if qdrant is not None:
        await qdrant.close()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(chat_routes.router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
