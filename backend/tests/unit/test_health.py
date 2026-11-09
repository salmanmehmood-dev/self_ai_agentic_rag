from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient

from agentic_crag.api.main import create_app


@asynccontextmanager
async def _lifespan_graph_ready(app: FastAPI) -> AsyncIterator[None]:
    app.state.graph = object()
    app.state.runtime = "local"
    app.state.qdrant_collection = "crag_chunks_local"
    app.state.embedding_dims = 384
    app.state.qdrant = None
    app.state.ingest = None
    app.state.checkpoint_conn = None
    yield


@asynccontextmanager
async def _lifespan_graph_missing(app: FastAPI) -> AsyncIterator[None]:
    app.state.graph = None
    app.state.runtime = "cloud"
    app.state.qdrant_collection = "crag_chunks"
    app.state.embedding_dims = 768
    app.state.qdrant = None
    app.state.ingest = None
    app.state.checkpoint_conn = None
    yield


def test_health_returns_runtime_fields() -> None:
    with TestClient(create_app(lifespan_override=_lifespan_graph_ready)) as client:
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["runtime"] == "local"
        assert body["graph_ready"] is True
        assert body["qdrant_collection"] == "crag_chunks_local"
        assert body["embedding_dims"] == 384


def test_ready_ok_when_graph_present() -> None:
    with TestClient(create_app(lifespan_override=_lifespan_graph_ready)) as client:
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json()["graph_ready"] is True


def test_ready_503_when_graph_missing() -> None:
    with TestClient(create_app(lifespan_override=_lifespan_graph_missing)) as client:
        response = client.get("/ready")
        assert response.status_code == 503
        body = response.json()
        assert body["graph_ready"] is False
        assert body["runtime"] == "cloud"
