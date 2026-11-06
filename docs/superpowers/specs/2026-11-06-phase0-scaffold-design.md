# Phase 0 Scaffold Design — Agentic CRAG Copilot

**Date:** 2026-11-06  
**Status:** Approved (brainstorming)  
**Scope:** Repository basis only — no LangGraph nodes, no LLM calls, no SSE chat, no React Flow UI.

## GateGuard first-touch facts

1. **Supersedes / duplicates:** None. `docs/` is empty. Root MDs (`system_architecture_hld_lld.md`, `interactive_ui_agent_workbench_specification.md`, `ai_coding_agent_directives_guardrails.md`, `clean_code_production_engineering_standards.md`, `evaluation_observability_decisions_log.md`) remain product specs; this file is the Phase 0 *implementation design* only.
2. **Linked from:** `docs/superpowers/plans/2026-11-06-phase0-scaffold.md`, `docs/superpowers/plans/2026-11-06-agentic-crag-phase-roadmap.md`, and root `README.md` (when scaffold lands).
3. **Why new file:** Brainstorming skill requires approved designs at `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`. Root MDs are architecture/UI/guardrails, not a Phase 0 scaffold design.
4. **User instruction (verbatim):** `yes`

## 1. Goal

Create a runnable monorepo skeleton that matches the hexagonal blueprint in `clean_code_production_engineering_standards.md`, so later one-chat phases can fill adapters, graph nodes, SSE, and the Next.js workbench without reshaping the tree.

## 2. Approach (chosen)

**Monorepo scaffold from blueprint:** `backend/` + `frontend/` + root `docker-compose.yml` (Qdrant only) + `AGENTS.md` + `README.md` + `.env.example`. Backend exposes FastAPI `GET /health` only. Frontend is a Next.js 15 App Router TypeScript stub with a single title page. Domain entities and ports are typed stubs with no infrastructure imports.

Rejected alternatives: backend-only skeleton (incomplete portfolio shape); Nx/Turborepo (tooling overhead for MVP).

## 3. Source-of-truth documents (repo root)

| File | Role |
| --- | --- |
| `system_architecture_hld_lld.md` | CRAG + Self-RAG graph, state schema, node contracts |
| `interactive_ui_agent_workbench_specification.md` | Next.js workbench + typed SSE protocol |
| `ai_coding_agent_directives_guardrails.md` | Invariants for agents (copy into `AGENTS.md`) |
| `clean_code_production_engineering_standards.md` | Hexagonal tree, Protocols, settings, chunking |
| `evaluation_observability_decisions_log.md` | Misnamed near-duplicate of HLD/LLD — replace in a later docs phase with real eval/obs decisions |

Root MDs stay in place for Phase 0. Do not delete them.

## 4. Repository layout

```text
self_ai_agentic_rag/
├── AGENTS.md
├── README.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── docs/superpowers/
│   ├── specs/
│   └── plans/
├── backend/
│   ├── pyproject.toml
│   ├── src/agentic_crag/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── domain/
│   │   │   ├── entities.py
│   │   │   ├── events.py
│   │   │   ├── exceptions.py
│   │   │   └── ports.py
│   │   ├── adapters/
│   │   │   ├── __init__.py
│   │   │   ├── llm/
│   │   │   ├── retrieval/
│   │   │   └── search/
│   │   ├── orchestration/
│   │   │   └── __init__.py
│   │   └── api/
│   │       ├── main.py
│   │       ├── dependencies.py
│   │       └── routes/
│   │           └── __init__.py
│   └── tests/
│       └── unit/
│           └── test_health.py
└── frontend/          # Next.js 15 App Router, TypeScript strict
```

**Package decision:** Importable package is `agentic_crag` under `backend/src/agentic_crag/` (avoids bare `src` import ambiguity). Blueprint folder names (`domain/`, `adapters/`, `orchestration/`, `api/`) are preserved inside that package.

## 5. Components

