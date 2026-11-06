# Agentic CRAG — Chat-Sized Phase Roadmap

**Goal:** Ship Corrective + Self-Reflective Agentic RAG with a Next.js observability workbench on free-tier APIs, one chatable phase at a time.

**Spec inputs:** root `system_architecture_hld_lld.md`, `interactive_ui_agent_workbench_specification.md`, `ai_coding_agent_directives_guardrails.md`, `clean_code_production_engineering_standards.md`.

| Phase | One-chat deliverable | Exit criteria | Skills |
| --- | --- | --- | --- |
| **0** | Monorepo scaffold: domain stubs, FastAPI `/health`, Next stub, Qdrant compose, `AGENTS.md`, `.env.example` | Health test green; Qdrant up; Next page loads | hexagonal, fastapi-patterns, docker-patterns, python-patterns |
| **1** | LLM failover gateway + structured-output adapter (Gemini primary, Groq fallback) with unit tests (mocked HTTP) | `generate_structured` + 429→Groq path tested | python-patterns; python-reviewer |
| **2** | Ingest pipeline + hybrid Qdrant retrieve (dense + sparse RRF) | Upload/sample ingest; retrieve returns top-K chunks | rag-pipeline-reviewer |
| **3** | LangGraph nodes 1–3 + edges (sanitize/route, hybrid retrieve, batch grade) + loop counters | Graph runs happy path to synthesize *or* rewrite edge with mocks | python-reviewer |
| **4** | Nodes 4–7 (rewrite, web fallback, synthesize, verify) + hard ceilings `MAX_QUERY_REWRITES=2`, `MAX_HALLUCINATION_RETRIES=1` | Full cyclic path with mocked ports | python-reviewer |
| **5** | FastAPI SSE `POST /api/v1/chat/stream` emitting typed events | curl/EventSource receives `node_transition` + `token_chunk` | fastapi-patterns |
| **6** | Next workbench: chat pane + thought timeline + SSE client | Live tokens + stepper from real/mock stream | react/typescript-reviewer |
| **7** | React Flow 7-node canvas + grader inspector | Nodes pulse on events; KEEP/FILTERED cards | react-reviewer |
| **8** | Recruiter presets + citation badges + evals drawer shell | Three scenario pills work; `[n]` opens inspector | react-reviewer |
| **9** | Golden eval set (subset OK) + CI lint/type/test (+ optional Phoenix) | CI green; eval script runnable | agent-eval; fix-ci |

**Rule:** Do not start phase N+1 until phase N exit criteria pass. Write a dedicated `docs/superpowers/plans/YYYY-MM-DD-phaseN-*.md` before executing each phase.

**Phase 0 detailed plan:** `docs/superpowers/plans/2026-11-06-phase0-scaffold.md`

**Design:** `docs/superpowers/specs/2026-11-06-phase0-scaffold-design.md`
