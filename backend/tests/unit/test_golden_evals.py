"""Ensure offline golden eval harness stays green in CI."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[2]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from evals.run_evals import main, run_all  # noqa: E402


@pytest.mark.asyncio
async def test_golden_subset_all_pass() -> None:
    report = await run_all()
    failed = [c for c in report["cases"] if not c["pass"]]
    assert report["failed"] == 0, failed
    assert report["total"] == 8


def test_cli_exit_zero() -> None:
    assert main([]) == 0
