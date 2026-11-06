"""E07 orphan citation stripping."""

from agentic_crag.orchestration.citations import strip_orphan_citations


def test_strip_orphan_citations_keeps_valid_only() -> None:
    text = "Claim [1] and junk [9] plus [2]."
    assert strip_orphan_citations(text, max_index=2) == "Claim [1] and junk  plus [2]."
