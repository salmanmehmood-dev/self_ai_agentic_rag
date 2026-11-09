# Deploy: Vercel + Render + Qdrant Cloud

GitHub-connected auto-deploy (easiest path). Push to your linked branch → Vercel rebuilds the UI, Render rebuilds the API. No manual image push.

```
Browser → Vercel (Next.js) → SSE → Render (FastAPI / LangGraph) → Qdrant Cloud
                                                      ↓
                                         Gemini → Groq → Routeway
```

## 1. Qdrant Cloud (free)

1. Create a free cluster in [Qdrant Cloud](https://cloud.qdrant.io/).
2. Copy **Cluster URL** (port `6333`) and **API key**.
3. Use collection name **`crag_chunks`** (768-d Gemini embeddings).  
   Do **not** use `crag_chunks_local` (384-d FastEmbed / laptop only).

On first API boot with an empty collection, sample corpus auto-ingest runs (E01).

## 2. Render API (GitHub → Docker)

Repo already linked in Render? Create a **Web Service**:

| Setting | Value |
|---------|--------|
| Language / Runtime | **Docker** |
| Root Directory | `backend` |
| Dockerfile Path | `./Dockerfile` (default under root dir) |
| Health Check Path | `/ready` |
| Persistent disk | Mount **`/data`** (Sqlite checkpoints) |

### Environment variables

```
LOCAL_DEV_MODE=false
GEMINI_API_KEY=
GROQ_API_KEY=
ROUTEWAY_API_KEY=
ROUTEWAY_MODEL=deepseek-v4.1-flash:free
TAVILY_API_KEY=
QDRANT_URL=https://YOUR-CLUSTER.qdrant.io:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=crag_chunks
CHECKPOINT_PATH=/data/checkpoints.sqlite
CORS_ORIGINS=https://YOUR-APP.vercel.app
EXPOSE_DEVELOPER_ERRORS=false
LLM_TIER=free
FREE_MODELS_ONLY=true
```

Deploy → open `https://YOUR-API.onrender.com/ready` (must be **200**).  
`GET /health` is liveness; `/ready` waits until the graph is wired.

Auto-redeploy: enable **Auto-Deploy** on the Git branch (e.g. `main`).

Optional: apply the Blueprint in repo-root [`render.yaml`](../render.yaml) if you prefer infra-as-code.

## 3. Vercel frontend (GitHub → Next.js)

1. [Vercel](https://vercel.com) → **Add New Project** → import the **same** GitHub repo.
2. Settings:

| Setting | Value |
|---------|--------|
| Framework Preset | **Next.js** |
| Root Directory | `frontend` |
| Build Command | `npm run build` (default) |

3. Environment variable:

```
NEXT_PUBLIC_API_URL=https://YOUR-API.onrender.com
```

4. Deploy. Copy the `*.vercel.app` URL.

5. Go back to Render → set `CORS_ORIGINS` to that exact origin → **Manual Deploy** once.

## 4. Smoke test

1. Open the Vercel URL.
2. Run scenario **01 Failover path** (or ask: *How does Gemini to Groq failover work after a 429?*).
3. Confirm: thought timeline, live graph nodes, graded chunks, cited answer stream.

## 5. Paste live URLs into README

Update the **Live demo** section in root `README.md` with:

- Workbench: `https://….vercel.app`
- API ready: `https://….onrender.com/ready`

## Local parity (laptop)

```bash
cp .env.example .env   # fill keys
make docker            # Compose forces LOCAL_DEV_MODE=false on api + local Qdrant
# UI http://localhost:3000 · API http://localhost:8000/ready
```

Cloud deploys never use Ollama or `crag_chunks_local`. Mixing 384-d / 768-d collections fails boot (`ERR_EMBED_DIM_MISMATCH`).

## Checklist

- [ ] No secrets committed (`.env` gitignored)
- [ ] Dockerfile honors `$PORT` (Render)
- [ ] `LOCAL_DEV_MODE=false` on Render
- [ ] `QDRANT_COLLECTION=crag_chunks` (768-d)
- [ ] `CORS_ORIGINS` matches Vercel origin
- [ ] Sample corpus present under `backend/data/sample_corpus/`
- [ ] `/ready` returns 200 before sharing the demo link
