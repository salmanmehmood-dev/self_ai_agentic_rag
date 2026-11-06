# Production Engineering & Clean Code Standards

## 1. Repository Blueprint (Hexagonal Architecture)

```text
agentic-crag-copilot/
├── .github/workflows/
│   └── ci.yml                      # Lint (Ruff), Typecheck (Mypy), Unit Tests, Eval Gate
├── backend/
│   ├── src/
│   │   ├── domain/                 # Pure Python + Pydantic v2 (Zero external SDK imports)
│   │   │   ├── entities.py         # DocumentChunk, GradedChunk, CitationItem
│   │   │   ├── events.py           # Typed SSE Event payloads
│   │   │   ├── exceptions.py       # Domain-specific exception hierarchy
│   │   │   └── ports.py            # Python Protocol interfaces (LLM, VectorDB, WebSearch)
│   │   ├── adapters/               # Concrete infrastructure implementations
│   │   │   ├── llm/
│   │   │   │   ├── gemini_client.py
│   │   │   │   ├── groq_client.py
│   │   │   │   └── failover_gateway.py
│   │   │   ├── retrieval/
│   │   │   │   ├── qdrant_hybrid.py
│   │   │   │   └── chunker.py      # Semantic & AST-aware document splitter
│   │   │   └── search/
│   │   │       └── web_search.py   # Tavily primary + DuckDuckGo fallback
│   │   ├── orchestration/          # LangGraph Cyclic State Machine
│   │   │   ├── state.py            # GraphState TypedDict & reducers
│   │   │   ├── nodes.py            # Pure async node functions
│   │   │   ├── edges.py            # Conditional routing functions
│   │   │   └── graph.py            # StateGraph compilation & checkpointer
│   │   ├── api/                    # FastAPI Delivery Layer
│   │   │   ├── main.py             # Lifespan context manager, CORS, middleware
│   │   │   ├── dependencies.py     # Dependency injection container
│   │   │   ├── routes/
│   │   │   │   ├── chat.py         # SSE streaming endpoint
│   │   │   │   ├── ingest.py       # Document upload & indexing status
│   │   │   │   └── benchmarks.py   # Pre-computed Ragas telemetry endpoint
│   │   └── config.py               # pydantic-settings BaseSettings
│   ├── evals/                      # Automated Ragas / DeepEval suite
│   │   ├── golden_dataset.json     # 30 curated multi-hop & adversarial test cases
│   │   └── run_evals.py
│   ├── tests/
│   │   ├── unit/                   # Fast deterministic tests (mocked ports)
│   │   └── integration/            # End-to-end graph traversal tests
│   └── pyproject.toml              # uv / Poetry dependency lock & tool configs
├── frontend/                       # Next.js 15 App Router (Interactive Agent Workbench)
└── docker-compose.yml              # One-command startup: Backend + Frontend + Qdrant + Phoenix
```

---

## 2. Python Coding Standards

### 2.1 Dependency Inversion via `typing.Protocol`
Never couple LangGraph nodes directly to `google.genai` or `qdrant_client`. Define structural interfaces in `src/domain/ports.py`:

```python
from typing import Protocol, TypeVar
from pydantic import BaseModel
from src.domain.entities import DocumentChunk

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
    async def retrieve_hybrid(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[DocumentChunk]: ...
```

### 2.2 Configuration Management (`pydantic-settings`)
* **Forbidden**: `os.getenv("GEMINI_API_KEY")` scattered across files.
* **Required**: Centralized `Settings` class in `src/config.py` validated at application startup. If a required key is missing, fail immediately during FastAPI lifespan startup with a clear diagnostic message.

### 2.3 Async Concurrency & Resource Lifecycles
* Initialize expensive clients (`AsyncQdrantClient`, `httpx.AsyncClient`, embedding models) **once** inside FastAPI's `lifespan` async context manager and attach them to `app.state`.
* Never instantiate `SentenceTransformer` or `FastEmbed` inside a request handler.
* Use `asyncio.TaskGroup` (Python 3.11+) for structured concurrency so child tasks are automatically cancelled if a sibling raises an unhandled exception.

### 2.4 Structured Logging & Correlation IDs
* Every incoming HTTP request receives an `X-Correlation-ID` header (or generates a UUIDv4).
* Bind `correlation_id`, `session_id`, and `current_node` using `structlog.contextvars`.
* Log every node transition with exact duration in milliseconds (`duration_ms`), token usage (`input_tokens`, `output_tokens`), and model provider used (`gemini-2.5-flash` vs `groq-llama-3.3-70b`).

---

## 3. Document Ingestion & Chunking Standards
A RAG system is only as strong as its chunking pipeline:
1. **Structure-Aware Parsing**: Use `Docling` or `PyMuPDF4LLM` to preserve Markdown headers, tables, and code blocks rather than naive character splitting.
2. **Parent-Child / Contextual Headers**: Prepend the document title and hierarchical section path (e.g., `[Source: AWS_EKS_SLA.pdf | Section: 4.2 Failover Policy]`) to every chunk before generating dense and sparse embeddings.
3. **Deterministic Chunk IDs**: Generate UUIDv5 deterministic IDs using `uuid5(NAMESPACE_DNS, f"{doc_hash}:{chunk_index}")` so re-ingesting the same document performs an idempotent upsert rather than creating duplicate chunks.