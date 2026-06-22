from fastapi.testclient import TestClient
from sqlalchemy import select

from chess_coach_agent.api import app
from chess_coach_agent.db import session_scope
from chess_coach_agent.db_models import ReviewScheduleRow


def test_persistent_coach_training_and_progress_flow(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with TestClient(app) as client:
        sample = client.get("/api/sample").json()
        analysis = client.post(
            "/api/analyze",
            json={
                "pgn": sample["pgn"],
                "player": "kfctofu",
                "platform": "chess.com",
                "max_games": 1,
            },
        )
        assert analysis.status_code == 200

        coach = client.post(
            "/api/coach/sessions",
            json={"platform": "chess.com", "username": "kfctofu"},
        )
        assert coach.status_code == 200
        coach_id = coach.json()["id"]

        turn = client.post(
            f"/api/coach/sessions/{coach_id}/messages",
            json={"content": "Give me a practice quiz from my games"},
        )
        assert turn.status_code == 200
        message_id = turn.json()["message_id"]
        stream = client.get(
            f"/api/coach/sessions/{coach_id}/stream",
            params={"message_id": message_id},
        )
        assert stream.status_code == 200
        assert "event: panel_ready" in stream.text
        assert "event: complete" in stream.text
        resumed = client.get(
            f"/api/coach/sessions/{coach_id}/stream",
            params={"message_id": message_id},
            headers={"Last-Event-ID": "1"},
        )
        assert "id: 1\n" not in resumed.text
        assert "event: complete" in resumed.text

        training = client.post(
            "/api/training/sessions",
            json={"platform": "chess.com", "username": "kfctofu", "position_count": 3},
        )
        assert training.status_code == 200
        payload = training.json()
        assert payload["positions"]
        position = payload["positions"][0]
        move = position["choices"][0] if position["choices"] else "e2e4"
        attempt = client.post(
            f"/api/training/sessions/{payload['id']}/attempts",
            json={"position_id": position["id"], "move": move, "elapsed_ms": 1200},
        )
        assert attempt.status_code == 200
        assert attempt.json()["legal"] is True
        with session_scope() as session:
            schedule = session.scalar(
                select(ReviewScheduleRow).where(
                    ReviewScheduleRow.position_id == position["id"]
                )
            )
            assert schedule is not None
            assert schedule.interval_days == 7

        hinted = client.post(
            f"/api/training/sessions/{payload['id']}/attempts",
            json={
                "position_id": position["id"],
                "move": move,
                "hints_used": 1,
                "elapsed_ms": 900,
            },
        )
        assert hinted.status_code == 200
        with session_scope() as session:
            schedule = session.scalar(
                select(ReviewScheduleRow).where(
                    ReviewScheduleRow.position_id == position["id"]
                )
            )
            assert schedule is not None
            assert schedule.interval_days == 3

        progress = client.get("/api/progress/chess.com/kfctofu")
        assert progress.status_code == 200
        assert progress.json()["total_games"] >= 1
        assert progress.json()["recent_attempts"] >= 2
