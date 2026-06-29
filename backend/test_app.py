import json
from pathlib import Path

from fastapi.testclient import TestClient


def _fresh_client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("PM_DB_PATH", str(tmp_path / "test.db"))
    import importlib
    import backend.db as db_module
    import backend.rate_limit as rate_limit_module
    import backend.app as app_module
    importlib.reload(db_module)
    importlib.reload(rate_limit_module)
    importlib.reload(app_module)
    return TestClient(app_module.app)


def _signup(client: TestClient, username: str = "alice", password: str = "secretpw"):
    response = client.post("/api/auth/signup", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def test_health_route():
    from backend.app import app
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_signup_creates_account_and_session(tmp_path, monkeypatch):
    client = _fresh_client(tmp_path, monkeypatch)
    body = _signup(client)
    assert body["username"] == "alice"
    assert "session_token" in client.cookies

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["username"] == "alice"


def test_signup_duplicate_username_rejected(tmp_path, monkeypatch):
    client = _fresh_client(tmp_path, monkeypatch)
    _signup(client)
    response = client.post("/api/auth/signup", json={"username": "alice", "password": "otherpassword"})
    assert response.status_code == 400


def test_signup_rejects_short_password(tmp_path, monkeypatch):
    client = _fresh_client(tmp_path, monkeypatch)
    response = client.post("/api/auth/signup", json={"username": "newperson", "password": "short1"})
    assert response.status_code == 400
    assert "8 characters" in response.json()["detail"]


def test_login_invalid_credentials(tmp_path, monkeypatch):
    client = _fresh_client(tmp_path, monkeypatch)
    response = client.post("/api/auth/login", json={"username": "bad", "password": "wrong"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_login_valid_credentials_sets_cookie(tmp_path, monkeypatch):
    client = _fresh_client(tmp_path, monkeypatch)
    response = client.post("/api/auth/login", json={"username": "user", "password": "password"})
    assert response.status_code == 200
    assert response.json()["username"] == "user"
    assert "session_token" in client.cookies


def test_logout_clears_session(tmp_path, monkeypatch):
    client = _fresh_client(tmp_path, monkeypatch)
    _signup(client)
    assert client.get("/api/auth/me").status_code == 200

    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_me_without_session_is_401(tmp_path, monkeypatch):
    client = _fresh_client(tmp_path, monkeypatch)
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_signup_provisions_starter_board(tmp_path, monkeypatch):
    client = _fresh_client(tmp_path, monkeypatch)
    _signup(client)

    response = client.get("/api/boards")
    assert response.status_code == 200
    boards = response.json()
    assert len(boards) == 1
    assert boards[0]["name"] == "My Board"
    assert boards[0]["role"] == "owner"


def test_create_rename_delete_board(tmp_path, monkeypatch):
    client = _fresh_client(tmp_path, monkeypatch)
    _signup(client)

    create_resp = client.post("/api/boards", json={"name": "Roadmap"})
    assert create_resp.status_code == 200
    board_id = create_resp.json()["id"]

    boards = client.get("/api/boards").json()
    assert len(boards) == 2

    rename_resp = client.patch(f"/api/boards/{board_id}", json={"name": "Renamed"})
    assert rename_resp.status_code == 200
    boards = client.get("/api/boards").json()
    assert any(b["id"] == board_id and b["name"] == "Renamed" for b in boards)

    delete_resp = client.delete(f"/api/boards/{board_id}")
    assert delete_resp.status_code == 200
    boards = client.get("/api/boards").json()
    assert len(boards) == 1


def test_board_routes_require_membership(tmp_path, monkeypatch):
    client = _fresh_client(tmp_path, monkeypatch)
    _signup(client, "alice")
    own_boards = client.get("/api/boards").json()
    own_board_id = own_boards[0]["id"]

    other_client = _fresh_client(tmp_path, monkeypatch)
    _signup(other_client, "bob")

    response = other_client.get(f"/api/boards/{own_board_id}/state")
    assert response.status_code == 404


def test_get_and_save_board_state(tmp_path, monkeypatch):
    client = _fresh_client(tmp_path, monkeypatch)
    _signup(client)
    board_id = client.get("/api/boards").json()[0]["id"]

    state_resp = client.get(f"/api/boards/{board_id}/state")
    assert state_resp.status_code == 200
    assert "state" in state_resp.json()

    new_state = {"columns": [{"id": "col-1", "title": "Todo", "cardIds": []}], "cards": {}}
    save_resp = client.post(
        f"/api/boards/{board_id}/state",
        json={"state": json.dumps(new_state)},
    )
    assert save_resp.status_code == 200
    assert json.loads(save_resp.json()["state"]) == new_state

    activity = client.get(f"/api/boards/{board_id}/activity").json()
    assert any(entry["action"] == "board_state_saved" for entry in activity)


def test_save_board_state_unknown_board(tmp_path, monkeypatch):
    client = _fresh_client(tmp_path, monkeypatch)
    _signup(client)
    response = client.post(
        "/api/boards/999/state",
        json={"state": json.dumps({"columns": [], "cards": {}})},
    )
    assert response.status_code == 404


def test_share_board_with_member_and_remove(tmp_path, monkeypatch):
    owner_client = _fresh_client(tmp_path, monkeypatch)
    _signup(owner_client, "alice")
    board_id = owner_client.get("/api/boards").json()[0]["id"]

    bob_client = _fresh_client(tmp_path, monkeypatch)
    _signup(bob_client, "bob")

    add_resp = owner_client.post(
        f"/api/boards/{board_id}/members", json={"username": "bob", "role": "editor"}
    )
    assert add_resp.status_code == 200
    bob_user_id = add_resp.json()["user_id"]

    bob_state_resp = bob_client.get(f"/api/boards/{board_id}/state")
    assert bob_state_resp.status_code == 200

    delete_attempt = bob_client.delete(f"/api/boards/{board_id}")
    assert delete_attempt.status_code == 403

    remove_resp = owner_client.delete(f"/api/boards/{board_id}/members/{bob_user_id}")
    assert remove_resp.status_code == 200

    bob_state_after = bob_client.get(f"/api/boards/{board_id}/state")
    assert bob_state_after.status_code == 404


def test_non_owner_cannot_add_members(tmp_path, monkeypatch):
    owner_client = _fresh_client(tmp_path, monkeypatch)
    _signup(owner_client, "alice")
    board_id = owner_client.get("/api/boards").json()[0]["id"]

    bob_client = _fresh_client(tmp_path, monkeypatch)
    _signup(bob_client, "bob")
    owner_client.post(f"/api/boards/{board_id}/members", json={"username": "bob", "role": "editor"})

    carol_client = _fresh_client(tmp_path, monkeypatch)
    _signup(carol_client, "carol")

    response = bob_client.post(
        f"/api/boards/{board_id}/members", json={"username": "carol", "role": "editor"}
    )
    assert response.status_code == 403


def test_cannot_remove_last_owner(tmp_path, monkeypatch):
    owner_client = _fresh_client(tmp_path, monkeypatch)
    _signup(owner_client, "alice")
    board_id = owner_client.get("/api/boards").json()[0]["id"]
    owner_user_id = owner_client.get("/api/auth/me").json()["user_id"]

    response = owner_client.delete(f"/api/boards/{board_id}/members/{owner_user_id}")
    assert response.status_code == 400


def test_editor_can_leave_board_but_not_remove_others(tmp_path, monkeypatch):
    owner_client = _fresh_client(tmp_path, monkeypatch)
    _signup(owner_client, "alice")
    board_id = owner_client.get("/api/boards").json()[0]["id"]

    bob_client = _fresh_client(tmp_path, monkeypatch)
    _signup(bob_client, "bob")
    carol_client = _fresh_client(tmp_path, monkeypatch)
    _signup(carol_client, "carol")

    owner_client.post(f"/api/boards/{board_id}/members", json={"username": "bob", "role": "editor"})
    add_carol = owner_client.post(
        f"/api/boards/{board_id}/members", json={"username": "carol", "role": "editor"}
    )
    carol_user_id = add_carol.json()["user_id"]

    forbidden = bob_client.delete(f"/api/boards/{board_id}/members/{carol_user_id}")
    assert forbidden.status_code == 403

    bob_user_id = bob_client.get("/api/auth/me").json()["user_id"]
    left = bob_client.delete(f"/api/boards/{board_id}/members/{bob_user_id}")
    assert left.status_code == 200

    members = owner_client.get(f"/api/boards/{board_id}/members").json()
    assert {m["username"] for m in members} == {"alice", "carol"}


def test_cors_does_not_reflect_arbitrary_origins(tmp_path, monkeypatch):
    client = _fresh_client(tmp_path, monkeypatch)
    response = client.get("/health", headers={"Origin": "http://evil.example"})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_cors_allows_configured_dev_origin(tmp_path, monkeypatch):
    client = _fresh_client(tmp_path, monkeypatch)
    response = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_change_password_succeeds_and_old_password_stops_working(tmp_path, monkeypatch):
    monkeypatch.setenv("PM_DB_PATH", str(tmp_path / "test.db"))
    import importlib
    import backend.db as db_module
    import backend.rate_limit as rate_limit_module
    import backend.app as app_module
    importlib.reload(db_module)
    importlib.reload(rate_limit_module)
    importlib.reload(app_module)
    from fastapi.testclient import TestClient

    client = TestClient(app_module.app)
    _signup(client)

    response = client.post(
        "/api/auth/change-password",
        json={"currentPassword": "secretpw", "newPassword": "newsecretpw"},
    )
    assert response.status_code == 200

    new_client = TestClient(app_module.app)
    old_login = new_client.post("/api/auth/login", json={"username": "alice", "password": "secretpw"})
    assert old_login.status_code == 401

    new_login = new_client.post("/api/auth/login", json={"username": "alice", "password": "newsecretpw"})
    assert new_login.status_code == 200


def test_change_password_rejects_wrong_current_password(tmp_path, monkeypatch):
    client = _fresh_client(tmp_path, monkeypatch)
    _signup(client)

    response = client.post(
        "/api/auth/change-password",
        json={"currentPassword": "wrongpassword", "newPassword": "newsecretpw"},
    )
    assert response.status_code == 400


def test_change_password_rejects_short_new_password(tmp_path, monkeypatch):
    client = _fresh_client(tmp_path, monkeypatch)
    _signup(client)

    response = client.post(
        "/api/auth/change-password",
        json={"currentPassword": "secretpw", "newPassword": "short1"},
    )
    assert response.status_code == 400


def test_change_password_invalidates_other_sessions(tmp_path, monkeypatch):
    monkeypatch.setenv("PM_DB_PATH", str(tmp_path / "test.db"))
    import importlib
    import backend.db as db_module
    import backend.rate_limit as rate_limit_module
    import backend.app as app_module
    importlib.reload(db_module)
    importlib.reload(rate_limit_module)
    importlib.reload(app_module)
    from fastapi.testclient import TestClient

    client_a = TestClient(app_module.app)
    _signup(client_a)

    client_b = TestClient(app_module.app)
    client_b.post("/api/auth/login", json={"username": "alice", "password": "secretpw"})
    assert client_b.get("/api/auth/me").status_code == 200

    client_a.post(
        "/api/auth/change-password",
        json={"currentPassword": "secretpw", "newPassword": "newsecretpw"},
    )

    assert client_b.get("/api/auth/me").status_code == 401
    assert client_a.get("/api/auth/me").status_code == 200


def test_login_locks_out_after_repeated_failures(tmp_path, monkeypatch):
    from backend import rate_limit

    client = _fresh_client(tmp_path, monkeypatch)
    _signup(client, "alice")

    for _ in range(rate_limit.MAX_FAILED_ATTEMPTS):
        response = client.post("/api/auth/login", json={"username": "alice", "password": "wrong"})
        assert response.status_code == 401

    locked_response = client.post("/api/auth/login", json={"username": "alice", "password": "secretpw"})
    assert locked_response.status_code == 429


def test_login_lockout_does_not_affect_other_usernames(tmp_path, monkeypatch):
    from backend import rate_limit

    client = _fresh_client(tmp_path, monkeypatch)
    _signup(client, "alice")
    _signup(client, "bob")

    for _ in range(rate_limit.MAX_FAILED_ATTEMPTS):
        client.post("/api/auth/login", json={"username": "alice", "password": "wrong"})

    response = client.post("/api/auth/login", json={"username": "bob", "password": "secretpw"})
    assert response.status_code == 200


def test_successful_login_resets_failure_count(tmp_path, monkeypatch):
    from backend import rate_limit

    client = _fresh_client(tmp_path, monkeypatch)
    _signup(client, "alice")

    for _ in range(rate_limit.MAX_FAILED_ATTEMPTS - 1):
        client.post("/api/auth/login", json={"username": "alice", "password": "wrong"})

    success = client.post("/api/auth/login", json={"username": "alice", "password": "secretpw"})
    assert success.status_code == 200

    # Failure count should have reset, so one more wrong attempt should not lock the account out.
    again = client.post("/api/auth/login", json={"username": "alice", "password": "wrong"})
    assert again.status_code == 401
    still_works = client.post("/api/auth/login", json={"username": "alice", "password": "secretpw"})
    assert still_works.status_code == 200
