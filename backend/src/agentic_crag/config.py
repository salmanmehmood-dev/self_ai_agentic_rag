from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "agentic-crag"
    cors_origins: list[str] = ["http://localhost:3000"]
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "crag_chunks"
    embedding_dims: int = 768
    gemini_api_key: str | None = None
    groq_api_key: str | None = None
    tavily_api_key: str | None = None


settings = Settings()
