# Deploy to Railway (portfolio demo)

Readers: you (operator) + recruiters following README. No secrets in this file.
User plan: public Railway URL (choice B).

## Services

| Service | Root dir | Notes |
| --- | --- | --- |
| **api** | `backend/` | Dockerfile → uvicorn `:8000` |
| **web** | `frontend/` | Dockerfile; set build arg `NEXT_PUBLIC_API_URL` to public api URL |
| **Qdrant** | Qdrant Cloud free cluster | Set `QDRANT_URL` + `QDRANT_API_KEY` on api |
| **Phoenix** | Optional | Set `PHOENIX_COLLECTOR_ENDPOINT` (Cloud or self-hosted) |

## Steps

1. Create a Railway project; connect this GitHub repo.
2. Add service **api**: Root Directory `backend`, Dockerfile builder.
3. Attach a volume mounted at `/data` for Sqlite checkpoints.
4. Set api variables (from rotated keys — never paste into chat):

```
LOCAL_DEV_MODE=false
GEMINI_API_KEY=
GROQ_API_KEY=
ROUTEWAY_API_KEY=
ROUTEWAY_MODEL=deepseek-v4.1-flash:free
TAVILY_API_KEY=
QDRANT_URL=https://YOUR-CLUSTER.qdrant.io:6333
QDRANT_API_KEY=
CHECKPOINT_PATH=/data/checkpoints.sqlite
CORS_ORIGINS=https://YOUR-WEB.up.railway.app
PHOENIX_COLLECTOR_ENDPOINT=
LLM_TIER=free
# LLM_TIER=paid   # after upgrading Gemini/Groq plans
```

5. Add service **web**: Root Directory `frontend`. Build arg:

```
NEXT_PUBLIC_API_URL=https://YOUR-API.up.railway.app
```

6. Deploy both. Open web URL → ask Scenario 1 (failover). Confirm SSE events.
7. Paste the live web URL into root `README.md` under **Live demo**.

## Local parity

```bash
cp .env.example .env   # fill keys
docker compose up --build
# workbench http://localhost:3000  api http://localhost:8000/health  phoenix :6006
```
