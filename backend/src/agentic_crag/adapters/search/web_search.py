"""Tavily primary (optional key) + DuckDuckGo fallback with 4s timeout (E04)."""

from __future__ import annotations

import asyncio
import re
import uuid
from collections.abc import Awaitable, Callable

import httpx

from agentic_crag.adapters.llm.rate_limit import AsyncRateLimiter
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


async def _tavily_search(
    query: str,
    max_results: int,
    *,
    api_key: str,
    timeout_s: float,
) -> list[tuple[str, str, str]]:
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_s)) as client:
        resp = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "max_results": max_results,
                "include_answer": False,
            },
        )
        resp.raise_for_status()
        payload = resp.json()
    rows: list[tuple[str, str, str]] = []
    for item in payload.get("results") or []:
        title = str(item.get("title") or "web")
        href = str(item.get("url") or "web://unknown")
        body = str(item.get("content") or item.get("snippet") or "")
        rows.append((title, href, body))
    return rows


class WebSearchAdapter:
    def __init__(
        self,
        *,
        timeout_s: float = 4.0,
        tavily_api_key: str | None = None,
        search_fn: SearchFn | None = None,
        rate_limiter: AsyncRateLimiter | None = None,
    ) -> None:
        self._timeout_s = timeout_s
        self._tavily_api_key = tavily_api_key
        self._search_fn = search_fn
        self._limiter = rate_limiter

    async def search(self, query: str, max_results: int = 5) -> list[DocumentChunk]:
        if self._limiter is not None and self._tavily_api_key and self._search_fn is None:
            await self._limiter.acquire()
        try:
            if self._search_fn is not None:
                rows = await asyncio.wait_for(
                    self._search_fn(query, max_results),
                    timeout=self._timeout_s,
                )
            elif self._tavily_api_key:
                try:
                    rows = await _tavily_search(
                        query,
                        max_results,
                        api_key=self._tavily_api_key,
                        timeout_s=self._timeout_s,
                    )
                except Exception:
                    rows = await asyncio.wait_for(
                        _duckduckgo_search(query, max_results),
                        timeout=self._timeout_s,
                    )
            else:
                rows = await asyncio.wait_for(
                    _duckduckgo_search(query, max_results),
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
