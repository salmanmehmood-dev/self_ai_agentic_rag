# Phase 0 Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the monorepo basis (hexagonal backend stubs, FastAPI `/health`, Next.js stub, Qdrant compose, agent/env docs) with no LLM or graph logic.

**Architecture:** Ports-and-adapters skeleton under `backend/src/agentic_crag/`. Domain holds Pydantic entities, SSE event models, and Protocol ports only. FastAPI delivery layer exposes health. Frontend is a static App Router stub. Docker Compose runs Qdrant only.

**Tech Stack:** Python 3.12+, uv, FastAPI, pydantic v2, pydantic-settings, pytest, ruff, mypy, Next.js 15, TypeScript, Tailwind, Docker Compose, Qdrant.

**Design:** `docs/superpowers/specs/2026-11-06-phase0-scaffold-design.md`  
**Roadmap:** `docs/superpowers/plans/2026-11-06-agentic-crag-phase-roadmap.md`

## Global Constraints

- Domain package must contain **zero** imports from `langchain`, `langgraph`, `fastapi`, `qdrant_client`, or `google.genai`.
- No hardcoded API keys; use `.env.example` placeholders only.
- Phase 0 must not call LLMs, open Qdrant clients from the app, or implement SSE chat.
- `MAX_QUERY_REWRITES = 2` and `MAX_HALLUCINATION_RETRIES = 1` are documented in `AGENTS.md` only (not wired yet).
- Happy-path LLM call budget and batch grading rules live in `AGENTS.md` for later phases.
- Prefer `uv` for Python deps; `ruff check` and `mypy --strict` must pass on `agentic_crag`.

## File map

| Path | Responsibility |
| --- | --- |
| `AGENTS.md` | Copy of root guardrails for coding agents |
| `README.md` | Project overview + run instructions |
| `.env.example` | Key placeholders |
| `.gitignore` | Python/Node/env/Docker ignores |
| `docker-compose.yml` | Qdrant service |
| `backend/pyproject.toml` | Package metadata, deps, ruff/mypy/pytest |
| `backend/src/agentic_crag/config.py` | Settings |
| `backend/src/agentic_crag/domain/*.py` | Entities, events, exceptions, ports |
| `backend/src/agentic_crag/api/main.py` | FastAPI app + `/health` |
| `backend/tests/unit/test_health.py` | Health test |
| `frontend/` | Next.js 15 stub |

---

### Task 1: Root docs, ignore, and env example

**Files:**
- Create: `AGENTS.md`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `README.md` (minimal; expand after Task 5)

**Interfaces:**
- Consumes: root `ai_coding_agent_directives_guardrails.md`
- Produces: agent rules at repo root; env var names for later Settings

- [ ] **Step 1: Copy guardrails into `AGENTS.md`**

Copy the full contents of `ai_coding_agent_directives_guardrails.md` into `AGENTS.md`. Keep the purpose block. Title may be `# AGENTS.md` or keep the original H1.

- [ ] **Step 2: Write `.gitignore`**

```gitignore
.env
.venv/
__pycache__/
*.py[cod]
.mypy_cache/
.ruff_cache/
.pytest_cache/
.coverage
htmlcov/
node_modules/
.next/
out/
dist/
*.egg-info/
.DS_Store
```

- [ ] **Step 3: Write `.env.example`**

```bash
GEMINI_API_KEY=
GROQ_API_KEY=
TAVILY_API_KEY=
QDRANT_URL=http://localhost:6333
```

- [ ] **Step 4: Write stub `README.md`**

```markdown
# Agentic CRAG Copilot

Corrective + Self-Reflective Agentic RAG (LangGraph) with a Next.js agent workbench.

## Status

Phase 0 scaffold. See `docs/superpowers/plans/2026-11-06-agentic-crag-phase-roadmap.md`.

## Quick start

Documented after backend/frontend/compose land (Phase 0 Tasks 2–5).
```

- [ ] **Step 5: Verify files exist**

Run: `ls AGENTS.md .gitignore .env.example README.md`  
Expected: all four listed.

---

### Task 2: Backend package + domain stubs

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/src/agentic_crag/__init__.py`
- Create: `backend/src/agentic_crag/config.py`
- Create: `backend/src/agentic_crag/domain/__init__.py`
- Create: `backend/src/agentic_crag/domain/entities.py`
- Create: `backend/src/agentic_crag/domain/events.py`
- Create: `backend/src/agentic_crag/domain/exceptions.py`
- Create: `backend/src/agentic_crag/domain/ports.py`
- Create: empty `__init__.py` under `adapters/`, `adapters/llm/`, `adapters/retrieval/`, `adapters/search/`, `orchestration/`, `api/routes/`

**Interfaces:**
- Consumes: HLD state/entity field names; UI SSE event names
- Produces: importable `agentic_crag.domain.*` and `agentic_crag.config.Settings`

- [ ] **Step 1: Write `backend/pyproject.toml`**

```toml
[project]
name = "agentic-crag"
version = "0.1.0"
description = "Corrective & Self-Reflective Agentic RAG"
readme = "../README.md"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115.0",
  "uvicorn[standard]>=0.32.0",
  "pydantic>=2.9.0",
  "pydantic-settings>=2.6.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3.0",
  "pytest-asyncio>=0.24.0",
  "httpx>=0.27.0",
  "ruff>=0.8.0",
  "mypy>=1.13.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/agentic_crag"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.mypy]
