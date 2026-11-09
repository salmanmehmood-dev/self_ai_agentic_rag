"""AsyncSqliteSaver factory for LangGraph thread checkpoints.

Called from: api/main.py lifespan (build_crag_graph checkpointer=...).
No existing checkpoint helper in adapters/. Writes SQLite checkpoint rows via
langgraph AsyncSqliteSaver. User: "Implement the plan as specified" (1.3 AsyncSqliteSaver).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


async def open_sqlite_checkpointer(path: str) -> tuple[Any, Any]:
    """Open AsyncSqliteSaver at ``path`` (creates parent dirs)."""
    import aiosqlite
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(str(target))
    checkpointer = AsyncSqliteSaver(conn)
    await checkpointer.setup()
    return checkpointer, conn


async def close_sqlite_checkpointer(conn: Any) -> None:
    if conn is not None:
        await conn.close()
