"""FastAPI entrypoint.

Callers: uvicorn agentic_crag.api.main:app; tests via create_app().
User: "Implement the plan as specified" — checkpointer, Phoenix, LLMGateway.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from qdrant_client import AsyncQdrantClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from agentic_crag.adapters.checkpoint import (
    close_sqlite_checkpointer,
    open_sqlite_checkpointer,
)
from agentic_crag.adapters.llm.rate_limit import AsyncIpRpmLimiter, AsyncRateLimiter
from agentic_crag.adapters.observability.phoenix_tracing import setup_phoenix_tracing
from agentic_crag.adapters.retrieval.ingest import MarkdownIngestService
from agentic_crag.adapters.retrieval.qdrant_hybrid import QdrantHybridStore
from agentic_crag.adapters.retrieval.sample_bootstrap import ensure_sample_corpus
from agentic_crag.adapters.runtime_factory import build_embedder, build_llm
from agentic_crag.adapters.search.web_search import WebSearchAdapter
from agentic_crag.api.error_envelope import build_error_body
from agentic_crag.api.middleware import CorrelationIdMiddleware, configure_structlog
from agentic_crag.api.routes import benchmarks as benchmarks_routes
from agentic_crag.api.routes import chat as chat_routes
from agentic_crag.api.routes import ingest as ingest_routes
from agentic_crag.config import settings
from agentic_crag.domain.events import ProviderFailoverData
from agentic_crag.domain.exceptions import EmbeddingDimensionMismatchError
from agentic_crag.orchestration.graph import build_crag_graph

configure_structlog()
_log = structlog.get_logger("agentic_crag.api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    failover_buf: list[ProviderFailoverData] = []
    app.state.failover_events = failover_buf

    async def on_failover(data: ProviderFailoverData) -> None:
        failover_buf.append(data)

    setup_phoenix_tracing(
        endpoint=settings.phoenix_collector_endpoint,
        project_name=settings.phoenix_project_name,
    )

    qdrant: AsyncQdrantClient | None = None
    graph: Any | None = None
    ingest: MarkdownIngestService | None = None
    checkpoint_conn: Any | None = None
    runtime = "local" if settings.local_dev_mode else "cloud"
    active_collection = settings.active_qdrant_collection
    active_dims = settings.active_embedding_dims

    limits = settings.tier_limits()
    chat_ip_limiter = AsyncIpRpmLimiter(limits.chat_per_ip_rpm)
    app.state.chat_ip_limiter = chat_ip_limiter
    app.state.llm_tier = settings.llm_tier

    has_fallback = bool(settings.groq_api_key or settings.routeway_api_key)
    runtime_ready = settings.local_dev_mode or (
        bool(settings.gemini_api_key) and has_fallback
    )

    if runtime_ready:
        llm = build_llm(settings, on_failover=on_failover)
        embedder = build_embedder(settings)
        tavily_lim = AsyncRateLimiter(limits.tavily, name="tavily")
        qdrant_kwargs: dict[str, Any] = {
            "url": settings.qdrant_url,
            "check_compatibility": False,
        }
        if settings.qdrant_api_key:
            qdrant_kwargs["api_key"] = settings.qdrant_api_key
        qdrant = AsyncQdrantClient(**qdrant_kwargs)
        store = QdrantHybridStore(
            qdrant,
            embedder,
            collection_name=active_collection,
            embedding_dims=active_dims,
        )
        ingest = MarkdownIngestService(store)
        try:
            await store.ensure_collection()
            await ensure_sample_corpus(ingest)
        except EmbeddingDimensionMismatchError:
            await qdrant.close()
            raise
        except Exception as exc:  # noqa: BLE001 — boot must continue
            print(f"[agentic-crag] E01 sample ingest failed (continuing): {exc}")
        web = WebSearchAdapter(
            tavily_api_key=settings.tavily_api_key,
            rate_limiter=tavily_lim,
        )
        checkpointer, checkpoint_conn = await open_sqlite_checkpointer(
            settings.checkpoint_path
        )
        graph = build_crag_graph(llm, store, web, checkpointer=checkpointer)
        model = (
            settings.ollama_model
            if settings.local_dev_mode
            else settings.gemini_model
        )
        print(
            f"[agentic-crag] runtime={runtime} collection={active_collection} "
            f"dims={active_dims} model={model}"
        )
    else:
        missing = [
            name
            for name, val in (
                ("GEMINI_API_KEY", settings.gemini_api_key),
                ("GROQ_API_KEY|ROUTEWAY_API_KEY", has_fallback or None),
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
    app.state.checkpoint_conn = checkpoint_conn
    app.state.runtime = runtime
    app.state.qdrant_collection = active_collection
    app.state.embedding_dims = active_dims
    yield
    await close_sqlite_checkpointer(checkpoint_conn)
    if qdrant is not None:
        await qdrant.close()


def create_app(*, lifespan_override: Any | None = None) -> FastAPI:
    """App factory. Tests pass lifespan_override to inject mocked graph/ingest."""
    app = FastAPI(
        title=settings.app_name,
        lifespan=lifespan_override or lifespan,
    )
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(chat_routes.router)
    app.include_router(ingest_routes.router)
    app.include_router(benchmarks_routes.router)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict) and "user_message" in detail and "code" in detail:
            body = detail
        else:
            body = build_error_body(
                code="ERR_HTTP",
                developer_message=str(detail),
                user_message="Request failed. Please try again.",
                expose_developer=settings.expose_developer_errors,
            ).model_dump()
        _log.error(
            "http_error",
            status_code=exc.status_code,
            code=body.get("code"),
            developer_message=body.get("developer_message"),
            path=str(request.url.path),
        )
        return JSONResponse(status_code=exc.status_code, content={"detail": body})

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        body = build_error_body(
            code="ERR_VALIDATION",
            developer_message=str(exc.errors()),
            expose_developer=settings.expose_developer_errors,
        ).model_dump()
        _log.warning(
            "validation_error",
            developer_message=body["developer_message"],
            path=str(request.url.path),
        )
        return JSONResponse(status_code=422, content={"detail": body})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        body = build_error_body(
            code="ERR_INTERNAL",
            developer_message=f"{type(exc).__name__}: {exc}",
            expose_developer=settings.expose_developer_errors,
        ).model_dump()
        _log.exception(
            "unhandled_error",
            developer_message=body["developer_message"],
            path=str(request.url.path),
        )
        return JSONResponse(status_code=500, content={"detail": body})

    @app.get("/health")
    async def health(request: Request) -> dict[str, object]:
        """Liveness: process is up. Includes runtime readiness fields for operators."""
        graph_ready = getattr(request.app.state, "graph", None) is not None
        return {
            "status": "ok",
            "runtime": getattr(request.app.state, "runtime", "unknown"),
            "graph_ready": graph_ready,
            "qdrant_collection": getattr(
                request.app.state, "qdrant_collection", None
            ),
            "embedding_dims": getattr(request.app.state, "embedding_dims", None),
        }

    @app.get("/ready")
    async def ready(request: Request) -> JSONResponse:
        """Readiness: graph is wired. Railway should use this for traffic."""
        graph_ready = getattr(request.app.state, "graph", None) is not None
        body = {
            "status": "ready" if graph_ready else "not_ready",
            "runtime": getattr(request.app.state, "runtime", "unknown"),
            "graph_ready": graph_ready,
            "qdrant_collection": getattr(
                request.app.state, "qdrant_collection", None
            ),
            "embedding_dims": getattr(request.app.state, "embedding_dims", None),
        }
        return JSONResponse(
            status_code=200 if graph_ready else 503,
            content=body,
        )

    return app


app = create_app()
