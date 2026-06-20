from fastapi.testclient import TestClient

from backend.app import app

client = TestClient(app)


def test_health_route():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_auth_invalid_credentials():
    response = client.post("/api/auth", json={"username": "bad", "password": "wrong"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_auth_valid_credentials():
    response = client.post("/api/auth", json={"username": "user", "password": "password"})
    assert response.status_code == 200
    assert response.json()["username"] == "user"
    assert "user_id" in response.json()


def test_get_board_valid_user():
    response = client.get("/api/board?user_id=1")
    assert response.status_code == 200
    board_state = response.json()
    assert "state" in board_state
    assert isinstance(board_state["state"], str)


def test_get_board_invalid_user():
    response = client.get("/api/board?user_id=999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Board not found"


def test_save_board_valid_user():
    import json
    new_state = {"columns": [{"id": "col-1", "title": "Todo", "cardIds": []}], "cards": {}}
    response = client.post(
        "/api/board?user_id=1",
        json={"state": json.dumps(new_state)}
    )
    assert response.status_code == 200
    assert response.json()["state"] == json.dumps(new_state)


def test_save_board_invalid_user():
    import json
    new_state = {"columns": [], "cards": {}}
    response = client.post(
        "/api/board?user_id=999",
        json={"state": json.dumps(new_state)}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Board not found"
