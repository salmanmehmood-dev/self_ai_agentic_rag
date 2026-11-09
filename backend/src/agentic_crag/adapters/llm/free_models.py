"""Free-tier model allowlists (portfolio default).

Caller: config.Settings validators + api.main when FREE_MODELS_ONLY=true.
Routeway free IDs must end with ``:free``. Gemini/Groq use AI Studio / Groq
free-tier model IDs (no paid PAYG twins).
No prior free_models module (Grep: only defaults in gemini/groq/routeway clients).
User: "this project should use only free models of routeway and other api"
"""

from __future__ import annotations

# Google AI Studio free-tier chat models
FREE_GEMINI_MODELS: frozenset[str] = frozenset(
    {
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
    }
)

# Groq free / developer-tier chat models
FREE_GROQ_MODELS: frozenset[str] = frozenset(
    {
        "openai/gpt-oss-120b",
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile",
        "gemma2-9b-it",
    }
)

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
DEFAULT_ROUTEWAY_MODEL = "deepseek-v4.1-flash:free"
DEFAULT_EMBED_MODEL = "gemini-embedding-001"


def assert_free_gemini(model: str) -> str:
    name = model.strip()
    if name not in FREE_GEMINI_MODELS:
        allowed = ", ".join(sorted(FREE_GEMINI_MODELS))
        msg = f"GEMINI_MODEL={name!r} not in free allowlist: {allowed}"
        raise ValueError(msg)
    return name


def assert_free_groq(model: str) -> str:
    name = model.strip()
    if name not in FREE_GROQ_MODELS:
        allowed = ", ".join(sorted(FREE_GROQ_MODELS))
        msg = f"GROQ_MODEL={name!r} not in free allowlist: {allowed}"
        raise ValueError(msg)
    return name


def assert_free_routeway(model: str) -> str:
    name = model.strip()
    if not name.endswith(":free"):
        msg = (
            f"ROUTEWAY_MODEL={name!r} must end with ':free' "
            "(portfolio uses Routeway free models only)"
        )
        raise ValueError(msg)
    return name
