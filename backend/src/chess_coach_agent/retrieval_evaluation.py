from __future__ import annotations

import argparse
import json
from pathlib import Path

from .knowledge import retrieve_notes


def run_retrieval_eval(dataset: Path) -> dict:
    rows = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    results: dict[str, dict] = {}
    for strategy in ("title", "bm25"):
        reciprocal_ranks: list[float] = []
        hits = 0
        details = []
        for row in rows:
            titles = [note.title for note in retrieve_notes(row["query"], top_k=3, strategy=strategy)]
            rank = titles.index(row["expected_title"]) + 1 if row["expected_title"] in titles else 0
            hits += int(rank > 0)
            reciprocal_ranks.append(1 / rank if rank else 0)
            details.append({"id": row["id"], "expected": row["expected_title"], "rank": rank, "actual": titles})
        results[strategy] = {
            "hit_rate_at_3": round(hits / max(1, len(rows)), 3),
            "mean_reciprocal_rank": round(sum(reciprocal_ranks) / max(1, len(rows)), 3),
            "details": details,
        }
    winner = max(results, key=lambda name: (results[name]["mean_reciprocal_rank"], results[name]["hit_rate_at_3"]))
    return {"dataset_size": len(rows), "winner": winner, "strategies": results}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path("data/eval/retrieval.jsonl"))
    args = parser.parse_args()
    print(json.dumps(run_retrieval_eval(args.dataset), indent=2))


if __name__ == "__main__":
    main()
