# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A Project Management app: multi-user accounts with real signup/login (cookie-based sessions), multiple Kanban boards per user, board sharing (owner/editor roles), per-board activity logs, drag-and-drop cards with due dates and labels, search/filtering, and an AI chat sidebar (via OpenRouter) that can create/edit/move cards. See `AGENTS.md` for the original MVP business requirements (note: the "hardcoded single user / single board" limitations described there have since been superseded — see below) and `docs/PLAN.md` for the original build roadmap. `docs/DATABASE.md` documents the original schema rationale; `docs/code_review.md` is a point-in-time review — verify findings against current code before treating them as outstanding.

## Commands

### Backend (`backend/`, uv-managed)

```bash
cd backend && uv run pytest -v                  # all tests
cd backend && uv run pytest test_app.py -v       # single file
cd backend && uv run pytest test_app.py::test_name -v  # single test
cd backend && uv run uvicorn backend.app:app --reload --port 8000  # run dev server
```

### Frontend (`frontend/`)

```bash
npm install
npm run dev                 # next dev server (standalone, no backend)
npm run build                # next build -> static export in out/
npm run lint
npm run test:unit            # vitest run
npm run test:unit:watch      # vitest watch mode
npx vitest run src/components/KanbanBoard.test.tsx   # single test file
npm run test:e2e             # playwright (builds frontend + runs backend on :3000, see frontend/scripts/e2e-server.sh)
npm run test:all             # unit + e2e
```

E2E tests run against the real FastAPI backend (not the standalone `next dev` server), because auth/board state require backend cookies and API routes. `frontend/scripts/e2e-server.sh` builds the frontend, points the backend at the build output via `PM_STATIC_DIR`, and runs it against a fresh temp `PM_DB_PATH` on port 3000.

### Docker (full stack, matches production)

```bash
./scripts/start.sh   # builds frontend, builds image, runs container on :8000
./scripts/stop.sh
```

## Architecture

This is two independently-developed apps glued together at build/serve time, not a monorepo with shared tooling:

- **Frontend** (`frontend/`) is a Next.js app built with `output: "export"` — it produces static HTML/JS in `frontend/out/`, it does not run `next start` in production.
- **Backend** (`backend/`) is FastAPI. In Docker (`Dockerfile`), the frontend's `out/` is copied into `backend/static/`, and `backend/app.py` serves `index.html` at `/` and mounts `_next` assets, while also exposing `/api/*` JSON routes. There is no reverse proxy — one process serves both UI and API.
- In local frontend dev (`npm run dev`), the Next app talks to the backend over HTTP using `window.location.origin` as the API base (`frontend/src/lib/api.ts`) — for that to work against a real backend, run both processes and proxy/CORS accordingly. CORS allows only `http://localhost:3000` and `http://127.0.0.1:3000` by default (override via `CORS_ALLOWED_ORIGINS`, comma-separated) in `app.py` — it is deliberately **not** `allow_origins=["*"]`: since auth now uses real session cookies (`allow_credentials=True`), a wildcard origin would make Starlette reflect back any request's `Origin` header, letting other sites read API responses using a logged-in user's session. Production (Docker) serves frontend and backend from one origin, so CORS isn't exercised there at all.

### Backend structure (`backend/`)

- `app.py` — FastAPI app, all routes, CORS, static file mounting. Calls `init_db()` at import time. Auth routes (`/api/auth/signup`, `/login`, `/logout`, `/me`, `/change-password`) set/read an httpOnly `session_token` cookie; a `get_current_user` dependency resolves the user from it. `login` is gated by `backend/rate_limit.py` (in-memory, per-username failure counter; 5 failures locks the username out for 15 minutes, returning 429 — resets on a successful login). `change-password` verifies the current password and invalidates every other session for that user (`delete_other_sessions`), keeping only the session making the request. Board routes are nested under `/api/boards/{board_id}/...` and gated by `require_board_role` (role checks: `owner` > `editor`). Removing a board member is owner-only, except a member can always remove themselves (`is_self` check in `remove_board_member_route`) to leave a board — `db.remove_board_member` still rejects removing the board's last `owner` regardless of who calls it.
- `rate_limit.py` — in-process login lockout tracker (module-level dict, not persisted). Tests that reload `backend.app`/`backend.db` via `importlib.reload` must also reload `backend.rate_limit`, otherwise lockout state leaks between test functions since the module-level `_state` dict survives reloads of modules that merely reference it.
- `db.py` — sqlite3 access layer (no ORM). Schema: `users` / `sessions` / `boards` / `board_members` / `board_state` / `activity_log`. A board has one `owner_id` but can have multiple members via `board_members` (role `owner` or `editor`), enabling sharing. Board state is still a JSON blob in `board_state.state`, not normalized. `init_db` seeds a default `user`/`password` account and board on init, and `_migrate_schema` handles upgrading an older single-owner-column (`boards.user_id`) DB found on disk into the current `owner_id` + `board_members` shape — relevant when changing the board/membership schema further. `_maybe_upgrade_board_state` similarly migrates an older single-column board shape into the current 5-column shape. DB path is `PM_DB_PATH` env var (defaults to `backend/pm.db`; Docker sets it to `/data/pm.db` for persistence across container restarts).
- `ai_service.py` — OpenRouter client (`openai/gpt-oss-120b:free`), reads `OPENROUTER_API_KEY` from `.env`. `is_configured()` gates AI routes so missing keys degrade gracefully (503) instead of crashing. The board-context prompt also supports optional `dueDate`/`labels` fields on cards.
- `schemas.py` — Pydantic models for AI chat request/response, including the structured `AIResponse` (message + optional `boardUpdate` + confidence) the model is asked to return. `NewCard`/`CardUpdate` carry optional `dueDate`/`labels`.
- `board_updates.py` — applies an AI-proposed `boardUpdate` onto the current board state dict (add/move/edit cards, including `dueDate`/`labels`).
- Auth supports real signup (any username/password) plus the seeded default `user`/`password` account. Sessions are opaque random tokens stored server-side in `sessions` (7-day TTL), not JWTs — kept deliberately simple since there's no need for stateless verification at this scale. Passwords are hashed with per-user-salted PBKDF2-SHA256 (`_hash_password`/`_verify_password` in `db.py`), stored as `salt_hex$digest_hex`; `_verify_password` also accepts the old unsalted-sha256 format for backward compatibility with any pre-existing DB, but `create_user`/password changes always write the new salted format. `create_user` also enforces `MIN_PASSWORD_LENGTH` (8) — the seeded default password (`password`) is exactly 8 chars, so don't lower this without checking that seed.

