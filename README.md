# Agentic CRAG Copilot

Corrective + Self-Reflective Agentic RAG (LangGraph) with a Next.js observability workbench — Gemini primary, Groq failover, hybrid Qdrant retrieve, Tavily web fallback, Phoenix traces.

## Live demo

> **URL:** _add your Railway web URL after first deploy_ (see [docs/DEPLOY_RAILWAY.md](docs/DEPLOY_RAILWAY.md))

## What recruiters should notice

- **Self-RAG happy path = 4 LLM calls**: Route → batch Grade → Synthesize → Verify (verify stays separate).
- **Corrective loop**: rewrite ≤2, then Tavily/DDGS web fallback; hallucination retry ≤1 → amber `partial_verification`.
- **Free-tier models only** (default): Gemini Flash + Groq `openai/gpt-oss-120b` + Routeway `*:free`.
- **Failover**: Gemini 429/503 → Groq → Routeway (`provider_failover` SSE).
- **Workbench**: React Flow canvas, grader inspector, citation badges, evals drawer (golden offline metrics).

## Quick start (Docker)

```bash
cp .env.example .env   # fill GEMINI_API_KEY + GROQ_API_KEY (ROUTEWAY_API_KEY optional)
make docker            # or: make docker-d  (detached)
# UI http://localhost:3000 · API http://localhost:8000/health · Phoenix http://localhost:6006
# make down | make logs | make health
```

## Quick start (dev)

```bash
cp .env.example .env
docker compose up -d qdrant phoenix

cd backend && uv sync --extra dev
uv run uvicorn agentic_crag.api.main:app --reload --port 8000

cd frontend && cp .env.local.example .env.local && npm ci && npm run dev
```

## Dual runtime (`LOCAL_DEV_MODE`)

Default in `.env.example` is **local** (`LOCAL_DEV_MODE=true`): API can boot without cloud LLM keys. Factory: `backend/src/agentic_crag/adapters/runtime_factory.py`.

| | **Local** | **Cloud** |
| --- | --- | --- |
| Flag | `LOCAL_DEV_MODE=true` | `LOCAL_DEV_MODE=false` |
| LLM | Ollama OpenAI-compatible API (`OLLAMA_BASE_URL`, default `qwen2.5:3b`) | `LLMGateway`: Gemini → Groq → Routeway |
| Embeddings | FastEmbed `BAAI/bge-small-en-v1.5` (384-d) | `gemini-embedding-001` (768-d) |
| Qdrant collection | `crag_chunks_local` | `crag_chunks` |
| Keys | Qdrant URL; **no** `GEMINI_API_KEY` / `GROQ_API_KEY` for boot | `GEMINI_API_KEY`, `GROQ_API_KEY` (+ optional `ROUTEWAY_API_KEY`) |

**Local prerequisites:** Qdrant running (`docker compose up -d qdrant`), [Ollama](https://ollama.com/) with `ollama pull qwen2.5:3b`. Ollama down → fail-fast error (no cloud failover).

**Cloud:** Same as historical stack; set keys in `.env` and `LOCAL_DEV_MODE=false`.

Do not reuse one Qdrant collection across modes — dense vector size differs (384 vs 768). Mismatch aborts startup (`ERR_EMBED_DIM_MISMATCH`).

Design: [docs/superpowers/specs/2026-11-09-dual-runtime-design.md](docs/superpowers/specs/2026-11-09-dual-runtime-design.md)

## Quality gates

```bash
cd backend
uv run ruff check src tests evals
uv run mypy --strict src/agentic_crag
uv run pytest
uv run python evals/run_evals.py   # golden 30/30 mocked
```

CI: `.github/workflows/ci.yml` (ruff, mypy, pytest unit+integration, golden 30, Next lint/build).

## Architecture (short)

```
Browser → Next workbench → FastAPI SSE → LangGraph CRAG
                              ├─ LLMGateway (Gemini → Groq → Routeway free)
                              ├─ Qdrant hybrid RRF (+ sample corpus E01)
                              ├─ Tavily → DuckDuckGo (E04)
                              ├─ AsyncSqliteSaver threads
                              └─ Phoenix OTEL (optional endpoint)
```

## LLM rate limits (free ↔ paid)

`FREE_MODELS_ONLY=true` (default) locks Gemini/Groq allowlists + Routeway `*:free` IDs. `LLM_TIER=free` rate presets throttle before vendor 429s. Failover: **Gemini → Groq → Routeway**. Override models only within free allowlists (`GEMINI_MODEL`, `GROQ_MODEL`, `ROUTEWAY_MODEL`). Set `FREE_MODELS_ONLY=false` only if you intentionally use paid twins.

## Deploy (Railway)

Step-by-step: [docs/DEPLOY_RAILWAY.md](docs/DEPLOY_RAILWAY.md). Use **Qdrant Cloud** free tier for vectors; set `CORS_ORIGINS` to the Railway web origin. Set `LLM_TIER=paid` when you upgrade API plans.

## Docs

- Agent rules: `AGENTS.md`
- HLD: `system_architecture_hld_lld.md`
- Phase roadmap: `docs/superpowers/plans/2026-11-06-agentic-crag-phase-roadmap.md`