### 5.1 Domain (pure Pydantic + stdlib + typing)

- **entities:** `DocumentChunk`, `GradedChunk`, `CitationItem`, `VerificationResult`, `NodeExecutionEvent` with fields from HLD §3.1.
- **events:** Pydantic models aligned to UI `AgentSSEEvent` discriminators (`node_transition`, `retrieval_results`, `grading_verdict`, `query_rewritten`, `token_chunk`, `verification_complete`, plus `provider_failover` from guardrails).
- **ports:** `LLMClientPort.generate_structured`, `HybridRetrieverPort.retrieve_hybrid`, `WebSearchPort.search`, `EmbedderPort.embed_documents` / `embed_query`.
- **exceptions:** hierarchy with stable codes for E01–E10 (message + `code` attribute). No raising in Phase 0.

Domain must import **zero** of: `langchain`, `langgraph`, `fastapi`, `qdrant_client`, `google.genai`.

### 5.2 Config

`Settings` via `pydantic-settings`. Phase 0: `app_name`, `cors_origins`, `qdrant_url` have defaults; API keys are optional strings so the health app boots without secrets.

### 5.3 API

FastAPI app factory + lifespan (no-op yield) + CORS from settings + `GET /health` → `{"status": "ok"}`. Empty `dependencies.py` and `routes/` package.

### 5.4 Docker

`docker-compose.yml`: service `qdrant` image `qdrant/qdrant` (pin a recent tag in the plan), ports `6333:6333` and `6334:6334`, named volume, healthcheck against HTTP ready endpoint. No backend/frontend containers in Phase 0.

### 5.5 Frontend

Next.js 15 App Router, TypeScript strict, Tailwind allowed. Single page: product title “Agentic CRAG Workbench” and short subtitle. No API client, no SSE, no React Flow.

### 5.6 Agent + env docs

- `AGENTS.md`: content from `ai_coding_agent_directives_guardrails.md`.
- `.env.example`: `GEMINI_API_KEY=`, `GROQ_API_KEY=`, `TAVILY_API_KEY=`, `QDRANT_URL=http://localhost:6333`.
- `README.md`: what the project is, stack table, how to run Qdrant / backend health / frontend stub, pointer to phase plans.

## 6. Data flow (Phase 0)

```
curl/localhost:8000/health → FastAPI → {"status":"ok"}
browser → Next stub (static)
docker compose → Qdrant only (no application traffic yet)
```

## 7. Error handling

- Optional API keys missing: app still starts.
- Invalid typed settings: fail fast at Settings load with a clear validation error.
- No chat, ingest, or graph error paths in Phase 0.

## 8. Testing and verification gate

1. `uv sync` in `backend/`
2. `pytest` — `test_health` passes
3. `ruff check` and `mypy --strict` pass on package
4. `docker compose up -d` — Qdrant healthy
5. `npm run dev` in `frontend/` — page loads

## 9. Explicit non-goals (Phase 0)

LangGraph graph, LLM/Qdrant/web adapters, ingest, SSE stream, React Flow, citation UI, Ragas, Phoenix/Langfuse, full CI workflow (optional later).

## 10. Skills / plugins for this project

| Phase | Skills |
| --- | --- |
| 0 scaffold | hexagonal-architecture, fastapi-patterns, docker-patterns, python-patterns |
| LLM / graph | fastapi-patterns, python-patterns; python-reviewer after edits |
| RAG retrieve/ingest | rag-pipeline-reviewer (later) |
| Frontend workbench | react-patterns / typescript-reviewer |
| Ship / agent behavior | agent-architecture-audit, agent-eval |
| Execution | writing-plans → executing-plans or subagent-driven-development |

## 11. Follow-on phases

See `docs/superpowers/plans/2026-11-06-agentic-crag-phase-roadmap.md`.  
Phase 0 tasks: `docs/superpowers/plans/2026-11-06-phase0-scaffold.md`.
