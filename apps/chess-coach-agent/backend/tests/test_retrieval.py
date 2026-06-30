from pathlib import Path

from chess_coach_agent.knowledge import retrieve_notes
from chess_coach_agent.retrieval_evaluation import run_retrieval_eval


def test_retrieval_finds_tactical_vision():
    notes = retrieve_notes("checks captures threats forcing tactic")
    titles = [note.title for note in notes]
    assert "Tactical Vision" in titles


def test_bm25_wins_retrieval_benchmark():
    result = run_retrieval_eval(Path("data/eval/retrieval.jsonl"))
    assert result["winner"] == "bm25"
    assert result["strategies"]["bm25"]["hit_rate_at_3"] >= 0.875
