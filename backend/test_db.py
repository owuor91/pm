from pathlib import Path

import json
import pytest

from backend.db import (
    DEFAULT_BOARD_STATE_OBJECT,
    DB_PATH,
    get_connection,
    init_db,
    update_board_state_by_user_id,
)


def test_init_db_creates_schema_and_default_user(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    from backend.db import _hash_password
    with get_connection(db_path) as conn:
        user = conn.execute("SELECT username, password FROM users WHERE username = ?", ("user",)).fetchone()
        assert user is not None
        assert user["username"] == "user"
        assert user["password"] == _hash_password("password")

        board = conn.execute("SELECT id FROM boards WHERE user_id = (SELECT id FROM users WHERE username = ?)", ("user",)).fetchone()
        assert board is not None

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
            "SELECT state FROM board_state WHERE board_id = (SELECT id FROM boards WHERE user_id = 1)"
        ).fetchone()
        assert board is not None
        assert json.loads(board["state"]) == new_state
