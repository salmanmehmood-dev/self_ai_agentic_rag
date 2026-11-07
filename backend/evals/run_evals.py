#!/usr/bin/env python3
"""Run golden CRAG path subset with mocked LLM/retriever/web (no live APIs).

Usage (from backend/):
  uv run python evals/run_evals.py
  uv run python evals/run_evals.py --json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any, TypeVar
from unittest.mock import AsyncMock

from pydantic import BaseModel

from agentic_crag.domain.entities import DocumentChunk
from agentic_crag.orchestration.graph import build_crag_graph
from agentic_crag.orchestration.schemas import (
    BatchGradeResult,
    ChunkEvaluation,
    RewriteResult,
    RouteSchema,
    SynthesisResult,
    VerifySchema,
)

T = TypeVar("T", bound=BaseModel)

_DATASET = Path(__file__).with_name("golden_dataset.json")
_ORPHAN_RE = re.compile(r"\[(\d+)\]")

_CHUNK = DocumentChunk(
    chunk_id="c1",
    source_file="sla.md",
    section_header="Failover",
    text="[Source: sla.md | Section: Failover]\nRetries on 429 then Groq failover.",
)
_WEB = DocumentChunk(
    chunk_id="w1",
    source_file="https://example.com/failover",
    section_header="Web",
    text="[Source: https://example.com/failover | Section: Web]\nPublic failover notes.",
    source_type="web",
)


class ScriptedLLM:
    def __init__(self, responses: list[BaseModel]) -> None:
        self._responses = list(responses)
        self.calls = 0

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[T],
        temperature: float = 0.0,
    ) -> T:
        del system_prompt, user_prompt, temperature
        self.calls += 1
        if not self._responses:
            raise AssertionError(f"LLM exhausted; next schema={response_schema.__name__}")
        item = self._responses.pop(0)
        if not isinstance(item, response_schema):
            raise AssertionError(
                f"expected {response_schema.__name__}, got {type(item).__name__}"
            )
        return item  # type: ignore[return-value]


def _pass_grade() -> BatchGradeResult:
    return BatchGradeResult(
        evaluations=[
            ChunkEvaluation(chunk_id="c1", relevant=True, confidence=0.92, reasoning="ok")
        ]
    )


def _reject_grade() -> BatchGradeResult:
    return BatchGradeResult(
        evaluations=[
            ChunkEvaluation(chunk_id="c1", relevant=False, confidence=0.2, reasoning="noise")
        ]
    )


def _script_for_path(path: str) -> tuple[ScriptedLLM, AsyncMock, AsyncMock]:
    reject = _reject_grade()
    if path == "happy_rag":
        llm = ScriptedLLM(
            [
                RouteSchema(route="rag", reason="kb"),
                _pass_grade(),
                SynthesisResult(answer="Failover retries then Groq. [1]"),
                VerifySchema(
                    is_grounded=True, addresses_query=True, confidence_score=0.9
                ),
            ]
        )
        retriever = AsyncMock()
        retriever.retrieve_hybrid = AsyncMock(return_value=[_CHUNK])
        return llm, retriever, AsyncMock()

    if path == "rewrite_then_pass":
        llm = ScriptedLLM(
            [
                RouteSchema(route="rag", reason="kb"),
                reject,
                RewriteResult(new_query="SLA failover policy", reason="expand"),
                _pass_grade(),
                SynthesisResult(answer="Rewritten path finds SLA. [1]"),
                VerifySchema(
                    is_grounded=True, addresses_query=True, confidence_score=0.88
                ),
            ]
        )
        retriever = AsyncMock()
        retriever.retrieve_hybrid = AsyncMock(return_value=[_CHUNK])
        return llm, retriever, AsyncMock()

    if path == "web_fallback":
        llm = ScriptedLLM(
            [
                RouteSchema(route="rag", reason="kb"),
                reject,
                RewriteResult(new_query="failover SLA policy", reason="expand"),
                reject,
                RewriteResult(new_query="Gemini Groq failover", reason="entities"),
                reject,
                SynthesisResult(answer="From web: failover notes. [1]"),
                VerifySchema(
                    is_grounded=True, addresses_query=True, confidence_score=0.8
                ),
            ]
        )
        retriever = AsyncMock()
        retriever.retrieve_hybrid = AsyncMock(return_value=[_CHUNK])
        web = AsyncMock()
        web.search = AsyncMock(return_value=[_WEB])
        return llm, retriever, web

    if path == "blocked":
        return ScriptedLLM([]), AsyncMock(), AsyncMock()

    if path == "hallucination_partial":
        llm = ScriptedLLM(
            [
                RouteSchema(route="rag", reason="kb"),
                _pass_grade(),
                SynthesisResult(answer="Invented claim [9]"),
                VerifySchema(
                    is_grounded=False,
                    addresses_query=True,
                    confidence_score=0.4,
                    critique="unsupported",
                ),
                SynthesisResult(answer="Still weak [1][9]"),
                VerifySchema(
                    is_grounded=False,
                    addresses_query=True,
                    confidence_score=0.3,
                    critique="still bad",
                ),
            ]
        )
        retriever = AsyncMock()
        retriever.retrieve_hybrid = AsyncMock(return_value=[_CHUNK])
        return llm, retriever, AsyncMock()

    if path == "orphan_cite_strip":
        llm = ScriptedLLM(
            [
                RouteSchema(route="rag", reason="kb"),
                _pass_grade(),
                SynthesisResult(answer="Failover policy. [1][9]"),
                VerifySchema(
                    is_grounded=True, addresses_query=True, confidence_score=0.85
                ),
            ]
        )
        retriever = AsyncMock()
        retriever.retrieve_hybrid = AsyncMock(return_value=[_CHUNK])
        return llm, retriever, AsyncMock()

    if path == "direct":
        llm = ScriptedLLM(
            [
                RouteSchema(route="direct", reason="greeting"),
                SynthesisResult(answer="Hello — how can I help?"),
            ]
        )
        return llm, AsyncMock(), AsyncMock()

    raise ValueError(f"unknown path script: {path}")


def _check_case(
    case: dict[str, Any], result: dict[str, Any], llm: ScriptedLLM
) -> list[str]:
    expect = case["expect"]
    errors: list[str] = []

    if "route_decision" in expect and result.get("route_decision") != expect["route_decision"]:
        errors.append(
            f"route_decision={result.get('route_decision')!r} "
            f"want {expect['route_decision']!r}"
        )

    if "web_fallback_triggered" in expect:
        got = bool(result.get("web_fallback_triggered"))
        if got != bool(expect["web_fallback_triggered"]):
            errors.append(f"web_fallback_triggered={got} want {expect['web_fallback_triggered']}")

    rewrite = int(result.get("rewrite_count") or 0)
    if "min_rewrite_count" in expect and rewrite < int(expect["min_rewrite_count"]):
        errors.append(f"rewrite_count={rewrite} < {expect['min_rewrite_count']}")
    if "max_rewrite_count" in expect and rewrite > int(expect["max_rewrite_count"]):
        errors.append(f"rewrite_count={rewrite} > {expect['max_rewrite_count']}")

    if "verification_status" in expect:
        report = result.get("verification_report")
        status = getattr(report, "status", None) if report is not None else None
        if status != expect["verification_status"]:
            errors.append(f"verification_status={status!r} want {expect['verification_status']!r}")

    if "max_hallucination_retries" in expect:
        retries = int(result.get("hallucination_retry_count") or 0)
        if retries > int(expect["max_hallucination_retries"]):
            errors.append(
                f"hallucination_retry_count={retries} > {expect['max_hallucination_retries']}"
            )
        if retries < 1 and expect["verification_status"] == "partial_verification":
            errors.append("expected at least one hallucination retry")

    if expect.get("require_citation"):
        draft = result.get("draft_answer") or ""
        if "[1]" not in draft:
            errors.append("missing [1] citation in draft_answer")

    if expect.get("forbid_orphan_citation"):
        draft = result.get("draft_answer") or ""
        graded = result.get("graded_chunks") or []
        max_idx = len(graded)
        for m in _ORPHAN_RE.finditer(draft):
            n = int(m.group(1))
            if max_idx < 1 or n < 1 or n > max_idx:
                errors.append(f"orphan citation [{n}] remains (max={max_idx})")

    if "llm_calls" in expect and llm.calls != int(expect["llm_calls"]):
        errors.append(f"llm_calls={llm.calls} want {expect['llm_calls']}")

    return errors


async def run_case(case: dict[str, Any]) -> dict[str, Any]:
    llm, retriever, web = _script_for_path(case["path"])
    graph = build_crag_graph(llm, retriever, web)
    result: dict[str, Any] = await graph.ainvoke(
        {
            "session_id": case["id"],
            "original_query": case["query"],
            "rewrite_count": 0,
            "hallucination_retry_count": 0,
            "node_trace": [],
        }
    )
    errors = _check_case(case, result, llm)
    return {
        "id": case["id"],
        "name": case["name"],
        "path": case["path"],
        "pass": len(errors) == 0,
        "errors": errors,
        "latency_note": "mocked",
    }


async def run_all(dataset_path: Path = _DATASET) -> dict[str, Any]:
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for case in payload["cases"]:
        rows.append(await run_case(case))
    passed = sum(1 for r in rows if r["pass"])
    return {
        "version": payload.get("version"),
        "total": len(rows),
        "passed": passed,
        "failed": len(rows) - passed,
        "cases": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline golden CRAG evals")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=_DATASET,
        help="Path to golden_dataset.json",
    )
    args = parser.parse_args(argv)
    report = asyncio.run(run_all(args.dataset))

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Golden evals: {report['passed']}/{report['total']} passed")
        for row in report["cases"]:
            mark = "PASS" if row["pass"] else "FAIL"
            print(f"  [{mark}] {row['id']} {row['name']}")
            for err in row["errors"]:
                print(f"         - {err}")

    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
