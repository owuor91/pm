import importlib
import json

from fastapi.testclient import TestClient


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("PM_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    import backend.db as db_module
    import backend.rate_limit as rate_limit_module
    import backend.app as app_module

    importlib.reload(db_module)
    importlib.reload(rate_limit_module)
    importlib.reload(app_module)

    client = TestClient(app_module.app)
    signup = client.post("/api/auth/signup", json={"username": "alice", "password": "secretpw"})
    board_id = client.get("/api/boards").json()[0]["id"]
    return app_module, client, board_id


def test_ai_chat_applies_update_and_persists(tmp_path, monkeypatch):
    app_module, client, board_id = _setup(tmp_path, monkeypatch)

    def fake_call(prompt: str, board_state: dict, conversation=None):
        return json.dumps(
            {
                "message": "Done.",
                "boardUpdate": {
                    "newCards": [
                        {
                            "id": "card-new",
                            "title": "Created by AI",
                            "details": "d",
                            "columnId": "col-backlog",
                        }
                    ]
                },
                "confidence": 0.9,
            }
        )

    monkeypatch.setattr(app_module.ai_service, "call_ai_with_board_context", fake_call)

    response = client.post("/api/ai/chat", json={"boardId": board_id, "prompt": "Add a card"})
    assert response.status_code == 200

    payload = response.json()
    assert payload["applied"] is True
    assert payload["message"] == "Done."

    saved = client.get(f"/api/boards/{board_id}/state").json()
    board = json.loads(saved["state"])
    assert "card-new" in board["cards"]
    backlog = next(column for column in board["columns"] if column["id"] == "col-backlog")
    assert "card-new" in backlog["cardIds"]

    activity = client.get(f"/api/boards/{board_id}/activity").json()
    assert any(entry["action"] == "ai_update" for entry in activity)


def test_ai_chat_rejects_non_json(tmp_path, monkeypatch):
    app_module, client, board_id = _setup(tmp_path, monkeypatch)

    monkeypatch.setattr(app_module.ai_service, "call_ai_with_board_context", lambda **kwargs: "not json")

    response = client.post("/api/ai/chat", json={"boardId": board_id, "prompt": "Hi"})
    assert response.status_code == 502
    assert response.json()["detail"] == "AI returned non-JSON response"


def test_ai_chat_requires_board_membership(tmp_path, monkeypatch):
    app_module, client, board_id = _setup(tmp_path, monkeypatch)

    other_client = TestClient(app_module.app)
    other_client.post("/api/auth/signup", json={"username": "bob", "password": "secretpw"})

    response = other_client.post("/api/ai/chat", json={"boardId": board_id, "prompt": "Hi"})
    assert response.status_code == 404
