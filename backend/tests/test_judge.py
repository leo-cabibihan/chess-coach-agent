import asyncio
import json
from pathlib import Path

from chess_coach_agent.judge_evaluation import run_llm_judge


async def fake_judge(_system: str, prompt: str) -> tuple[str, bool]:
    expected = prompt.split("Expected theme: ", 1)[1].splitlines()[0]
    candidate = prompt.split("Candidate coaching output:\n", 1)[1]
    theme_score = 2 if expected in candidate else 0
    payload = {
        "theme_score": theme_score,
        "grounding_score": 2 if "Played move:" in candidate else 1,
        "coaching_score": 2 if "Drill:" in candidate else 1,
        "reason": "Structured judge fixture",
    }
    return json.dumps(payload), True


def test_llm_judge_pipeline_uses_ground_truth_and_selects_grounded_prompt():
    result = asyncio.run(
        run_llm_judge(
            Path("data/eval/critical_moments.jsonl"),
            variants=("concise", "grounded"),
            judge=fake_judge,
        )
    )
    assert result["dataset_size"] == 2
    assert result["winner"] == "grounded"
    assert result["variants"]["grounded"]["pass_rate"] == 1.0
