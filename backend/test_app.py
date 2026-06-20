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
