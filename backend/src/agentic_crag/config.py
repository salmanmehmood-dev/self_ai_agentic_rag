from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/src/agentic_crag/config.py → backend/ and repo root
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Repo-root .env first; backend/.env overrides when present.
        env_file=(str(_REPO_ROOT / ".env"), str(_BACKEND_DIR / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "agentic-crag"
    cors_origins: list[str] = ["http://localhost:3000"]
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "crag_chunks"
    embedding_dims: int = 768
    gemini_api_key: str | None = None
    groq_api_key: str | None = None
    tavily_api_key: str | None = None


settings = Settings()
