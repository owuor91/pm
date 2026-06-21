# High level steps for project

## Part 1: Plan and audit

- [x] Review existing repo structure and current frontend implementation
- [x] Create `frontend/AGENTS.md` describing current frontend code
- [x] Expand this plan document with a detailed checklist for Parts 2-10
- [x] Confirm user approval before starting any scaffold or implementation work

Success criteria:
- This document contains a step-by-step roadmap
- The frontend description file exists and is accurate
- User explicitly approves the plan before implementation begins

## Part 2: Scaffolding

Goals:
- Add FastAPI backend scaffolding under `backend/`
- Add Docker support and local start/stop scripts
- Serve a minimal static page at `/`
- Confirm an API route works

Tasks:
- [x] Create `backend/app.py` (FastAPI app)
- [x] Add minimal backend routes:
  - `/health` → `{"status":"ok"}`
  - `/api/hello` → `{"message":"hello"}`
- [x] Add `Dockerfile` and optional `docker-compose.yml`
- [x] Add `scripts/start.sh` and `scripts/stop.sh`
- [x] Verify Docker build and run locally

Success criteria:
- Docker image builds cleanly
- Backend runs in container and serves static content at `/`
- `/api/hello` returns valid JSON
- Start/stop scripts work for local development

## Part 3: Add in Frontend

Goals:
- Build the existing Next.js app and serve it from the backend
- Ensure the Kanban demo page is accessible at `/`
- Add frontend-related tests if needed

Tasks:
- [x] Configure the frontend build step in Docker
- [x] Ensure static asset serving or `next start` is set up correctly
- [x] Confirm the Kanban board loads from the backend

Success criteria:
- Frontend builds successfully inside the container
- `/` serves the Kanban UI
- UI renders without errors in production mode

## Part 4: Fake user sign in experience

Goals:
- Add login gating for the Kanban app
- Use hardcoded credentials: `user` / `password`
- Support logout

Tasks:
- [x] Implement login UI in the frontend
- [x] Prevent accessing the Kanban board until authenticated
- [x] Add logout functionality
- [x] Add tests for login and logout flows

Success criteria:
- Unauthenticated visitors cannot see the board
- Correct credentials unlock the board
- Logout returns to the login state

## Part 5: Database modeling

Goals:
- Define a SQLite schema for users and board data
- Persist Kanban state as JSON for MVP simplicity
- Document schema decisions in `docs/`

Tasks:
- [x] Create a database design doc in `docs/`
- [x] Add schema proposal for `users`, `boards`, and `board_state`
- [x] Ensure support for multiple users and one board per user
- [x] Plan DB initialization when missing

Success criteria:
- Documented schema is available in `docs/`
- Schema is approved before backend persistence work begins
- Backend can create the DB automatically if missing

## Part 6: Backend API

Goals:
- Add backend endpoints to read and update a user's Kanban board
- Persist board state in SQLite
- Add backend tests for API and DB behavior

Tasks:
- [x] Implement routes for board retrieval and update
- [x] Use a simple hardcoded user auth model for MVP
- [x] Persist board JSON in SQLite
- [x] Add tests for endpoints and DB operations

Success criteria:
- Backend exposes stable endpoints for board state
- Board state persists across restarts
- Tests verify correct CRUD behavior

## Part 7: Frontend + Backend

Goals:
- Connect the frontend to the backend API for a persisted board
- Keep current board UX and drag/drop behavior
- Confirm persistence across reloads

Tasks:
- [x] Load board data from `/api/board` on startup
- [x] Send board changes to backend endpoints
- [x] Keep frontend state synced with backend
- [x] Add integration tests for end-to-end data flow

Success criteria:
- Frontend loads board state from backend
- Changes persist after page reload
- UI remains interactive and stable

## Part 8: AI connectivity

Goals:
- Add OpenRouter AI support in the backend
- Confirm `OPENROUTER_API_KEY` loads from `.env`
- Verify AI connectivity with a simple prompt

Tasks:
- [x] Implement backend AI service calling OpenRouter
- [x] Create a test route or health check for the AI call
- [x] Add a simple `2+2` connectivity test
- [x] Handle missing API key gracefully

Success criteria:
- Backend can call OpenRouter successfully
- AI route returns expected results for the test prompt
- `.env` key is not committed in source control

## Part 9: AI structured outputs with board context

Goals:
- Send Kanban JSON and conversation context to the AI
- Receive structured output with text and optional board changes
- Apply valid board updates automatically

Tasks:
- [x] Define structured output schema for AI responses
- [x] Build request payload including board data and prompt
- [x] Parse AI response and extract board update instructions
- [x] Add tests for structured parsing and update application

Success criteria:
- AI responses can include board updates
- Backend applies valid updates to persisted state
- Tests validate structured output handling

## Part 10: AI chat UI and Kanban updates

Goals:
- Add an AI chat sidebar in the frontend
- Display AI messages and let AI update the board
- Refresh the board UI automatically after updates

Tasks:
- [x] Build chat sidebar UI
- [x] Post user messages to the backend AI endpoint
- [x] Display AI replies and optional board actions
- [x] Apply board updates in the frontend when returned
- [x] Add integration tests for chat and board refresh

Success criteria:
- Users can chat with AI and receive replies
- AI-driven board updates appear in the UI
- Board state stays consistent after AI actions