### Frontend structure (`frontend/src/`)

- `lib/api.ts` — all backend HTTP calls (`signup`/`login`/`logout`/`me`, board CRUD, membership, `getBoardState`/`saveBoardState`, `getActivity`, `aiChat`). All requests use `credentials: "include"` so the session cookie is sent. `getBoardState`/`aiChat` `JSON.parse` a `state`/`boardState` string field returned by the backend, since board state travels as a JSON string end-to-end.
- `lib/kanban.ts` — `Card` (with optional `dueDate`/`labels`)/`Column`/`BoardData` types and `moveCard` drag-and-drop logic (within-column and cross-column reordering). Also has `initialData`, a fixture mirroring `DEFAULT_BOARD_STATE_OBJECT` in `backend/db.py` — if you change the default board shape, update both.
- `components/LoginGate.tsx` — toggles between login and signup forms, calls `login`/`signup`, and bootstraps an existing session via `me()` on mount so refreshing the page doesn't force a re-login. `handleLogout` resets `mode` back to `"login"` — without that, a user who signed up (switching the form to signup mode) and later logs out gets dropped back into the signup form, not login (a real bug caught by an e2e test, not just intuition).
- `components/ChangePasswordDialog.tsx` — lets the signed-in user change their password (verifies the current one server-side); the backend invalidates all other sessions on success but keeps the current one logged in.
- `components/KanbanBoard.tsx` — top-level state owner: requires `userId`/`username` (from `LoginGate`'s session), loads the user's board list (`listBoards`), tracks the selected board, loads/saves its state via `lib/api.ts` (debounced auto-save, flushed before switching/creating boards), wires up `@dnd-kit` `DndContext`, and renders the board picker, search/filter bar, columns, chat sidebar, and members/activity dialogs. Also owns "leave board" (calls `removeBoardMember` with the current user's own ID; shown only for `editor` members — owners must transfer or delete instead, and the backend rejects removing the last owner regardless).
- `components/BoardPicker.tsx` — switch/create/rename/delete boards.
- `components/BoardMembersDialog.tsx` — view members and (owner-only) add/remove them by username, for board sharing. Hides the remove control for the sole owner (removing the last owner is rejected server-side; the dialog surfaces that error if it ever occurs).
- `components/ActivityDialog.tsx` — lists recent `activity_log` entries for the selected board.
- `components/KanbanColumn.tsx`, `KanbanCard.tsx`, `KanbanCardPreview.tsx`, `NewCardForm.tsx` — column/card rendering, drag previews via `@dnd-kit/sortable`, due date/label entry, and inline card editing (`KanbanCard` toggles an edit form for title/details/dueDate/labels — the only way to edit a card besides the AI chat).
- `components/ChatSidebar.tsx` / `CopilotDialog.tsx` — AI chat UI scoped to a `boardId`; posts to `aiChat`, applies any returned board state into the board owner's state.
- Tests live next to source as `*.test.tsx`/`*.test.ts` (Vitest + Testing Library, jsdom); Playwright e2e specs are separate under `frontend/tests/`. E2E runs against the real backend via `frontend/scripts/e2e-server.sh` (see Commands above), not the standalone dev server, since auth/board routes are required.

## Coding standards (from `AGENTS.md`)

- Keep it simple — no over-engineering, no unnecessary defensive programming, no speculative features.
- Be concise; no emojis anywhere (code, docs, commits).
- When debugging, find the root cause with evidence before applying a fix — don't guess.
- `.env` (OpenRouter key) must never be committed.
