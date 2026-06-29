from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "pm.db"
DB_PATH = Path(os.environ.get("PM_DB_PATH", str(DEFAULT_DB_PATH))).expanduser()
DEFAULT_USERNAME = "user"
DEFAULT_PASSWORD = "password"
DEFAULT_BOARD_NAME = "Default Board"
PBKDF2_ITERATIONS = 200_000
SESSION_TTL_SECONDS = 7 * 24 * 3600

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

EMPTY_BOARD_STATE_OBJECT = {
    "columns": [
        {"id": "col-backlog", "title": "Backlog", "cardIds": []},
        {"id": "col-discovery", "title": "Discovery", "cardIds": []},
        {"id": "col-progress", "title": "In Progress", "cardIds": []},
        {"id": "col-review", "title": "Review", "cardIds": []},
        {"id": "col-done", "title": "Done", "cardIds": []},
    ],
    "cards": {},
}
EMPTY_BOARD_STATE = json.dumps(EMPTY_BOARD_STATE_OBJECT)

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  password TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS boards (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_id INTEGER NOT NULL,
  name TEXT NOT NULL DEFAULT 'Default Board',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS board_members (
  board_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  role TEXT NOT NULL DEFAULT 'editor',
  added_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (board_id, user_id),
  FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS board_state (
  board_id INTEGER PRIMARY KEY,
  state TEXT NOT NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS activity_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  board_id INTEGER NOT NULL,
  user_id INTEGER,
  action TEXT NOT NULL,
  details TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
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
        _migrate_schema(connection)
        _seed_default_data(connection)


def _migrate_schema(connection: sqlite3.Connection) -> None:
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(boards)").fetchall()}
    if "user_id" in columns and "owner_id" not in columns:
        connection.execute("ALTER TABLE boards RENAME COLUMN user_id TO owner_id")

    boards_without_membership = connection.execute(
        "SELECT b.id, b.owner_id FROM boards b "
        "WHERE NOT EXISTS (SELECT 1 FROM board_members bm WHERE bm.board_id = b.id AND bm.user_id = b.owner_id)"
    ).fetchall()
    for board in boards_without_membership:
        connection.execute(
            "INSERT INTO board_members (board_id, user_id, role) VALUES (?, ?, 'owner')",
            (board["id"], board["owner_id"]),
        )
    connection.commit()


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    if "$" not in stored:
        # Legacy unsalted sha256 hash from before salted PBKDF2 was introduced.
        return hmac.compare_digest(hashlib.sha256(password.encode()).hexdigest(), stored)

    salt_hex, digest_hex = stored.split("$", 1)
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), PBKDF2_ITERATIONS)
    return hmac.compare_digest(candidate.hex(), digest_hex)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --- Users & auth -----------------------------------------------------------


MIN_PASSWORD_LENGTH = 8


def create_user(username: str, password: str, db_path: Optional[Path] = None) -> int:
    username = username.strip()
    if not username or not password:
        raise ValueError("Username and password are required")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")

    with get_connection(db_path) as connection:
        try:
            user_id = connection.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, _hash_password(password)),
            ).lastrowid
        except sqlite3.IntegrityError:
            raise ValueError("Username already taken")
        connection.commit()
        return user_id


def get_user_by_credentials(
    username: str, password: str, db_path: Optional[Path] = None
) -> Optional[sqlite3.Row]:
    with get_connection(db_path) as connection:
        user = connection.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        if user is None or not _verify_password(password, user["password"]):
            return None
        return user


def create_session(user_id: int, db_path: Optional[Path] = None) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    expires_at = _now() + timedelta(seconds=SESSION_TTL_SECONDS)
    with get_connection(db_path) as connection:
        connection.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires_at.isoformat()),
        )
        connection.commit()
    return token, expires_at


def get_user_by_session_token(
    token: str, db_path: Optional[Path] = None
) -> Optional[sqlite3.Row]:
    with get_connection(db_path) as connection:
        row = connection.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id "
            "WHERE s.token = ? AND s.expires_at > ?",
            (token, _now().isoformat()),
        ).fetchone()
        return row


def delete_session(token: str, db_path: Optional[Path] = None) -> None:
    with get_connection(db_path) as connection:
        connection.execute("DELETE FROM sessions WHERE token = ?", (token,))
        connection.commit()


