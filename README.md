# Agentic CRAG Workbench

Corrective + self-reflective agentic RAG (LangGraph) with a live Next.js instrument panel — typed SSE, hybrid retrieval, grader, failover, and citations.

## Live demo

| Layer | URL |
|-------|-----|
| **Workbench** | _add Vercel URL after deploy_ |
| **API ready** | _add `https://….onrender.com/ready`_ |

Deploy guide: [docs/DEPLOY.md](docs/DEPLOY.md)

## Stack (portfolio deploy)

| Layer | Provider | Why |
|-------|----------|-----|
| Frontend | **Vercel** | Native Next.js App Router, HTTPS, Git auto-deploy |
| Backend API | **Render** (Docker) | Persistent Docker + SSE + LangGraph; disk for Sqlite checkpoints |
| Vector DB | **Qdrant Cloud** free | Managed hybrid search — avoids OOM from in-process vectors |

Push to GitHub → Vercel + Render rebuild. No manual image push.

## What recruiters should notice

- **Self-RAG happy path = 4 LLM calls**: Route → batch Grade → Synthesize → Verify (verify stays separate).
- **Corrective loop**: rewrite ≤2, then Tavily/DDGS web fallback; hallucination retry ≤1 → amber `partial_verification`.
- **Free-tier models only** (default): Gemini Flash + Groq `openai/gpt-oss-120b` + Routeway `*:free`.
- **Failover**: Gemini 429/503 → Groq → Routeway (`provider_failover` SSE).
- **Workbench**: React Flow canvas, grader inspector, citation badges, evals drawer.

## Quick start (Docker)

```bash
cp .env.example .env   # fill GEMINI_API_KEY + GROQ_API_KEY (ROUTEWAY optional)
make docker            # or: make docker-d
# UI http://localhost:3000 · API http://localhost:8000/ready · Phoenix :6006
```

Compose runs the API in **cloud** mode (`LOCAL_DEV_MODE=false`) against the Compose Qdrant service.

## Quick start (dev)

```bash
cp .env.example .env
docker compose up -d qdrant phoenix

cd backend && uv sync --extra dev
uv run uvicorn agentic_crag.api.main:app --reload --port 8000

cd frontend && npm ci && npm run dev
# set frontend/.env.local → NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Dual runtime

| | Local | Cloud (Render / Compose api) |
| --- | --- | --- |
| Flag | `LOCAL_DEV_MODE=true` | `LOCAL_DEV_MODE=false` |
| LLM | Ollama (`qwen2.5:3b`) | Gemini → Groq → Routeway |
| Embeddings | FastEmbed 384-d | Gemini embed 768-d |
| Collection | `crag_chunks_local` | `crag_chunks` |

Do not mix collections across modes (dim mismatch aborts startup).

## Architecture

```
Browser → Next workbench → FastAPI SSE → LangGraph CRAG
                              ├─ LLMGateway (Gemini → Groq → Routeway)
                              ├─ Qdrant hybrid RRF (+ sample corpus E01)
                              ├─ Tavily → DuckDuckGo (E04)
                              └─ AsyncSqliteSaver checkpoints
```

Deep dive: [system_architecture_hld_lld.md](system_architecture_hld_lld.md)

## Quality gates

```bash
cd backend
uv run ruff check src tests evals
uv run mypy --strict src/agentic_crag
uv run pytest
uv run python evals/run_evals.py

cd frontend && npm run lint && npm run build
```

CI: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

## License

Portfolio / demo project. Add a license file if you open-source formally.
