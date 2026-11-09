from __future__ import annotations

from pathlib import Path

from typing import Annotated

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from agentic_crag.adapters.llm.free_models import (
    DEFAULT_EMBED_MODEL,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_GROQ_MODEL,
    DEFAULT_ROUTEWAY_MODEL,
    assert_free_gemini,
    assert_free_groq,
    assert_free_routeway,
)
from agentic_crag.adapters.llm.tier_presets import TierLimits, TierName, get_tier_limits

# backend/src/agentic_crag/config.py → backend/ and repo root
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_REPO_ROOT / ".env"), str(_BACKEND_DIR / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "agentic-crag"
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "crag_chunks"
    embedding_dims: int = 768
    gemini_api_key: str | None = None
    groq_api_key: str | None = None
    routeway_api_key: str | None = None
    gemini_model: str = DEFAULT_GEMINI_MODEL
    groq_model: str = DEFAULT_GROQ_MODEL
    routeway_model: str = DEFAULT_ROUTEWAY_MODEL
    embed_model: str = DEFAULT_EMBED_MODEL
    routeway_base_url: str = "https://api.routeway.ai/v1"
    tavily_api_key: str | None = None
    checkpoint_path: str = "data/checkpoints.sqlite"
    phoenix_collector_endpoint: str | None = None
    phoenix_project_name: str = "agentic-crag"
    expose_developer_errors: bool = True

    # Portfolio default: only free-tier model IDs (Gemini AI Studio / Groq free /
    # Routeway ``*:free``). Set FREE_MODELS_ONLY=false to unlock paid twins.
    free_models_only: bool = True
    # free | paid — rate-limit presets (keep free when using free models)
    llm_tier: TierName = "free"
    # Optional per-provider overrides (0 = use tier preset)
    gemini_rpm: int = 0
    gemini_rpd: int = 0
    groq_rpm: int = 0
    groq_rpd: int = 0
    routeway_rpm: int = 0
    routeway_rpd: int = 0
    embed_rpm: int = 0
    tavily_rpm: int = 0
    chat_per_ip_rpm: int = 0
    llm_request_timeout_s: float = 45.0

    local_dev_mode: bool = True
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "qwen2.5:3b"
    # Local CPU grading often exceeds the cloud 45s budget.
    ollama_timeout_s: float = 180.0
    local_embed_model: str = "BAAI/bge-small-en-v1.5"
    local_embedding_dims: int = 384
    qdrant_collection_local: str = "crag_chunks_local"

    @property
    def active_embedding_dims(self) -> int:
        return self.local_embedding_dims if self.local_dev_mode else self.embedding_dims

    @property
    def active_qdrant_collection(self) -> str:
        return self.qdrant_collection_local if self.local_dev_mode else self.qdrant_collection

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, value: object) -> object:
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return ["http://localhost:3000"]
            if raw.startswith("["):
                return value
            return [part.strip() for part in raw.split(",") if part.strip()]
        return value

    @field_validator("llm_tier", mode="before")
    @classmethod
    def _norm_tier(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @model_validator(mode="after")
    def _enforce_free_models(self) -> Settings:
        if not self.free_models_only:
            return self
        self.gemini_model = assert_free_gemini(self.gemini_model)
        self.groq_model = assert_free_groq(self.groq_model)
        self.routeway_model = assert_free_routeway(self.routeway_model)
        if self.llm_tier != "free":
            # Keep rate-limit presets aligned with free quotas.
            self.llm_tier = "free"
        return self

    def tier_limits(self) -> TierLimits:
        base = get_tier_limits(self.llm_tier)
        gemini = base.gemini
        groq = base.groq
        routeway = base.routeway
        embed = base.embed
        tavily = base.tavily
        if self.gemini_rpm > 0 or self.gemini_rpd > 0:
            gemini = type(gemini)(
                rpm=self.gemini_rpm or gemini.rpm,
                rpd=self.gemini_rpd or gemini.rpd,
                min_interval_s=gemini.min_interval_s,
                max_wait_s=gemini.max_wait_s,
            )
        if self.groq_rpm > 0 or self.groq_rpd > 0:
            groq = type(groq)(
                rpm=self.groq_rpm or groq.rpm,
                rpd=self.groq_rpd or groq.rpd,
                min_interval_s=groq.min_interval_s,
                max_wait_s=groq.max_wait_s,
            )
        if self.routeway_rpm > 0 or self.routeway_rpd > 0:
            routeway = type(routeway)(
                rpm=self.routeway_rpm or routeway.rpm,
                rpd=self.routeway_rpd or routeway.rpd,
                min_interval_s=routeway.min_interval_s,
                max_wait_s=routeway.max_wait_s,
            )
        if self.embed_rpm > 0:
            embed = type(embed)(
                rpm=self.embed_rpm,
                rpd=embed.rpd,
                min_interval_s=embed.min_interval_s,
                max_wait_s=embed.max_wait_s,
            )
        if self.tavily_rpm > 0:
            tavily = type(tavily)(
                rpm=self.tavily_rpm,
                rpd=tavily.rpd,
                min_interval_s=tavily.min_interval_s,
                max_wait_s=tavily.max_wait_s,
            )
        chat_rpm = self.chat_per_ip_rpm or base.chat_per_ip_rpm
        return TierLimits(
            gemini=gemini,
            groq=groq,
            routeway=routeway,
            embed=embed,
            tavily=tavily,
            chat_per_ip_rpm=chat_rpm,
            retry_base_s=base.retry_base_s,
            retry_max_s=base.retry_max_s,
            retry_attempts=base.retry_attempts,
        )


settings = Settings()