def delete_other_sessions(user_id: int, keep_token: str, db_path: Optional[Path] = None) -> None:
    with get_connection(db_path) as connection:
        connection.execute(
            "DELETE FROM sessions WHERE user_id = ? AND token != ?",
            (user_id, keep_token),
        )
        connection.commit()


def update_user_password(
    user_id: int,
    current_password: str,
    new_password: str,
    db_path: Optional[Path] = None,
) -> None:
    if len(new_password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")

    with get_connection(db_path) as connection:
        user = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if user is None or not _verify_password(current_password, user["password"]):
            raise ValueError("Current password is incorrect")

        connection.execute(
            "UPDATE users SET password = ? WHERE id = ?",
            (_hash_password(new_password), user_id),
        )
        connection.commit()


# --- Boards & membership -----------------------------------------------------


def create_board(
    owner_id: int,
    name: str,
    state: str | dict = EMPTY_BOARD_STATE,
    db_path: Optional[Path] = None,
) -> int:
    if not isinstance(state, str):
        state = json.dumps(state)

    with get_connection(db_path) as connection:
        board_id = connection.execute(
            "INSERT INTO boards (owner_id, name) VALUES (?, ?)",
            (owner_id, name.strip() or "Untitled Board"),
        ).lastrowid
        connection.execute(
            "INSERT INTO board_members (board_id, user_id, role) VALUES (?, ?, 'owner')",
            (board_id, owner_id),
        )
        connection.execute(
            "INSERT INTO board_state (board_id, state) VALUES (?, ?)",
            (board_id, state),
        )
        connection.commit()
        return board_id


def list_boards_for_user(user_id: int, db_path: Optional[Path] = None) -> list[dict]:
    with get_connection(db_path) as connection:
        rows = connection.execute(
            "SELECT b.id, b.name, b.updated_at, bm.role FROM boards b "
            "JOIN board_members bm ON bm.board_id = b.id "
            "WHERE bm.user_id = ? ORDER BY b.updated_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_board_member_role(
    board_id: int, user_id: int, db_path: Optional[Path] = None
) -> Optional[str]:
    with get_connection(db_path) as connection:
        row = connection.execute(
            "SELECT role FROM board_members WHERE board_id = ? AND user_id = ?",
            (board_id, user_id),
        ).fetchone()
        return row["role"] if row else None


def rename_board(board_id: int, name: str, db_path: Optional[Path] = None) -> None:
    with get_connection(db_path) as connection:
        connection.execute(
            "UPDATE boards SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (name.strip() or "Untitled Board", board_id),
        )
        connection.commit()


def delete_board(board_id: int, db_path: Optional[Path] = None) -> None:
    with get_connection(db_path) as connection:
        connection.execute("DELETE FROM boards WHERE id = ?", (board_id,))
        connection.commit()


def list_board_members(board_id: int, db_path: Optional[Path] = None) -> list[dict]:
    with get_connection(db_path) as connection:
        rows = connection.execute(
            "SELECT u.id AS user_id, u.username, bm.role FROM board_members bm "
            "JOIN users u ON u.id = bm.user_id WHERE bm.board_id = ? ORDER BY bm.added_at",
            (board_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def add_board_member(
    board_id: int, username: str, role: str = "editor", db_path: Optional[Path] = None
) -> dict:
    if role not in {"owner", "editor"}:
        raise ValueError("Invalid role")

    with get_connection(db_path) as connection:
        user = connection.execute(
            "SELECT * FROM users WHERE username = ?", (username.strip(),)
        ).fetchone()
        if user is None:
            raise ValueError("User not found")

        existing = connection.execute(
            "SELECT 1 FROM board_members WHERE board_id = ? AND user_id = ?",
            (board_id, user["id"]),
        ).fetchone()
        if existing is not None:
            raise ValueError("User is already a member of this board")

        connection.execute(
            "INSERT INTO board_members (board_id, user_id, role) VALUES (?, ?, ?)",
            (board_id, user["id"], role),
        )
        connection.commit()
        return {"user_id": user["id"], "username": user["username"], "role": role}


def remove_board_member(board_id: int, user_id: int, db_path: Optional[Path] = None) -> None:
    with get_connection(db_path) as connection:
        member = connection.execute(
            "SELECT role FROM board_members WHERE board_id = ? AND user_id = ?",
            (board_id, user_id),
        ).fetchone()
        if member is None:
            return

        if member["role"] == "owner":
            owner_count = connection.execute(
                "SELECT COUNT(*) AS count FROM board_members WHERE board_id = ? AND role = 'owner'",
                (board_id,),
            ).fetchone()["count"]
            if owner_count <= 1:
                raise ValueError("Cannot remove the last owner of a board")

        connection.execute(
            "DELETE FROM board_members WHERE board_id = ? AND user_id = ?",
            (board_id, user_id),
        )
        connection.commit()


# --- Board state --------------------------------------------------------------


def get_board_state(board_id: int, db_path: Optional[Path] = None) -> Optional[str]:
    with get_connection(db_path) as connection:
        row = connection.execute(
            "SELECT state FROM board_state WHERE board_id = ?", (board_id,)
        ).fetchone()
        return row["state"] if row else None


def update_board_state(
    board_id: int,
    state: str | dict,
    db_path: Optional[Path] = None,
) -> None:
    if not isinstance(state, str):
        state = json.dumps(state)

    with get_connection(db_path) as connection:
        cursor = connection.execute(
            "UPDATE board_state SET state = ?, updated_at = CURRENT_TIMESTAMP WHERE board_id = ?",
            (state, board_id),
        )
        if cursor.rowcount == 0:
            raise ValueError("Board not found")
        connection.execute(
            "UPDATE boards SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (board_id,)
        )
        connection.commit()


# Backwards-compatible single-board helpers used by the legacy default account.


def get_board_state_by_user_id(
    user_id: int, db_path: Optional[Path] = None,
) -> Optional[str]:
    with get_connection(db_path) as connection:
        row = connection.execute(
            "SELECT bs.state FROM board_state bs "
            "JOIN boards b ON bs.board_id = b.id "
            "WHERE b.owner_id = ?",
            (user_id,),
        ).fetchone()
        return row["state"] if row else None


def update_board_state_by_user_id(
    user_id: int, state: str | dict, db_path: Optional[Path] = None,
) -> None:
    with get_connection(db_path) as connection:
        row = connection.execute(
            "SELECT b.id FROM boards b WHERE b.owner_id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Board not found for user")
        update_board_state(row["id"], state, db_path)


# --- Activity log --------------------------------------------------------------


def log_activity(
    board_id: int,
    user_id: Optional[int],
    action: str,
    details: Optional[dict] = None,
    db_path: Optional[Path] = None,
) -> None:
    with get_connection(db_path) as connection:
        connection.execute(
            "INSERT INTO activity_log (board_id, user_id, action, details) VALUES (?, ?, ?, ?)",
            (board_id, user_id, action, json.dumps(details) if details is not None else None),
        )
        connection.commit()


def list_activity(board_id: int, limit: int = 50, db_path: Optional[Path] = None) -> list[dict]:
    with get_connection(db_path) as connection:
        rows = connection.execute(
            "SELECT a.id, a.board_id, a.user_id, u.username, a.action, a.details, a.created_at "
            "FROM activity_log a LEFT JOIN users u ON u.id = a.user_id "
            "WHERE a.board_id = ? ORDER BY a.id DESC LIMIT ?",
            (board_id, limit),
        ).fetchall()
        results = []
        for row in rows:
            entry = dict(row)
            if entry["details"]:
                try:
                    entry["details"] = json.loads(entry["details"])
                except json.JSONDecodeError:
                    pass
            results.append(entry)
        return results


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
            (DEFAULT_USERNAME, _hash_password(DEFAULT_PASSWORD)),
        ).lastrowid

    cursor = connection.execute(
        "SELECT id FROM boards WHERE owner_id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    if row:
        board_id = row["id"]
    else:
        board_id = connection.execute(
            "INSERT INTO boards (owner_id, name) VALUES (?, ?)",
            (user_id, DEFAULT_BOARD_NAME),
        ).lastrowid

    member = connection.execute(
        "SELECT 1 FROM board_members WHERE board_id = ? AND user_id = ?",
        (board_id, user_id),
    ).fetchone()
    if member is None:
        connection.execute(
            "INSERT INTO board_members (board_id, user_id, role) VALUES (?, ?, 'owner')",
            (board_id, user_id),
        )

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
