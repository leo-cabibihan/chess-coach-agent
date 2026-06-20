from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Score:
    name: str
    points: int
    max_points: int
    explanation: str


def exists(path: str) -> bool:
    return (ROOT / path).exists()


def read(path: str) -> str:
    file_path = ROOT / path
    if not file_path.exists():
        return ""
    return file_path.read_text(encoding="utf-8", errors="ignore")


def any_file(pattern: str) -> bool:
    return any(ROOT.glob(pattern))


def contains(path: str, *terms: str) -> bool:
    text = read(path).lower()
    return all(term.lower() in text for term in terms)


def score_problem() -> Score:
    ok = contains("README.md", "club players", "critical moments", "problem")
    return Score("Problem Description", 2 if ok else 1 if exists("README.md") else 0, 2, "README describes the chess improvement problem.")


def score_knowledge() -> Score:
    has_kb = any_file("backend/data/knowledge/*.md")
    has_test = exists("backend/tests/test_retrieval.py")
    return Score("Knowledge Base and Retrieval", 2 if has_kb and has_test else 1 if has_kb else 0, 2, "Chess principle KB and retrieval test are present.")


def score_agents() -> Score:
    agent = read("backend/src/chess_coach_agent/agent.py")
    llm = read("backend/src/chess_coach_agent/llm.py")
    tool_count = sum(agent.count(term) for term in ["import_pgn_text", "import_platform_games", "retrieve_chess_principles", "generate_trend_summary"])
    ok = "OPENROUTER_API_KEY" in llm and tool_count >= 4
    return Score("Agents and LLM", 3 if ok else 2 if tool_count >= 2 else 0, 3, f"Agent tool references: {tool_count}; OpenRouter path documented.")


def score_code_org() -> Score:
    ok = any_file("backend/src/chess_coach_agent/*.py") and any_file("frontend/src/**/*.tsx") and exists("backend/pyproject.toml")
    return Score("Code Organization", 2 if ok else 0, 2, "Backend package and React frontend are organized separately.")


def score_testing() -> Score:
    tests = list((ROOT / "backend/tests").glob("test_*.py"))
    return Score("Testing", 2 if len(tests) >= 5 and contains("README.md", "pytest") else 1 if tests else 0, 2, f"{len(tests)} backend tests are present.")


def score_evaluation() -> Score:
    ok = exists("backend/data/eval/critical_moments.jsonl") and exists("backend/src/chess_coach_agent/evaluation.py")
    documented = contains("README.md", "hand-crafted", "evaluation")
    return Score("Evaluation", 3 if ok and documented else 2 if ok else 0, 3, "Hand-crafted critical moment eval and runner are present.")


def score_eval_bonus() -> Score:
    handcrafted = exists("backend/data/eval/critical_moments.jsonl")
    manual = exists("docs/scorecard.md")
    return Score("Evaluation bonus points", (2 if handcrafted else 0) + (2 if manual else 0), 4, "Hand-crafted eval data and self-score are present.")


def score_monitoring() -> Score:
    logs = exists("backend/src/chess_coach_agent/monitoring.py")
    docs = contains("docs/monitoring.md", "jsonl", "events")
    return Score("Monitoring", 2 if logs and docs else 1 if logs else 0, 2, "JSONL monitoring and docs are present.")


def score_monitoring_bonus() -> Score:
    feedback_path = contains("docs/monitoring.md", "feedback", "evaluation data")
    log_to_eval = contains("docs/monitoring.md", "logs", "ground truth")
    return Score("Monitoring bonus points", (1 if feedback_path else 0) + (2 if log_to_eval else 0), 3, "Docs describe promoting logs/feedback into eval data.")


def score_reproducibility() -> Score:
    ok = contains("README.md", "quickstart", "uv sync", "npm install") and exists("backend/data/sample_games/kfctofu_sample.pgn")
    return Score("Reproducibility", 2 if ok else 1 if exists("README.md") else 0, 2, "README setup and sample PGN are present.")


def score_best_practices() -> Score:
    points = 0
    evidence = []
    if exists("Dockerfile.backend") or exists("Dockerfile.frontend"):
        points += 1
        evidence.append("Dockerfiles")
    if exists("docker-compose.yml"):
        points += 2
        evidence.append("docker-compose")
    if exists("Makefile"):
        points += 1
        evidence.append("Makefile")
    if exists("backend/pyproject.toml") and contains("README.md", "uv"):
        points += 1
        evidence.append("uv workflow")
    if any_file(".github/workflows/*.yml"):
        points += 2
        evidence.append("CI")
    return Score("Best Coding Practices", points, 7, ", ".join(evidence))


def score_additional_bonus() -> Score:
    points = 1 if any_file("frontend/src/**/*.tsx") else 0
    return Score("Additional Bonus Points", points, 3, "React UI is present; cloud deployment is optional.")


SCORERS: list[Callable[[], Score]] = [
    score_problem,
    score_knowledge,
    score_agents,
    score_code_org,
    score_testing,
    score_evaluation,
    score_eval_bonus,
    score_monitoring,
    score_monitoring_bonus,
    score_reproducibility,
    score_best_practices,
    score_additional_bonus,
]


def main() -> None:
    scores = [scorer() for scorer in SCORERS]
    total = sum(score.points for score in scores)
    max_total = sum(score.max_points for score in scores)
    print(f"Project score: {total}/{max_total}")
    print()
    for score in scores:
        print(f"- {score.name}: {score.points}/{score.max_points} — {score.explanation}")


if __name__ == "__main__":
    main()
