from pathlib import Path
import json
import os

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.db import (
    EMPTY_BOARD_STATE,
    SESSION_TTL_SECONDS,
    add_board_member,
    create_board,
    create_session,
    create_user,
    delete_board,
    delete_other_sessions,
    delete_session,
    get_board_member_role,
    get_board_state,
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
    update_user_password,
)
from backend import rate_limit
from backend.ai_service import AIService
from backend.board_updates import apply_board_update
from backend.schemas import AIChatRequest, AIChatResponse, AIResponse

SESSION_COOKIE_NAME = "session_token"
ROLE_RANK = {"editor": 1, "owner": 2}


app = FastAPI(
    title="Project Management MVP Backend",
    description="FastAPI backend for the Project Management MVP, exposing auth and Kanban board persistence APIs.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=[
        {
            "name": "auth",
            "description": "Authentication endpoints (signup, login, logout, session lookup).",
        },
        {
            "name": "boards",
            "description": "Board CRUD, membership, state, and activity endpoints.",
        },
        {
            "name": "ai",
            "description": "AI connectivity and interaction endpoints.",
        },
        {
            "name": "health",
            "description": "Service health check endpoints.",
        },
    ],
)

DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ALLOWED_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]

# Cookie-based sessions mean responses carry credentials; allow_origins=["*"] combined with
# allow_credentials=True would make Starlette reflect back any request Origin, letting any
# site read API responses using a logged-in user's cookie. Only the frontend dev server
# origins need cross-origin access (production serves both from one origin, no CORS needed).
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize AI service
ai_service = AIService()

static_dir = Path(os.environ.get("PM_STATIC_DIR", str(Path(__file__).resolve().parent / "static")))
if (static_dir / "_next").exists():
    app.mount("/_next", StaticFiles(directory=static_dir / "_next"), name="next")

init_db()


@app.get("/")
def root():
    return FileResponse(static_dir / "index.html")


@app.get("/favicon.ico")
def favicon():
    return FileResponse(static_dir / "favicon.ico")


def get_current_user(request: Request):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = get_user_by_session_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def require_board_role(board_id: int, user, min_role: str = "editor") -> str:
    role = get_board_member_role(board_id, user["id"])
    if role is None:
        raise HTTPException(status_code=404, detail="Board not found")
    if ROLE_RANK[role] < ROLE_RANK[min_role]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return role


def require_ai_configured() -> None:
    if not ai_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="AI service is not configured. OPENROUTER_API_KEY is missing.",
        )


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=SESSION_TTL_SECONDS,
        path="/",
    )


class SignupRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str


class BoardCreateRequest(BaseModel):
    name: str


class BoardRenameRequest(BaseModel):
    name: str


class BoardMemberCreateRequest(BaseModel):
    username: str
    role: str = "editor"


class BoardStateUpdateRequest(BaseModel):
    state: str


@app.post(
    "/api/auth/signup",
    tags=["auth"],
    summary="Create a new account",
    description="Create a new user account, log them in, and provision a starter board.",
)
def signup(request: SignupRequest, response: Response):
    try:
        user_id = create_user(request.username, request.password)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    create_board(user_id, "My Board", state=EMPTY_BOARD_STATE)
    token, _ = create_session(user_id)
    _set_session_cookie(response, token)
    return {"user_id": user_id, "username": request.username.strip()}


@app.post(
    "/api/auth/login",
    tags=["auth"],
    summary="Log in",
    description="Authenticate with username and password and start a session.",
)
def login(request: LoginRequest, response: Response):
    rate_limit_key = request.username.strip()
    if rate_limit.is_locked_out(rate_limit_key):
        raise HTTPException(
            status_code=429, detail="Too many failed login attempts. Try again later."
        )

    user = get_user_by_credentials(request.username, request.password)
    if user is None:
        rate_limit.record_failure(rate_limit_key)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    rate_limit.reset(rate_limit_key)
    token, _ = create_session(user["id"])
    _set_session_cookie(response, token)
    return {"user_id": user["id"], "username": user["username"]}


@app.post(
    "/api/auth/logout",
    tags=["auth"],
    summary="Log out",
    description="End the current session.",
)
def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        delete_session(token)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"status": "ok"}


@app.get(
    "/api/auth/me",
    tags=["auth"],
    summary="Get the current session's user",
    description="Resolve the signed-in user from the session cookie.",
)
def me(user=Depends(get_current_user)):
    return {"user_id": user["id"], "username": user["username"]}


@app.post(
    "/api/auth/change-password",
    tags=["auth"],
    summary="Change password",
    description="Change the current user's password after verifying their current password. Invalidates all other sessions.",
)
def change_password(request: Request, body: ChangePasswordRequest, user=Depends(get_current_user)):
    try:
        update_user_password(user["id"], body.currentPassword, body.newPassword)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    current_token = request.cookies.get(SESSION_COOKIE_NAME)
    if current_token:
        delete_other_sessions(user["id"], current_token)
    return {"status": "ok"}


@app.get(
    "/api/boards",
    tags=["boards"],
    summary="List my boards",
    description="List all boards the current user is a member of.",
)
def list_boards(user=Depends(get_current_user)):
    return list_boards_for_user(user["id"])


@app.post(
    "/api/boards",
    tags=["boards"],
    summary="Create a board",
    description="Create a new board owned by the current user.",
)
def create_board_route(request: BoardCreateRequest, user=Depends(get_current_user)):
    board_id = create_board(user["id"], request.name)
    return {"id": board_id, "name": request.name.strip() or "Untitled Board", "role": "owner"}


