# Code Review

## Security Issues (HIGH)

1. **API key committed in `.env`** — `.env` is gitignored, but the file already exists committed in the repo. The `OPENROUTER_API_KEY` value is exposed. Rotate the key and re-commit without the file. Use `git rm --cached .env` to stop tracking.

2. **Passwords stored in plaintext** — `backend/db.py` inserts and compares raw passwords (`test_db.py:22-23`). Even for an MVP, use a hashing library (e.g. `passlib` + `bcrypt`). The schema has no salt/hash column either.

3. **No session or auth token** — `LoginGate` stores `userId` only in React state. A page refresh forces re-login. Acceptable for MVP but should be documented as a known limitation.

## Backend Issues

| File:Lines | Issue |
|---|---|
| `app.py:188-192` | `AttributeError` catch for pydantic v1 compat is unnecessary — the project requires Python >=3.11 and uses modern pydantic v2. Remove the v1 fallback. |
| `app.py` | No CORS middleware. Works now (same origin via static serving), but will break if frontend/backend are ever separated. |
| `db.py:99-104` | `get_connection` sets `PRAGMA foreign_keys = ON` per-call. This is session-level and correct (SQLite resets pragmas per connection), but worth noting intentionally. |
| `board_updates.py:9` | `apply_board_update` mutates the input `board_state` dict in-place and returns it. The caller at `app.py:197` stores the returned value, which is the same mutated object. This is misleading — either make it truly pure (deep copy) or don't return the dict. |
| `schemas.py:34-38` | `AIRequest` model is defined but **never imported or used** anywhere. Remove dead code. |
| `ai_service.py:39` | 30-second timeout may be too short for free-tier OpenRouter models, which can be slow (10-60s). Consider increasing to 60s or making configurable. |
| `board_updates.py:21,58-82` | `newCards` is typed as `List[Dict[str, Any]]` with manual field validation. Better to define a `NewCard` Pydantic model for type safety. |
| `test_app.py` | Tests use the **production database** (`backend/pm.db`). No `tmp_path` isolation, so test order matters and `test_save_board_valid_user` mutates state for subsequent runs. |
| `test_db.py:38` | `update_board_state_by_user_id(1, ...)` hardcodes `user_id=1`, assuming sequential auto-increment IDs. Fragile across test runs with different seed states. |

## Frontend Issues

| File:Lines | Issue |
|---|---|
| `lib/kanban.ts:164-168` | `createId` uses `Math.random()` + `Date.now()`. Collisions are unlikely but possible. Use `crypto.randomUUID()` (available in all modern browsers). |
| `KanbanBoard.tsx:138-147` | `flushSave` captures `board` via `useCallback`. It's passed through `CopilotDialog` -> `ChatSidebar` and called from `handleSubmit`. The closure is usually fresh due to re-renders, but the pattern is fragile — `onBeforeSend` prop could become stale if a parent skips re-render. |
| `KanbanBoard.tsx:46-66` | Debounced auto-save fires on **every** board state change, including keystrokes in column rename. This generates many API calls. Consider flush-on-blur or a manual "Save" button for rename operations. |
| `api.ts:24-25` | `getBoard` calls `JSON.parse(data.state)` without try/catch. A corrupt DB state would throw an unhandled error in the frontend with no user feedback. |
| `kanban.ts:84-162` | `moveCard` is well-tested but complex. The `isOverColumn` branch at line 106 appends the card to the **end** rather than at the drop pointer position within the column — unexpected for users dropping onto a specific spot. |
| `KanbanCard.tsx:29` | `{...listeners}` on the same element as a clickable "Remove" button. dnd-kit filters button clicks internally, but worth noting for future maintainers. |

## Docker / Build Issues (HIGH)

1. **Dockerfile frontend build is broken.** `next.config.ts` uses `output: "export"`, which writes static output to `out/`, but the Dockerfile at lines 9-11 references `.next/server/app/index.html` and `.next/static/` — these paths do not exist in static export mode. Should copy from `out/` instead.

2. **Uses pip instead of uv.** Root `AGENTS.md` specifies "uv" as the Python package manager, but `Dockerfile:17` uses `pip install`. The `pyproject.toml` lists dependencies but they aren't installed from it.

3. **No dependency pinning.** The Dockerfile installs `fastapi`, `uvicorn`, `httpx`, `python-dotenv` with no version constraints, risking build breakage from upstream releases. Pin to known-good versions or install from `pyproject.toml`.

## Code Duplication

- Initial board data is defined identically in **two places**:
  - `frontend/src/lib/kanban.ts` — `initialData` (TypeScript)
  - `backend/db.py` — `DEFAULT_BOARD_STATE_OBJECT` (Python)
  Any structural change to the board (new columns, card shape) must be updated in both. Consider a shared JSON file or a build-time sync step.

## Documentation / AGENTS.md

| File | Issue |
|---|---|
| `backend/AGENTS.md` | Placeholder text only — should describe backend structure and architecture |
| `scripts/AGENTS.md` | Placeholder text only — should list available scripts and their usage |
| Root `AGENTS.md:28` | Model name uses spaces: `openai/gpt-oss-120b (free)` but `ai_service.py:11` uses `openai/gpt-oss-120b:free` (colon separator). Inconsistent. |
| `PLAN.md` | Part 1 items 7-9 are still unchecked even though the work appears complete or in progress |

## What's Done Well

- Clean separation of concerns in the backend (`db.py`, `ai_service.py`, `board_updates.py`, `schemas.py`)
- Good test coverage on both sides: 8 frontend component/lib tests, 5 backend test modules
- `ChatSidebar` auto-scroll and error handling are well-implemented
- Consistent color scheme via CSS custom properties
- Drag-and-drop with `@dnd-kit` is well-integrated
- Debounced save avoids hammering the API on rapid changes
- TypeScript types and React patterns are modern and idiomatic
- Backend tests cover both success and failure paths for most endpoints
- Static file serving setup in FastAPI is clean and minimal
