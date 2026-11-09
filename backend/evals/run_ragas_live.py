#!/usr/bin/env python3
"""Optional live Ragas scoring (requires API keys; not run in CI).

Invoked manually: `uv run python evals/run_ragas_live.py`. No other live Ragas
entry exists. Reads/prints metrics_snapshot.json; does not call APIs yet.
User instruction: "Implement the plan as specified, it is attached for your reference."
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_SNAPSHOT = Path(__file__).with_name("metrics_snapshot.json")


def main() -> int:
    print(
        "Live Ragas is optional for demos. CI uses offline golden_dataset.json.\n"
        "To wire Ragas: install ragas + langchain-google-genai, score a held-out\n"
        "set against live Gemini, then overwrite metrics_snapshot.json.\n"
        f"Current snapshot: {_SNAPSHOT} (source=golden_offline)."
    )
    if _SNAPSHOT.is_file():
        payload = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
        print(f"metrics={len(payload.get('metrics', []))} source={payload.get('source')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