@app.patch(
    "/api/boards/{board_id}",
    tags=["boards"],
    summary="Rename a board",
    description="Rename a board. Requires board membership.",
)
def rename_board_route(board_id: int, request: BoardRenameRequest, user=Depends(get_current_user)):
    require_board_role(board_id, user, min_role="editor")
    rename_board(board_id, request.name)
    return {"id": board_id, "name": request.name.strip() or "Untitled Board"}


@app.delete(
    "/api/boards/{board_id}",
    tags=["boards"],
    summary="Delete a board",
    description="Delete a board. Owner only.",
)
def delete_board_route(board_id: int, user=Depends(get_current_user)):
    require_board_role(board_id, user, min_role="owner")
    delete_board(board_id)
    return {"status": "ok"}


@app.get(
    "/api/boards/{board_id}/members",
    tags=["boards"],
    summary="List board members",
    description="List the members of a board. Requires board membership.",
)
def list_board_members_route(board_id: int, user=Depends(get_current_user)):
    require_board_role(board_id, user, min_role="editor")
    return list_board_members(board_id)


@app.post(
    "/api/boards/{board_id}/members",
    tags=["boards"],
    summary="Add a board member",
    description="Share a board with another user by username. Owner only.",
)
def add_board_member_route(
    board_id: int, request: BoardMemberCreateRequest, user=Depends(get_current_user)
):
    require_board_role(board_id, user, min_role="owner")
    try:
        member = add_board_member(board_id, request.username, request.role)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    log_activity(board_id, user["id"], "member_added", {"username": member["username"], "role": member["role"]})
    return member


@app.delete(
    "/api/boards/{board_id}/members/{member_user_id}",
    tags=["boards"],
    summary="Remove a board member",
    description="Remove a member from a board. Owners can remove anyone; any member can remove themselves to leave the board.",
)
def remove_board_member_route(board_id: int, member_user_id: int, user=Depends(get_current_user)):
    is_self = member_user_id == user["id"]
    require_board_role(board_id, user, min_role="editor" if is_self else "owner")
    try:
        remove_board_member(board_id, member_user_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    log_activity(
        board_id, user["id"], "member_left" if is_self else "member_removed", {"user_id": member_user_id}
    )
    return {"status": "ok"}


@app.get(
    "/api/boards/{board_id}/state",
    tags=["boards"],
    summary="Get board state",
    description="Retrieve the saved Kanban state for a board. Requires board membership.",
)
def get_board_state_route(board_id: int, user=Depends(get_current_user)):
    require_board_role(board_id, user, min_role="editor")
    state = get_board_state(board_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Board not found")
    return {"state": state}


@app.post(
    "/api/boards/{board_id}/state",
    tags=["boards"],
    summary="Save board state",
    description="Save the current Kanban state for a board. Requires board membership.",
)
def save_board_state_route(
    board_id: int, request: BoardStateUpdateRequest, user=Depends(get_current_user)
):
    require_board_role(board_id, user, min_role="editor")
    try:
        update_board_state(board_id, request.state)
    except ValueError:
        raise HTTPException(status_code=404, detail="Board not found")
    log_activity(board_id, user["id"], "board_state_saved")
    return {"state": request.state}


@app.get(
    "/api/boards/{board_id}/activity",
    tags=["boards"],
    summary="List recent board activity",
    description="List the most recent activity log entries for a board. Requires board membership.",
)
def get_board_activity_route(board_id: int, user=Depends(get_current_user)):
    require_board_role(board_id, user, min_role="editor")
    return list_activity(board_id)


@app.get(
    "/health",
    tags=["health"],
    summary="Health check",
    description="Returns a simple status payload to confirm the service is running.",
)
def health():
    return {"status": "ok"}


@app.get(
    "/api/ai/test",
    tags=["ai"],
    summary="Test AI connectivity",
    description="Test connection to OpenRouter AI with a simple prompt.",
)
def test_ai():
    require_ai_configured()
    return ai_service.test_connectivity()


@app.post(
    "/api/ai/chat",
    response_model=AIChatResponse,
    tags=["ai"],
    summary="Chat with AI using board context",
    description="Send the user's prompt and current board state to the AI. Applies any returned board updates and persists them.",
)
def ai_chat(request: AIChatRequest, user=Depends(get_current_user)):
    require_ai_configured()
    require_board_role(request.boardId, user, min_role="editor")

    state = get_board_state(request.boardId)
    if state is None:
        raise HTTPException(status_code=404, detail="Board not found")

    try:
        board_state = json.loads(state)
    except json.JSONDecodeError:
        board_state = {"columns": [], "cards": {}}

    conversation = None
    if request.messages:
        conversation = [{"role": message.role, "content": message.content} for message in request.messages]

    raw = ai_service.call_ai_with_board_context(
        prompt=request.prompt,
        board_state=board_state,
        conversation=conversation,
    )

    try:
        raw_json = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="AI returned non-JSON response")

    try:
        ai_response = AIResponse.model_validate(raw_json)
    except Exception:
        raise HTTPException(status_code=502, detail="AI returned invalid response shape")

    applied = False
    next_board_state = board_state
    if ai_response.boardUpdate is not None:
        next_board_state = apply_board_update(board_state, ai_response.boardUpdate)
        update_board_state(request.boardId, json.dumps(next_board_state))
        log_activity(request.boardId, user["id"], "ai_update", {"prompt": request.prompt})
        applied = True

    return {
        "message": ai_response.message,
        "boardState": json.dumps(next_board_state),
        "applied": applied,
        "confidence": ai_response.confidence,
    }


@app.get("/api/hello")
def hello():
    return {"message": "hello"}
