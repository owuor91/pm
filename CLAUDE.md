# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A Project Management MVP: a single-board Kanban app with hardcoded login, drag-and-drop cards, and an AI chat sidebar (via OpenRouter) that can create/edit/move cards. See `AGENTS.md` for full business requirements and `docs/PLAN.md` for the build roadmap (all parts complete). `docs/DATABASE.md` documents the schema rationale; `docs/code_review.md` is a point-in-time review — verify findings against current code before treating them as outstanding.

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
npm run test:e2e             # playwright (auto-starts next dev on :3000)
npm run test:all             # unit + e2e
```

### Docker (full stack, matches production)

```bash
./scripts/start.sh   # builds frontend, builds image, runs container on :8000
./scripts/stop.sh
```

## Architecture

This is two independently-developed apps glued together at build/serve time, not a monorepo with shared tooling:

- **Frontend** (`frontend/`) is a Next.js app built with `output: "export"` — it produces static HTML/JS in `frontend/out/`, it does not run `next start` in production.
- **Backend** (`backend/`) is FastAPI. In Docker (`Dockerfile`), the frontend's `out/` is copied into `backend/static/`, and `backend/app.py` serves `index.html` at `/` and mounts `_next` assets, while also exposing `/api/*` JSON routes. There is no reverse proxy — one process serves both UI and API.
- In local frontend dev (`npm run dev`), the Next app talks to the backend over HTTP using `window.location.origin` as the API base (`frontend/src/lib/api.ts`) — for that to work against a real backend, run both processes and proxy/CORS accordingly; CORS is wide open (`allow_origins=["*"]`) in `app.py` to support this split.

### Backend structure (`backend/`)

- `app.py` — FastAPI app, all routes, CORS, static file mounting. Calls `init_db()` at import time.
- `db.py` — sqlite3 access layer (no ORM). Schema: `users` / `boards` / `board_state` (one board per user; board state stored as a JSON blob in `board_state.state`, not normalized). Seeds a default `user`/`password` account and default board on init. `_maybe_upgrade_board_state` migrates an older single-column board shape found in existing DBs into the current 5-column shape — relevant when changing the board schema. DB path is `PM_DB_PATH` env var (defaults to `backend/pm.db`; Docker sets it to `/data/pm.db` for persistence across container restarts).
- `ai_service.py` — OpenRouter client (`openai/gpt-oss-120b:free`), reads `OPENROUTER_API_KEY` from `.env`. `is_configured()` gates AI routes so missing keys degrade gracefully (503) instead of crashing.
- `schemas.py` — Pydantic models for AI chat request/response, including the structured `AIResponse` (message + optional `boardUpdate` + confidence) the model is asked to return.
- `board_updates.py` — applies an AI-proposed `boardUpdate` onto the current board state dict (add/move/edit cards).
- Auth is a single hardcoded user (`user`/`password`, sha256-hashed in `db.py`); there is no session/token — the frontend just holds `userId` in React state after login.

### Frontend structure (`frontend/src/`)

- `lib/api.ts` — all backend HTTP calls (`authUser`, `getBoard`, `saveBoard`, `aiChat`). `getBoard`/`aiChat` `JSON.parse` a `state`/`boardState` string field returned by the backend, since board state travels as a JSON string end-to-end.
- `lib/kanban.ts` — `Card`/`Column`/`BoardData` types and `moveCard` drag-and-drop logic (within-column and cross-column reordering). Also has `initialData`, a fixture mirroring `DEFAULT_BOARD_STATE_OBJECT` in `backend/db.py` — if you change the default board shape, update both.
- `components/LoginGate.tsx` — gates the board behind hardcoded auth, calls `authUser`.
- `components/KanbanBoard.tsx` — top-level board state owner; loads/saves via `lib/api.ts` (debounced auto-save on changes), wires up `@dnd-kit` `DndContext`, renders columns and the chat sidebar.
- `components/KanbanColumn.tsx`, `KanbanCard.tsx`, `KanbanCardPreview.tsx`, `NewCardForm.tsx` — column/card rendering and drag previews via `@dnd-kit/sortable`.
- `components/ChatSidebar.tsx` / `CopilotDialog.tsx` — AI chat UI; posts to `aiChat`, applies any returned board state into the board owner's state.
- Tests live next to source as `*.test.tsx`/`*.test.ts` (Vitest + Testing Library, jsdom); Playwright e2e specs are separate under `frontend/tests/`.

## Coding standards (from `AGENTS.md`)

- Keep it simple — no over-engineering, no unnecessary defensive programming, no speculative features.
- Be concise; no emojis anywhere (code, docs, commits).
- When debugging, find the root cause with evidence before applying a fix — don't guess.
- `.env` (OpenRouter key) must never be committed.
