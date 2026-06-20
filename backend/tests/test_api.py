from fastapi.testclient import TestClient

from chess_coach_agent.api import app


def test_health_and_sample_endpoints():
    client = TestClient(app)
    assert client.get("/api/health").json()["status"] == "ok"
    sample = client.get("/api/sample").json()
    assert "pgn" in sample
    assert sample["player"] == "kfctofu"


def test_analyze_endpoint_with_sample():
    client = TestClient(app)
    sample = client.get("/api/sample").json()
    response = client.post("/api/analyze", json={"pgn": sample["pgn"], "player": "kfctofu", "max_games": 1})
    assert response.status_code == 200
    payload = response.json()
    assert payload["analyses"][0]["moments"]
