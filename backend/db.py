from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Optional

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "pm.db"
DB_PATH = Path(os.environ.get("PM_DB_PATH", str(DEFAULT_DB_PATH))).expanduser()
DEFAULT_USERNAME = "user"
DEFAULT_PASSWORD_HASH = hashlib.sha256("password".encode()).hexdigest()
DEFAULT_BOARD_NAME = "Default Board"
DEFAULT_BOARD_STATE_OBJECT = {
    "columns": [
        {"id": "col-backlog", "title": "Backlog", "cardIds": ["card-1", "card-2"]},
        {"id": "col-discovery", "title": "Discovery", "cardIds": ["card-3"]},
        {
            "id": "col-progress",
            "title": "In Progress",
            "cardIds": ["card-4", "card-5"],
        },
        {"id": "col-review", "title": "Review", "cardIds": ["card-6"]},
        {"id": "col-done", "title": "Done", "cardIds": ["card-7", "card-8"]},
    ],
    "cards": {
        "card-1": {
            "id": "card-1",
            "title": "Align roadmap themes",
            "details": "Draft quarterly themes with impact statements and metrics.",
        },
        "card-2": {
            "id": "card-2",
            "title": "Gather customer signals",
            "details": "Review support tags, sales notes, and churn feedback.",
        },
        "card-3": {
            "id": "card-3",
            "title": "Prototype analytics view",
            "details": "Sketch initial dashboard layout and key drill-downs.",
        },
        "card-4": {
            "id": "card-4",
            "title": "Refine status language",
            "details": "Standardize column labels and tone across the board.",
        },
        "card-5": {
            "id": "card-5",
            "title": "Design card layout",
            "details": "Add hierarchy and spacing for scanning dense lists.",
        },
        "card-6": {
            "id": "card-6",
            "title": "QA micro-interactions",
            "details": "Verify hover, focus, and loading states.",
        },
        "card-7": {
            "id": "card-7",
            "title": "Ship marketing page",
            "details": "Final copy approved and asset pack delivered.",
        },
        "card-8": {
            "id": "card-8",
            "title": "Close onboarding sprint",
            "details": "Document release notes and share internally.",
        },
    },
}
DEFAULT_BOARD_STATE = json.dumps(DEFAULT_BOARD_STATE_OBJECT)

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  password TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS boards (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  name TEXT NOT NULL DEFAULT 'Default Board',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS board_state (
  board_id INTEGER PRIMARY KEY,
  state TEXT NOT NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE
);
"""


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(db_path: Optional[Path] = None) -> None:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    with get_connection(path) as connection:
        connection.executescript(SCHEMA)
        _seed_default_data(connection)


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def get_user_by_credentials(
    username: str, password: str, db_path: Optional[Path] = None
) -> Optional[sqlite3.Row]:
    with get_connection(db_path) as connection:
        return connection.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, _hash_password(password)),
        ).fetchone()


def get_board_state_by_user_id(
    user_id: int, db_path: Optional[Path] = None,
) -> Optional[str]:
    with get_connection(db_path) as connection:
        row = connection.execute(
            "SELECT bs.state FROM board_state bs "
            "JOIN boards b ON bs.board_id = b.id "
            "WHERE b.user_id = ?",
            (user_id,),
        ).fetchone()
        return row["state"] if row else None


def update_board_state_by_user_id(
    user_id: int, state: str | dict, db_path: Optional[Path] = None,
) -> None:
    if not isinstance(state, str):
        state = json.dumps(state)

    with get_connection(db_path) as connection:
        row = connection.execute(
            "SELECT b.id FROM boards b WHERE b.user_id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Board not found for user")

        connection.execute(
            "UPDATE board_state SET state = ?, updated_at = CURRENT_TIMESTAMP WHERE board_id = ?",
            (state, row["id"]),
        )
        connection.commit()


def _maybe_upgrade_board_state(state: str) -> str | None:
    try:
        parsed = json.loads(state)
    except json.JSONDecodeError:
        return DEFAULT_BOARD_STATE

    if not isinstance(parsed, dict):
        return DEFAULT_BOARD_STATE

    columns = parsed.get("columns")
    cards = parsed.get("cards")

    if not isinstance(columns, list):
        return DEFAULT_BOARD_STATE

    if cards is None:
        cards = {}
    if not isinstance(cards, dict):
        return DEFAULT_BOARD_STATE

    if len(columns) == 0 and len(cards) == 0:
        return DEFAULT_BOARD_STATE

    if len(columns) == 1:
        column = columns[0]
        if not isinstance(column, dict):
            return DEFAULT_BOARD_STATE

        title = str(column.get("title", "")).strip()
        normalized_title = title.lower()
        if normalized_title in {"to do", "todo"}:
            existing_ids = {str(column.get("id", "")).strip()} - {""}

            def unique_id(base: str) -> str:
                candidate = base
                suffix = 2
                while candidate in existing_ids:
                    candidate = f"{base}-{suffix}"
                    suffix += 1
                existing_ids.add(candidate)
                return candidate

            upgraded_columns = [
                {
                    "id": str(column.get("id") or unique_id("col-todo")),
                    "title": title or "To Do",
                    "cardIds": column.get("cardIds") if isinstance(column.get("cardIds"), list) else [],
                },
                {"id": unique_id("col-discovery"), "title": "Discovery", "cardIds": []},
                {"id": unique_id("col-progress"), "title": "In Progress", "cardIds": []},
                {"id": unique_id("col-review"), "title": "Review", "cardIds": []},
                {"id": unique_id("col-done"), "title": "Done", "cardIds": []},
            ]
            return json.dumps({"columns": upgraded_columns, "cards": cards})

    return None


def _seed_default_data(connection: sqlite3.Connection) -> None:
    cursor = connection.execute(
        "SELECT id FROM users WHERE username = ?",
        (DEFAULT_USERNAME,),
    )
    row = cursor.fetchone()
    if row:
        user_id = row["id"]
    else:
        user_id = connection.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (DEFAULT_USERNAME, DEFAULT_PASSWORD_HASH),
        ).lastrowid

    cursor = connection.execute(
        "SELECT id FROM boards WHERE user_id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    if row:
        board_id = row["id"]
    else:
        board_id = connection.execute(
            "INSERT INTO boards (user_id, name) VALUES (?, ?)",
            (user_id, DEFAULT_BOARD_NAME),
        ).lastrowid

    cursor = connection.execute(
        "SELECT board_id FROM board_state WHERE board_id = ?",
        (board_id,),
    )
    existing = cursor.fetchone()
    if existing is None:
        connection.execute(
            "INSERT INTO board_state (board_id, state) VALUES (?, ?)",
            (board_id, DEFAULT_BOARD_STATE),
        )
    else:
        state_row = connection.execute(
            "SELECT state FROM board_state WHERE board_id = ?",
            (board_id,),
        ).fetchone()
        if state_row:
            upgraded = _maybe_upgrade_board_state(state_row["state"])
            if upgraded is not None and upgraded != state_row["state"]:
                connection.execute(
                    "UPDATE board_state SET state = ?, updated_at = CURRENT_TIMESTAMP WHERE board_id = ?",
                    (upgraded, board_id),
                )

    connection.commit()
