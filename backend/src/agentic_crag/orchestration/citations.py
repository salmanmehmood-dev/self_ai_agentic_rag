"""Post-process orphan citation markers (E07)."""

from __future__ import annotations

import re

_CITE_RE = re.compile(r"\[(\d+)\]")


def strip_orphan_citations(text: str, max_index: int) -> str:
    """Remove [n] markers where n is outside 1..max_index."""

    def _keep(match: re.Match[str]) -> str:
        n = int(match.group(1))
        if max_index >= 1 and 1 <= n <= max_index:
            return match.group(0)
        return ""

    return _CITE_RE.sub(_keep, text)
