from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from qdrant_client import AsyncQdrantClient

from agentic_crag.adapters.llm.gateway import FailoverLLMGateway
from agentic_crag.adapters.llm.gemini_client import GeminiClient
from agentic_crag.adapters.llm.groq_client import GroqClient
from agentic_crag.adapters.retrieval.embedder import GeminiEmbedder
from agentic_crag.adapters.retrieval.ingest import MarkdownIngestService
from agentic_crag.adapters.retrieval.qdrant_hybrid import QdrantHybridStore
from agentic_crag.adapters.retrieval.sample_bootstrap import ensure_sample_corpus
from agentic_crag.adapters.search.web_search import WebSearchAdapter
from agentic_crag.api.routes import chat as chat_routes
from agentic_crag.api.routes import ingest as ingest_routes
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
    ingest: MarkdownIngestService | None = None

    if settings.gemini_api_key and settings.groq_api_key:
        primary = GeminiClient(settings.gemini_api_key)
        fallback = GroqClient(settings.groq_api_key)
        llm = FailoverLLMGateway(primary, fallback, on_failover=on_failover)
        embedder: Any = GeminiEmbedder(
            settings.gemini_api_key,
            dims=settings.embedding_dims,
        )
        qdrant = AsyncQdrantClient(
            url=settings.qdrant_url,
            check_compatibility=False,
        )
        store = QdrantHybridStore(
            qdrant,
            embedder,
            collection_name=settings.qdrant_collection,
            embedding_dims=settings.embedding_dims,
        )
        ingest = MarkdownIngestService(store)
        # E01: empty collection → load sample docs so hybrid retrieve is usable.
        # Soft-fail: embedding outages must not block chat (degrades to web path).
        try:
            await ensure_sample_corpus(ingest)
        except Exception as exc:  # noqa: BLE001 — boot must continue
            print(f"[agentic-crag] E01 sample ingest failed (continuing): {exc}")
        web = WebSearchAdapter()
        graph = build_crag_graph(llm, store, web)
    else:
        missing = [
            name
            for name, val in (
                ("GEMINI_API_KEY", settings.gemini_api_key),
                ("GROQ_API_KEY", settings.groq_api_key),
            )
            if not val
        ]
        print(
            f"[agentic-crag] Chat graph disabled; missing {', '.join(missing)}. "
            "POST /api/v1/chat/stream will return 503 until keys load and process restarts."
        )

    app.state.graph = graph
    app.state.qdrant = qdrant
    app.state.ingest = ingest
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
    app.include_router(ingest_routes.router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
