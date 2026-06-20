import importlib
import json

from fastapi.testclient import TestClient


def test_ai_chat_applies_update_and_persists(tmp_path, monkeypatch):
    monkeypatch.setenv("PM_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    import backend.db as db_module
    import backend.app as app_module

    importlib.reload(db_module)
    importlib.reload(app_module)

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

    client = TestClient(app_module.app)
    response = client.post("/api/ai/chat", json={"userId": 1, "prompt": "Add a card"})
    assert response.status_code == 200

    payload = response.json()
    assert payload["applied"] is True
    assert payload["message"] == "Done."

    saved = client.get("/api/board?user_id=1").json()
    board = json.loads(saved["state"])
    assert "card-new" in board["cards"]
    backlog = next(column for column in board["columns"] if column["id"] == "col-backlog")
    assert "card-new" in backlog["cardIds"]


def test_ai_chat_rejects_non_json(tmp_path, monkeypatch):
    monkeypatch.setenv("PM_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    import backend.db as db_module
    import backend.app as app_module

    importlib.reload(db_module)
    importlib.reload(app_module)

    monkeypatch.setattr(app_module.ai_service, "call_ai_with_board_context", lambda **kwargs: "not json")

    client = TestClient(app_module.app)
    response = client.post("/api/ai/chat", json={"userId": 1, "prompt": "Hi"})
    assert response.status_code == 502
    assert response.json()["detail"] == "AI returned non-JSON response"

