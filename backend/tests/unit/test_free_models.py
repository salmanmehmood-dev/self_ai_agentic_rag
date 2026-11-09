"""Free-model allowlist + Settings enforcement.

Module under test: free_models.py + config.Settings._enforce_free_models.
Existing tests: none for free_models (new). User: only free models of routeway
and other api.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agentic_crag.adapters.llm.free_models import (
    assert_free_gemini,
    assert_free_groq,
    assert_free_routeway,
)
from agentic_crag.config import Settings


def test_routeway_requires_free_suffix() -> None:
    assert assert_free_routeway("deepseek-v4.1-flash:free") == "deepseek-v4.1-flash:free"
    with pytest.raises(ValueError, match=":free"):
        assert_free_routeway("gpt-4o-mini")


def test_gemini_groq_allowlists() -> None:
    assert assert_free_gemini("gemini-2.5-flash") == "gemini-2.5-flash"
    with pytest.raises(ValueError, match="allowlist"):
        assert_free_gemini("gemini-1.5-pro")
    assert assert_free_groq("openai/gpt-oss-120b") == "openai/gpt-oss-120b"
    with pytest.raises(ValueError, match="allowlist"):
        assert_free_groq("llama-3.3-70b-specdec")


def test_settings_rejects_paid_routeway() -> None:
    with pytest.raises(ValidationError):
        Settings(free_models_only=True, routeway_model="gpt-4o-mini")


def test_settings_allows_paid_when_flag_off() -> None:
    s = Settings(
        free_models_only=False,
        routeway_model="gpt-4o-mini",
        llm_tier="paid",
    )
    assert s.routeway_model == "gpt-4o-mini"
    assert s.llm_tier == "paid"


def test_settings_defaults_stay_free() -> None:
    s = Settings(free_models_only=True)
    assert s.llm_tier == "free"
    assert s.routeway_model.endswith(":free")
    assert "flash" in s.gemini_model
