"""Tavily-primary optional; DuckDuckGo fallback with 4s timeout (E04)."""

from __future__ import annotations

import asyncio
import re
import uuid
from collections.abc import Awaitable, Callable

from agentic_crag.domain.entities import DocumentChunk
from agentic_crag.domain.exceptions import WebSearchTimeoutError

SearchFn = Callable[[str, int], Awaitable[list[tuple[str, str, str]]]]


def _chunk_web_text(text: str, *, max_chars: int = 1600) -> list[str]:
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return []
    if len(clean) <= max_chars:
        return [clean]
    return [clean[i : i + max_chars] for i in range(0, len(clean), max_chars)]


def _duckduckgo_search_sync(query: str, max_results: int) -> list[tuple[str, str, str]]:
    from duckduckgo_search import DDGS

    rows: list[tuple[str, str, str]] = []
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=max_results)
        for item in results:
            title = str(item.get("title") or "web")
            href = str(item.get("href") or item.get("link") or "web://unknown")
            body = str(item.get("body") or item.get("snippet") or "")
            rows.append((title, href, body))
    return rows


async def _duckduckgo_search(query: str, max_results: int) -> list[tuple[str, str, str]]:
    return await asyncio.to_thread(_duckduckgo_search_sync, query, max_results)


class WebSearchAdapter:
    def __init__(
        self,
        *,
        timeout_s: float = 4.0,
        search_fn: SearchFn | None = None,
    ) -> None:
        self._timeout_s = timeout_s
        self._search_fn = search_fn or _duckduckgo_search

    async def search(self, query: str, max_results: int = 5) -> list[DocumentChunk]:
        try:
            rows = await asyncio.wait_for(
                self._search_fn(query, max_results),
                timeout=self._timeout_s,
            )
        except TimeoutError as exc:
            raise WebSearchTimeoutError(f"web search timed out: {exc}") from exc

        chunks: list[DocumentChunk] = []
        for title, href, body in rows:
            for i, piece in enumerate(_chunk_web_text(body)):
                chunks.append(
                    DocumentChunk(
                        chunk_id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{href}:{i}")),
                        source_file=href,
                        section_header=title,
                        text=f"[Source: {href} | Section: {title}]\n{piece}",
                        source_type="web",
                    )
                )
        return chunks[:max_results]
