from __future__ import annotations

import argparse
import json
from collections import Counter
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


def read_events() -> list[dict[str, Any]]:
    if not LOG_PATH.exists():
        return []
    events = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def monitoring_summary() -> dict[str, Any]:
    events = read_events()
    event_counts = Counter(event.get("event_type", "unknown") for event in events)
    feedback = [event for event in events if event.get("event_type") == "moment_feedback"]
    helpful = sum(event.get("rating") == "helpful" for event in feedback)
    themes = Counter(event.get("theme") for event in feedback if event.get("theme"))
    return {
        "total_events": len(events),
        "event_counts": dict(event_counts),
        "feedback_count": len(feedback),
        "helpful_rate": round(helpful / len(feedback), 3) if feedback else None,
        "feedback_themes": dict(themes),
        "recent_events": list(reversed(events[-8:])),
    }


def export_feedback_candidates(output: Path) -> int:
    candidates = []
    for event in read_events():
        if event.get("event_type") != "moment_feedback" or not event.get("fen"):
            continue
        candidates.append(
            {
                "id": f"feedback-{event.get('moment_id', 'unknown')}",
                "fen": event["fen"],
                "expected_theme": event.get("theme", "unknown"),
                "rating": event.get("rating"),
                "reviewer_notes": event.get("comment", ""),
                "source": "monitoring_feedback",
                "review_status": "candidate",
            }
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(row) + "\n" for row in candidates), encoding="utf-8")
    return len(candidates)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--export-candidates", type=Path)
    args = parser.parse_args()
    if args.export_candidates:
        count = export_feedback_candidates(args.export_candidates)
        print(json.dumps({"exported": count, "path": str(args.export_candidates)}, indent=2))
    else:
        print(json.dumps(monitoring_summary(), indent=2))


if __name__ == "__main__":
    main()
