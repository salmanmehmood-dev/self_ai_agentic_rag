"""E01 cold-start: ingest sample markdown when the vector store is empty.

Caller: api/main.py lifespan + POST /api/v1/ingest/sample.
Force=true wipes stale llama-3.3 chunks after corpus updates.
"""

from __future__ import annotations

from pathlib import Path

from agentic_crag.adapters.retrieval.ingest import MarkdownIngestService

# backend/src/agentic_crag/adapters/retrieval/sample_bootstrap.py
# → parents[4] = backend/
_SAMPLE_DIR = Path(__file__).resolve().parents[4] / "data" / "sample_corpus"


async def ensure_sample_corpus(
    ingest: MarkdownIngestService,
    *,
    force: bool = False,
) -> dict[str, int | str | bool]:
    """If collection has 0 points (or force), ingest every ``*.md`` under sample_corpus."""
    if force:
        await ingest.reset_collection()
    else:
        count = await ingest.point_count()
        if count > 0:
            return {"status": "ready", "points": count, "ingested": 0, "forced": False}

    if not _SAMPLE_DIR.is_dir():
        return {"status": "missing_sample_dir", "points": 0, "ingested": 0, "forced": force}

    ingested = 0
    for path in sorted(_SAMPLE_DIR.glob("*.md")):
        markdown = path.read_text(encoding="utf-8")
        ingested += await ingest.ingest_markdown(path.name, markdown)

    final = await ingest.point_count()
    print(
        f"[agentic-crag] E01 sample corpus: ingested {ingested} chunks "
        f"from {_SAMPLE_DIR} (points={final}, force={force})"
    )
    return {
        "status": "ingested",
        "points": final,
        "ingested": ingested,
        "forced": force,
    }
