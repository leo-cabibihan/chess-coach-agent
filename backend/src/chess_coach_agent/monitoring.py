from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


LOG_PATH = Path(__file__).resolve().parents[2] / "data" / "logs" / "events.jsonl"


def log_event(event_type: str, payload: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = {
            "timestamp": datetime.now(UTC).isoformat(),
        "event_type": event_type,
        **payload,
    }
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, default=str) + "\n")