python_version = "3.12"
strict = true
packages = ["agentic_crag"]
mypy_path = "src"
```

- [ ] **Step 2: Write `config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "agentic-crag"
    cors_origins: list[str] = ["http://localhost:3000"]
    qdrant_url: str = "http://localhost:6333"
    gemini_api_key: str | None = None
    groq_api_key: str | None = None
    tavily_api_key: str | None = None


settings = Settings()
```

- [ ] **Step 3: Write `domain/entities.py`**

```python
from typing import Literal

from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    chunk_id: str
    source_file: str
    section_header: str = ""
    text: str
    source_type: Literal["corpus", "web"] = "corpus"
    rrf_score: float | None = None
    dense_rank: int | None = None
    sparse_rank: int | None = None


class GradedChunk(DocumentChunk):
    relevant: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""


class CitationItem(BaseModel):
    index: int
    chunk_id: str
    source_file: str
    preview_text: str
    confidence: float | None = None


class VerificationResult(BaseModel):
    is_grounded: bool
    addresses_query: bool
    confidence_score: float = Field(ge=0.0, le=1.0)
    status: Literal["verified", "partial_verification"] = "verified"


class NodeExecutionEvent(BaseModel):
    node: str
    status: Literal["running", "completed", "skipped", "fallback"]
    latency_ms: int | None = None
    summary: str = ""
```

- [ ] **Step 4: Write `domain/events.py`**

```python
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class NodeTransitionData(BaseModel):
    node: Literal[
        "router", "retriever", "grader", "rewriter", "web_search", "synthesizer", "verifier"
    ]
    status: Literal["running", "completed", "skipped", "fallback"]
    latency_ms: int | None = None
    summary: str


class RetrievalChunkPayload(BaseModel):
    chunk_id: str
    source_file: str
    section_header: str
    rrf_score: float
    dense_rank: int
    sparse_rank: int
    preview_text: str


class RetrievalResultsData(BaseModel):
    query_used: str
    attempt: int
    chunks: list[RetrievalChunkPayload]


class ChunkEvaluationPayload(BaseModel):
    chunk_id: str
    relevant: bool
    confidence: float
    reasoning: str


class GradingVerdictData(BaseModel):
    passed_count: int
    rejected_count: int
    evaluations: list[ChunkEvaluationPayload]


class QueryRewrittenData(BaseModel):
    previous_query: str
    new_query: str
    reason: str
    rewrite_count: int


class TokenChunkData(BaseModel):
    delta: str


class VerificationCompleteData(BaseModel):
    is_grounded: bool
    addresses_query: bool
    confidence_score: float
    provider_used: Literal["gemini-2.5-flash", "groq-llama-3.3-70b"]
    total_latency_ms: int


class ProviderFailoverData(BaseModel):
    from_provider: str
    to_provider: str
    reason: str


class NodeTransitionEvent(BaseModel):
    event: Literal["node_transition"] = "node_transition"
    data: NodeTransitionData


class RetrievalResultsEvent(BaseModel):
    event: Literal["retrieval_results"] = "retrieval_results"
    data: RetrievalResultsData


class GradingVerdictEvent(BaseModel):
    event: Literal["grading_verdict"] = "grading_verdict"
    data: GradingVerdictData


class QueryRewrittenEvent(BaseModel):
    event: Literal["query_rewritten"] = "query_rewritten"
    data: QueryRewrittenData


class TokenChunkEvent(BaseModel):
    event: Literal["token_chunk"] = "token_chunk"
    data: TokenChunkData


class VerificationCompleteEvent(BaseModel):
    event: Literal["verification_complete"] = "verification_complete"
    data: VerificationCompleteData


class ProviderFailoverEvent(BaseModel):
    event: Literal["provider_failover"] = "provider_failover"
    data: ProviderFailoverData


AgentSSEEvent = Annotated[
    NodeTransitionEvent
    | RetrievalResultsEvent
    | GradingVerdictEvent
    | QueryRewrittenEvent
    | TokenChunkEvent
    | VerificationCompleteEvent
    | ProviderFailoverEvent,
    Field(discriminator="event"),
]
```

- [ ] **Step 5: Write `domain/exceptions.py` and `domain/ports.py`**

```python
# exceptions.py
class AgenticCragError(Exception):
    code: str = "ERR_UNKNOWN"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code


class EmptyCorpusError(AgenticCragError):
    code = "E01_EMPTY_CORPUS"


class ProviderQuotaError(AgenticCragError):
    code = "E02_PROVIDER_QUOTA"


