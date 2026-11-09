"""Unit tests for E01 sample corpus bootstrap (mocked store)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from agentic_crag.adapters.retrieval.sample_bootstrap import ensure_sample_corpus


@pytest.mark.asyncio
async def test_ensure_sample_skips_when_points_exist() -> None:
    ingest = MagicMock()
    ingest.point_count = AsyncMock(return_value=12)
    ingest.ingest_markdown = AsyncMock()

    result = await ensure_sample_corpus(ingest)

    assert result["status"] == "ready"
    assert result["points"] == 12
    ingest.ingest_markdown.assert_not_awaited()


@pytest.mark.asyncio
async def test_ensure_sample_force_resets_even_when_points_exist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    doc = tmp_path / "sla.md"
    doc.write_text("# SLA\n\nGroq openai/gpt-oss-120b failover.\n" * 3, encoding="utf-8")
    monkeypatch.setattr(
        "agentic_crag.adapters.retrieval.sample_bootstrap._SAMPLE_DIR",
        tmp_path,
    )
    ingest = MagicMock()
    ingest.reset_collection = AsyncMock()
    ingest.point_count = AsyncMock(return_value=3)
    ingest.ingest_markdown = AsyncMock(return_value=3)

    result = await ensure_sample_corpus(ingest, force=True)

    assert result["status"] == "ingested"
    assert result["forced"] is True
    ingest.reset_collection.assert_awaited_once()
    ingest.ingest_markdown.assert_awaited()


@pytest.mark.asyncio
async def test_ensure_sample_ingests_markdown_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    doc = tmp_path / "failover.md"
    doc.write_text("# Failover\n\nGemini 429 then Groq.\n" * 3, encoding="utf-8")
    monkeypatch.setattr(
        "agentic_crag.adapters.retrieval.sample_bootstrap._SAMPLE_DIR",
        tmp_path,
    )

    ingest = MagicMock()
    ingest.point_count = AsyncMock(side_effect=[0, 2])
    ingest.ingest_markdown = AsyncMock(return_value=2)

    result = await ensure_sample_corpus(ingest)

    assert result["status"] == "ingested"
    assert result["ingested"] == 2
    ingest.ingest_markdown.assert_awaited_once()
