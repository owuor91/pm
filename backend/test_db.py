from pathlib import Path

import json
import pytest

import hashlib

from backend.db import (
    DEFAULT_BOARD_STATE_OBJECT,
    add_board_member,
    create_board,
    create_session,
    create_user,
    delete_board,
    delete_other_sessions,
    delete_session,
    get_board_member_role,
    get_board_state,
    get_connection,
    get_user_by_credentials,
    get_user_by_session_token,
    init_db,
    list_activity,
    list_board_members,
    list_boards_for_user,
    log_activity,
    remove_board_member,
    rename_board,
    update_board_state,
    update_board_state_by_user_id,
    update_user_password,
)


def test_init_db_creates_schema_and_default_user(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    from backend.db import _verify_password
    with get_connection(db_path) as conn:
        user = conn.execute("SELECT username, password FROM users WHERE username = ?", ("user",)).fetchone()
        assert user is not None
        assert user["username"] == "user"
        assert _verify_password("password", user["password"])
        assert not _verify_password("wrong", user["password"])

        user_row = conn.execute("SELECT id FROM users WHERE username = 'user'").fetchone()
        board = conn.execute("SELECT id FROM boards WHERE owner_id = ?", (user_row["id"],)).fetchone()
        assert board is not None

        member = conn.execute(
            "SELECT role FROM board_members WHERE board_id = ? AND user_id = ?",
            (board["id"], user_row["id"]),
        ).fetchone()
        assert member["role"] == "owner"

        board_state = conn.execute("SELECT state FROM board_state WHERE board_id = ?", (board["id"],)).fetchone()
        assert board_state is not None
        assert json.loads(board_state["state"]) == DEFAULT_BOARD_STATE_OBJECT


def test_update_board_state_by_user_id(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    new_state = {"columns": [{"id": "col-backlog", "title": "Backlog", "cardIds": []}], "cards": {}}
    update_board_state_by_user_id(1, new_state, db_path)

    with get_connection(db_path) as conn:
        board = conn.execute(
            "SELECT state FROM board_state WHERE board_id = (SELECT id FROM boards WHERE owner_id = 1)"
        ).fetchone()
        assert board is not None
        assert json.loads(board["state"]) == new_state


def test_create_user_duplicate_username_raises(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    create_user("alice", "secretpw", db_path)
    with pytest.raises(ValueError):
        create_user("alice", "otherpassword", db_path)


def test_create_user_rejects_short_password(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    with pytest.raises(ValueError, match="at least 8 characters"):
        create_user("alice", "short1", db_path)


def test_create_session_and_resolve_user(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    user_id = create_user("alice", "secretpw", db_path)

    token, _ = create_session(user_id, db_path)
    user = get_user_by_session_token(token, db_path)
    assert user is not None
    assert user["id"] == user_id

    delete_session(token, db_path)
    assert get_user_by_session_token(token, db_path) is None


def test_create_board_adds_owner_membership_and_state(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    user_id = create_user("alice", "secretpw", db_path)

    board_id = create_board(user_id, "Marketing", db_path=db_path)

    assert get_board_member_role(board_id, user_id, db_path) == "owner"
    boards = list_boards_for_user(user_id, db_path)
    assert any(b["id"] == board_id and b["name"] == "Marketing" for b in boards)
    assert json.loads(get_board_state(board_id, db_path)) == {
        "columns": [
            {"id": "col-backlog", "title": "Backlog", "cardIds": []},
            {"id": "col-discovery", "title": "Discovery", "cardIds": []},
            {"id": "col-progress", "title": "In Progress", "cardIds": []},
            {"id": "col-review", "title": "Review", "cardIds": []},
            {"id": "col-done", "title": "Done", "cardIds": []},
        ],
        "cards": {},
    }


def test_rename_and_delete_board(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    user_id = create_user("alice", "secretpw", db_path)
    board_id = create_board(user_id, "Original", db_path=db_path)

    rename_board(board_id, "Renamed", db_path)
    boards = list_boards_for_user(user_id, db_path)
    assert any(b["id"] == board_id and b["name"] == "Renamed" for b in boards)

    delete_board(board_id, db_path)
    assert get_board_state(board_id, db_path) is None
    assert get_board_member_role(board_id, user_id, db_path) is None


def test_add_and_remove_board_member(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    owner_id = create_user("alice", "secretpw", db_path)
    create_user("bob", "secretpw", db_path)
    board_id = create_board(owner_id, "Shared", db_path=db_path)

    member = add_board_member(board_id, "bob", "editor", db_path)
    assert member["role"] == "editor"

    members = list_board_members(board_id, db_path)
    usernames = {m["username"] for m in members}
    assert usernames == {"alice", "bob"}

    bob_id = member["user_id"]
    remove_board_member(board_id, bob_id, db_path)
    members_after = list_board_members(board_id, db_path)
    assert {m["username"] for m in members_after} == {"alice"}


def test_remove_last_owner_raises(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    owner_id = create_user("alice", "secretpw", db_path)
    board_id = create_board(owner_id, "Shared", db_path=db_path)

    with pytest.raises(ValueError):
        remove_board_member(board_id, owner_id, db_path)


def test_remove_one_of_two_owners_succeeds(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    owner_id = create_user("alice", "secretpw", db_path)
    create_user("bob", "secretpw", db_path)
    board_id = create_board(owner_id, "Shared", db_path=db_path)
    member = add_board_member(board_id, "bob", "owner", db_path)

    remove_board_member(board_id, member["user_id"], db_path)
    members_after = list_board_members(board_id, db_path)
    assert {m["username"] for m in members_after} == {"alice"}


def test_add_board_member_unknown_username_raises(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    owner_id = create_user("alice", "secretpw", db_path)
    board_id = create_board(owner_id, "Shared", db_path=db_path)

    with pytest.raises(ValueError):
        add_board_member(board_id, "ghost", "editor", db_path)


def test_add_board_member_duplicate_raises(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    owner_id = create_user("alice", "secretpw", db_path)
    create_user("bob", "secretpw", db_path)
    board_id = create_board(owner_id, "Shared", db_path=db_path)

    add_board_member(board_id, "bob", "editor", db_path)
    with pytest.raises(ValueError):
        add_board_member(board_id, "bob", "editor", db_path)


def test_update_board_state_unknown_board_raises(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    with pytest.raises(ValueError):
        update_board_state(999, {"columns": [], "cards": {}}, db_path)


def test_activity_log_records_and_lists_entries(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    user_id = create_user("alice", "secretpw", db_path)
    board_id = create_board(user_id, "Board", db_path=db_path)

    log_activity(board_id, user_id, "board_state_saved", db_path=db_path)
    log_activity(board_id, user_id, "ai_update", {"prompt": "add a card"}, db_path=db_path)

    entries = list_activity(board_id, db_path=db_path)
    assert len(entries) == 2
    assert entries[0]["action"] == "ai_update"
    assert entries[0]["details"] == {"prompt": "add a card"}
    assert entries[0]["username"] == "alice"
    assert entries[1]["action"] == "board_state_saved"


def test_passwords_are_salted_per_user(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    create_user("alice", "samepassword", db_path)
    create_user("bob", "samepassword", db_path)

    with get_connection(db_path) as conn:
        alice_hash = conn.execute("SELECT password FROM users WHERE username = 'alice'").fetchone()["password"]
        bob_hash = conn.execute("SELECT password FROM users WHERE username = 'bob'").fetchone()["password"]

    assert alice_hash != bob_hash
    assert get_user_by_credentials("alice", "samepassword", db_path) is not None
    assert get_user_by_credentials("alice", "wrongpassword", db_path) is None


def test_legacy_unsalted_password_hash_still_verifies(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    legacy_hash = hashlib.sha256("legacypass".encode()).hexdigest()
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            ("legacy", legacy_hash),
        )
        conn.commit()

    user = get_user_by_credentials("legacy", "legacypass", db_path)
    assert user is not None
    assert get_user_by_credentials("legacy", "wrongpass", db_path) is None


def test_update_user_password_requires_correct_current_password(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    user_id = create_user("alice", "secretpw", db_path)

    with pytest.raises(ValueError, match="incorrect"):
        update_user_password(user_id, "wrongpassword", "newsecretpw", db_path)

    update_user_password(user_id, "secretpw", "newsecretpw", db_path)
    assert get_user_by_credentials("alice", "newsecretpw", db_path) is not None
    assert get_user_by_credentials("alice", "secretpw", db_path) is None


def test_update_user_password_rejects_short_new_password(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    user_id = create_user("alice", "secretpw", db_path)

    with pytest.raises(ValueError, match="at least 8 characters"):
        update_user_password(user_id, "secretpw", "short1", db_path)


def test_delete_other_sessions_keeps_only_specified_token(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    user_id = create_user("alice", "secretpw", db_path)

    token_a, _ = create_session(user_id, db_path)
    token_b, _ = create_session(user_id, db_path)

    delete_other_sessions(user_id, token_a, db_path)

    assert get_user_by_session_token(token_a, db_path) is not None
    assert get_user_by_session_token(token_b, db_path) is None
