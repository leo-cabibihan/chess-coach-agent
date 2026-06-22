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


def test_chat_without_model_key_returns_structured_fallback(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    client = TestClient(app)
    response = client.post("/api/chat", json={"question": "How do I find forcing moves?"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["used_llm"] is False
    assert payload["coaching"]["drill"]
    assert 0 <= payload["coaching"]["confidence"] <= 1
    assert len(payload["tools_used"]) >= 2
    assert payload["trace_id"]
