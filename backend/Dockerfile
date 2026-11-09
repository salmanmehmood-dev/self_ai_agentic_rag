# Backend API image for local Compose and Render (GitHub Docker deploy).
# Root Directory on Render: backend/

FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.6.14 /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
COPY src ./src
COPY evals ./evals
COPY data ./data

RUN UV_LINK_MODE=copy uv sync --frozen --no-dev --no-editable

ENV PATH="/app/.venv/bin:$PATH"
ENV CHECKPOINT_PATH=/data/checkpoints.sqlite
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

RUN mkdir -p /data

EXPOSE 8000

# Render injects PORT; Compose defaults to 8000.
CMD ["sh", "-c", "uvicorn agentic_crag.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
