# Backend AGENTS.md

## Overview

Python FastAPI backend serving the Kanban board MVP.

## Key files

- `app.py` — FastAPI application, routes, CORS, static file serving
- `db.py` — SQLite database initialization, schema, user auth, board state persistence
- `ai_service.py` — OpenRouter AI API client with board context support
- `board_updates.py` — Applies structured AI-suggested board changes to state
- `schemas.py` — Pydantic models for API request/response and board updates

## Dependencies

Managed by `uv` with `pyproject.toml` and `uv.lock`.
- fastapi, uvicorn, httpx, python-dotenv, pydantic

## Testing

```
cd backend && uv run pytest -v
```

Tests use `tmp_path` for isolated databases (monkeypatch `PM_DB_PATH`).
