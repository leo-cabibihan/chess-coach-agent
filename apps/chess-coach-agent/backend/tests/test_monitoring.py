from pathlib import Path

from fastapi.testclient import TestClient

from chess_coach_agent import monitoring
from chess_coach_agent.api import app


def test_feedback_is_visible_in_dashboard_and_exportable(tmp_path: Path, monkeypatch):
    log_path = tmp_path / "events.jsonl"
    monkeypatch.setattr(monitoring, "LOG_PATH", log_path)
    client = TestClient(app)
    response = client.post(
        "/api/feedback",
        json={
            "moment_id": "game-12",
            "game_id": "game",
            "rating": "helpful",
            "theme": "loose_piece",
            "fen": "8/8/8/8/8/8/8/K6k w - - 0 1",
            "comment": "Correctly identified the hanging rook.",
        },
    )
    assert response.status_code == 200
    summary = client.get("/api/monitoring").json()
    assert summary["feedback_count"] == 1
    assert summary["helpful_rate"] == 1.0

    output = tmp_path / "feedback_candidates.jsonl"
    assert monitoring.export_feedback_candidates(output) == 1
    assert '"review_status": "candidate"' in output.read_text(encoding="utf-8")
