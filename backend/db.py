from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).resolve().parent / "pm.db"
DEFAULT_USERNAME = "user"
DEFAULT_PASSWORD = "password"
DEFAULT_BOARD_NAME = "Default Board"
DEFAULT_BOARD_STATE = json.dumps({"columns": [], "cards": {}})

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
            (DEFAULT_USERNAME, DEFAULT_PASSWORD),
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
    if cursor.fetchone() is None:
        connection.execute(
            "INSERT INTO board_state (board_id, state) VALUES (?, ?)",
            (board_id, DEFAULT_BOARD_STATE),
        )

    connection.commit()
