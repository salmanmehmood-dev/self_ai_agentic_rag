# Agentic CRAG Copilot

Corrective + Self-Reflective Agentic RAG (LangGraph) with a Next.js agent workbench.

## Status

Phases 0–9 complete (scaffold → workbench → golden evals + CI). See roadmap.

## Quick start

```bash
# Once: copy keys into repo-root .env (GEMINI_API_KEY + GROQ_API_KEY required for chat)
cp .env.example .env

# Infra: Qdrant (6333) + Phoenix UI (6006)
docker compose up -d

# Backend (loads ../.env from repo root automatically)
cd backend && uv sync --extra dev
uv run uvicorn agentic_crag.api.main:app --reload --port 8000
# GET http://localhost:8000/health


# Frontend
cd frontend && cp .env.local.example .env.local && npm install && npm run dev
# Workbench → http://localhost:3000 (SSE → backend :8000)

# Offline golden evals (8/30 subset, mocked LLM — no API keys)
cd backend && uv run python evals/run_evals.py

# Corpus: sample docs auto-ingest on boot if Qdrant is empty (E01).
# Check / force: GET /api/v1/ingest/status · POST /api/v1/ingest/sample
```

CI runs on push/PR via `.github/workflows/ci.yml` (ruff, mypy, pytest, golden evals, Next lint/build).

## Docs

- Design: `docs/superpowers/specs/2026-11-06-phase0-scaffold-design.md`
- Phase 0 plan: `docs/superpowers/plans/2026-11-06-phase0-scaffold.md`
- Roadmap: `docs/superpowers/plans/2026-11-06-agentic-crag-phase-roadmap.md`
