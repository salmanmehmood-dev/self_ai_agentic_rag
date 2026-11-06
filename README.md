# Agentic CRAG Copilot

Corrective + Self-Reflective Agentic RAG (LangGraph) with a Next.js agent workbench.

## Status

Phase 0 scaffold. See `docs/superpowers/plans/2026-11-06-agentic-crag-phase-roadmap.md`.

## Quick start

```bash
# Infra: Qdrant (6333) + Phoenix UI (6006)
docker compose up -d

# Backend
cd backend && uv sync --extra dev
uv run uvicorn agentic_crag.api.main:app --reload --port 8000
# GET http://localhost:8000/health

# Frontend
cd frontend && npm install && npm run dev
```

CI runs on push/PR via `.github/workflows/ci.yml` (ruff, mypy, pytest, Next lint/build).

## Docs

- Design: `docs/superpowers/specs/2026-11-06-phase0-scaffold-design.md`
- Phase 0 plan: `docs/superpowers/plans/2026-11-06-phase0-scaffold.md`
- Roadmap: `docs/superpowers/plans/2026-11-06-agentic-crag-phase-roadmap.md`
