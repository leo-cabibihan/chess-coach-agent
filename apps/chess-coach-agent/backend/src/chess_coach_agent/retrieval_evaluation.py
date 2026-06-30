from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from .knowledge import retrieve_notes


def run_retrieval_eval(dataset: Path) -> dict:
    rows = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    results: dict[str, dict] = {}
    for strategy in ("title", "bm25", "vector", "hybrid"):
        reciprocal_ranks: list[float] = []
        latencies: list[float] = []
        hits = 0
        source_hits = 0
        details = []
        for row in rows:
            started = time.perf_counter()
            notes = retrieve_notes(row["query"], top_k=3, strategy=strategy)
            latencies.append((time.perf_counter() - started) * 1000)
            titles = [note.title for note in notes]
            rank = titles.index(row["expected_title"]) + 1 if row["expected_title"] in titles else 0
            hits += int(rank > 0)
            expected_source = row.get("expected_source")
            source_correct = not expected_source or any(
                note.title == row["expected_title"] and note.source == expected_source for note in notes
            )
            source_hits += int(source_correct)
            reciprocal_ranks.append(1 / rank if rank else 0)
            details.append(
                {
                    "id": row["id"],
                    "expected": row["expected_title"],
                    "rank": rank,
                    "actual": titles,
                    "source_correct": source_correct,
                }
            )
        results[strategy] = {
            "hit_rate_at_3": round(hits / max(1, len(rows)), 3),
            "mean_reciprocal_rank": round(sum(reciprocal_ranks) / max(1, len(rows)), 3),
            "source_correctness": round(source_hits / max(1, len(rows)), 3),
            "median_latency_ms": round(statistics.median(latencies), 3),
            "details": details,
        }
    bm25, hybrid = results["bm25"], results["hybrid"]
    hybrid_qualified = (
        hybrid["hit_rate_at_3"] >= bm25["hit_rate_at_3"]
        and hybrid["mean_reciprocal_rank"] >= bm25["mean_reciprocal_rank"]
        and hybrid["median_latency_ms"] < max(0.001, 2 * bm25["median_latency_ms"])
    )
    production_strategy = "hybrid" if hybrid_qualified else "bm25"
    return {
        "dataset_size": len(rows),
        "winner": production_strategy,
        "production_strategy": production_strategy,
        "hybrid_qualified": hybrid_qualified,
        "strategies": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path("data/eval/retrieval.jsonl"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_retrieval_eval(args.dataset)
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
