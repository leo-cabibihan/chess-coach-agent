from __future__ import annotations

import argparse
import json
from pathlib import Path

from .agent import ChessCoachAgent


def run_eval(dataset: Path) -> dict:
    agent = ChessCoachAgent()
    rows = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    passed = 0
    details = []
    for row in rows:
        response = agent.import_pgn_text(row["pgn"], player=row["player"], max_games=1)
        themes = {moment.theme for analysis in response.analyses for moment in analysis.moments}
        ok = row["expected_theme"] in themes
        passed += int(ok)
        details.append({"id": row["id"], "ok": ok, "expected": row["expected_theme"], "actual": sorted(themes)})
    return {"passed": passed, "total": len(rows), "accuracy": passed / max(1, len(rows)), "details": details}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path("data/eval/critical_moments.jsonl"))
    args = parser.parse_args()
    print(json.dumps(run_eval(args.dataset), indent=2))


if __name__ == "__main__":
    main()
