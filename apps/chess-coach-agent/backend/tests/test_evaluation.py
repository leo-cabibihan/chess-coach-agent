from pathlib import Path

from chess_coach_agent.evaluation import run_eval


def test_evaluation_runner_executes_dataset():
    result = run_eval(Path("data/eval/critical_moments.jsonl"))
    assert result["total"] >= 10
    assert 0 <= result["accuracy"] <= 1