class WebSearchTimeoutError(AgenticCragError):
    code = "E04_WEB_SEARCH_TIMEOUT"


class MalformedPdfError(AgenticCragError):
    code = "E06_SCANNED_OR_EMPTY_PDF"


class QueryTooLongError(AgenticCragError):
    code = "E08_QUERY_TOO_LONG"
```

```python
# ports.py
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
```

- [ ] **Step 6: Create empty package `__init__.py` files**

Create empty `__init__.py` for: `agentic_crag`, `domain`, `adapters`, `adapters/llm`, `adapters/retrieval`, `adapters/search`, `orchestration`, `api`, `api/routes`.

- [ ] **Step 7: Install and typecheck domain**

Run from `backend/`:

```bash
uv sync --extra dev
uv run mypy --strict src/agentic_crag/domain src/agentic_crag/config.py
uv run ruff check src/agentic_crag/domain src/agentic_crag/config.py
```

Expected: exit 0.

---

### Task 3: FastAPI health endpoint + unit test

**Files:**
- Create: `backend/src/agentic_crag/api/main.py`
- Create: `backend/src/agentic_crag/api/dependencies.py`
- Create: `backend/tests/unit/test_health.py`
- Create: `backend/tests/__init__.py`, `backend/tests/unit/__init__.py` (optional empty)

**Interfaces:**
- Consumes: `Settings`, `create_app` pattern
- Produces: `GET /health` → `{"status": "ok"}`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/unit/test_health.py
from fastapi.testclient import TestClient

from agentic_crag.api.main import create_app


def test_health_returns_ok() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test — expect fail**

```bash
cd backend && uv run pytest tests/unit/test_health.py -v
```

Expected: FAIL (import or attribute error for `create_app`).

- [ ] **Step 3: Implement `api/main.py` and empty `dependencies.py`**

```python
# dependencies.py
"""FastAPI dependency injection container (populated in later phases)."""
```

```python
# main.py
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agentic_crag.config import settings


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 4: Run test — expect pass**

```bash
cd backend && uv run pytest tests/unit/test_health.py -v
uv run ruff check src tests
uv run mypy --strict src/agentic_crag
```

Expected: all PASS / exit 0.

---

### Task 4: Docker Compose Qdrant

**Files:**
- Create: `docker-compose.yml`

**Interfaces:**
- Produces: `http://localhost:6333` Qdrant HTTP API

- [ ] **Step 1: Write compose file**

```yaml
services:
  qdrant:
    image: qdrant/qdrant:v1.12.5
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    healthcheck:
      test: ["CMD-SHELL", "bash -c 'exec 3<>/dev/tcp/127.0.0.1/6333'"]
      interval: 5s
      timeout: 3s
      retries: 10

volumes:
  qdrant_data:
```

- [ ] **Step 2: Start and verify**

```bash
docker compose up -d
docker compose ps
curl -s http://localhost:6333/readyz
```

Expected: service healthy / ready response (or HTTP 200 from `/readyz`).

---

### Task 5: Next.js frontend stub + README finish

**Files:**
- Create: `frontend/` via `create-next-app`
- Modify: `frontend/app/page.tsx` (or `src/app/page.tsx`)
- Modify: `README.md`

**Interfaces:**
- Produces: static home page title only

- [ ] **Step 1: Scaffold Next app**

```bash
npx create-next-app@15 frontend --typescript --tailwind --eslint --app --src-dir --no-import-alias --turbopack
```

If interactive prompts appear, choose defaults matching: App Router, TS, Tailwind, ESLint, `src/`.

- [ ] **Step 2: Replace home page**

```tsx
export default function Home() {
  return (
    <main style={{ padding: "4rem 1.5rem", fontFamily: "system-ui, sans-serif" }}>
      <h1>Agentic CRAG Workbench</h1>
      <p>Phase 0 scaffold — interactive agent canvas lands in later phases.</p>
    </main>
  );
}
```

- [ ] **Step 3: Smoke-run frontend**

```bash
cd frontend && npm run dev
```

Expected: page loads at `http://localhost:3000` with the title above.

- [ ] **Step 4: Finalize README quick start**

Replace Quick start section with run commands for compose, `uv run uvicorn agentic_crag.api.main:app --reload --port 8000`, and `npm run dev`, plus links to design/plan/roadmap under `docs/superpowers/`.

- [ ] **Step 5: Phase 0 exit checklist**

- [ ] `uv run pytest` green
- [ ] `ruff` + `mypy --strict` green
- [ ] Qdrant healthy
- [ ] Next page shows title
- [ ] No API keys in source

---

## Self-review

1. **Spec coverage:** Layout, domain stubs, health API, compose, frontend stub, AGENTS/env/README — all tasked.
2. **Placeholders:** None intentional; create-next-app flags may need local adjust if CLI version differs.
3. **Types:** `DocumentChunk` / ports / SSE event names match design + UI spec discriminators.
