from fastapi.testclient import TestClient
from sqlalchemy import select

from chess_coach_agent.api import app
from chess_coach_agent.db import session_scope
from chess_coach_agent.db_models import ReviewScheduleRow
from chess_coach_agent.importers import preview_pgn_games


def test_persistent_training_and_progress_flow(monkeypatch):
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
        analyzed_moment = analysis.json()["analyses"][0]["moments"][0]

        exact_training = client.post(
            "/api/training/sessions",
            json={
                "platform": "chess.com",
                "username": "kfctofu",
                "theme": analyzed_moment["theme"],
                "moment_id": analyzed_moment["id"],
                "position_count": 1,
            },
        )
        assert exact_training.status_code == 200
        assert len(exact_training.json()["positions"]) == 1
        assert exact_training.json()["positions"][0]["fen"] == analyzed_moment["fen_before"]

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


def test_full_history_sync_deduplicates_analyzed_games(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with TestClient(app) as client:
        sample = client.get("/api/sample").json()
        one_game_pgn = preview_pgn_games(
            sample["pgn"], "kfctofu", "chess.com", max_games=1
        )[0].pgn

        async def sample_history(
            _platform: str, _username: str, _max_games: int
        ) -> str:
            return one_game_pgn

        monkeypatch.setattr(
            "chess_coach_agent.adaptive_api.fetch_platform_pgn", sample_history
        )
        analyzed = client.post(
            "/api/analyze",
            json={
                "pgn": one_game_pgn,
                "player": "kfctofu",
                "platform": "chess.com",
                "max_games": 1,
            },
        )
        assert analyzed.status_code == 200

        started = client.post(
            "/api/games/sync",
            json={"platform": "chess.com", "username": "kfctofu", "max_games": 5000},
        )
        assert started.status_code == 200
        job = client.get(f"/api/games/sync/{started.json()['id']}")
        assert job.status_code == 200
        payload = job.json()
        assert payload["status"] == "complete"
        assert payload["total_games"] == 1
        assert payload["analyzed_games"] == 0
        assert payload["skipped_games"] == 1
