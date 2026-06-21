import json
from pathlib import Path

from fastapi.testclient import TestClient


def test_health_route():
    from backend.app import app
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_auth_invalid_credentials(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PM_DB_PATH", str(tmp_path / "test.db"))
    import importlib
    import backend.db as db_module
    import backend.app as app_module
    importlib.reload(db_module)
    importlib.reload(app_module)

    client = TestClient(app_module.app)
    response = client.post("/api/auth", json={"username": "bad", "password": "wrong"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_auth_valid_credentials(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PM_DB_PATH", str(tmp_path / "test.db"))
    import importlib
    import backend.db as db_module
    import backend.app as app_module
    importlib.reload(db_module)
    importlib.reload(app_module)

    client = TestClient(app_module.app)
    response = client.post("/api/auth", json={"username": "user", "password": "password"})
    assert response.status_code == 200
    assert response.json()["username"] == "user"
    assert "user_id" in response.json()


def test_get_board_valid_user(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PM_DB_PATH", str(tmp_path / "test.db"))
    import importlib
    import backend.db as db_module
    import backend.app as app_module
    importlib.reload(db_module)
    importlib.reload(app_module)

    client = TestClient(app_module.app)
    # First authenticate to ensure user exists
    auth_resp = client.post("/api/auth", json={"username": "user", "password": "password"})
    user_id = auth_resp.json()["user_id"]

    response = client.get(f"/api/board?user_id={user_id}")
    assert response.status_code == 200
    board_state = response.json()
    assert "state" in board_state
    assert isinstance(board_state["state"], str)


def test_get_board_invalid_user(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PM_DB_PATH", str(tmp_path / "test.db"))
    import importlib
    import backend.db as db_module
    import backend.app as app_module
    importlib.reload(db_module)
    importlib.reload(app_module)

    client = TestClient(app_module.app)
    response = client.get("/api/board?user_id=999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Board not found"


def test_save_board_valid_user(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PM_DB_PATH", str(tmp_path / "test.db"))
    import importlib
    import backend.db as db_module
    import backend.app as app_module
    importlib.reload(db_module)
    importlib.reload(app_module)

    client = TestClient(app_module.app)
    auth_resp = client.post("/api/auth", json={"username": "user", "password": "password"})
    user_id = auth_resp.json()["user_id"]

    new_state = {"columns": [{"id": "col-1", "title": "Todo", "cardIds": []}], "cards": {}}
    response = client.post(
        f"/api/board?user_id={user_id}",
        json={"state": json.dumps(new_state)}
    )
    assert response.status_code == 200
    assert response.json()["state"] == json.dumps(new_state)


def test_save_board_invalid_user(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PM_DB_PATH", str(tmp_path / "test.db"))
    import importlib
    import backend.db as db_module
    import backend.app as app_module
    importlib.reload(db_module)
    importlib.reload(app_module)

    client = TestClient(app_module.app)
    new_state = {"columns": [], "cards": {}}
    response = client.post(
        "/api/board?user_id=999",
        json={"state": json.dumps(new_state)}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Board not found"
