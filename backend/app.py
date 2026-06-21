from pathlib import Path
import json

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.db import (
    init_db,
    get_board_state_by_user_id,
    get_user_by_credentials,
    update_board_state_by_user_id,
)
from backend.ai_service import AIService
from backend.board_updates import apply_board_update
from backend.schemas import AIChatRequest, AIChatResponse, AIResponse, NewCard


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
            "description": "Authentication endpoints for logging in with hardcoded credentials.",
        },
        {
            "name": "board",
            "description": "Board state retrieval and persistence endpoints.",
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize AI service
ai_service = AIService()

static_dir = Path(__file__).resolve().parent / "static"
if (static_dir / "_next").exists():
    app.mount("/_next", StaticFiles(directory=static_dir / "_next"), name="next")

init_db()


@app.get("/")
def root():
    return FileResponse(static_dir / "index.html")


@app.get("/favicon.ico")
def favicon():
    return FileResponse(static_dir / "favicon.ico")


class AuthRequest(BaseModel):
    username: str
    password: str


class BoardStateResponse(BaseModel):
    state: str


class BoardStateUpdateRequest(BaseModel):
    state: str


@app.post(
    "/api/auth",
    response_model=dict,
    tags=["auth"],
    summary="Authenticate user",
    description="Authenticate with hardcoded credentials and return a user ID on success.",
)
def auth(request: AuthRequest):
    user = get_user_by_credentials(request.username, request.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"user_id": user["id"], "username": user["username"]}


@app.get(
    "/api/board",
    response_model=BoardStateResponse,
    tags=["board"],
    summary="Get board state",
    description="Retrieve the saved board state for the given user ID.",
)
def get_board(user_id: int = Query(..., description="The user ID")):
    row = get_board_state_by_user_id(user_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Board not found")
    return {"state": row}


@app.post(
    "/api/board",
    response_model=BoardStateResponse,
    tags=["board"],
    summary="Save board state",
    description="Save the current Kanban board state for the given user ID.",
)
def save_board(request: BoardStateUpdateRequest, user_id: int = Query(..., description="The user ID")):
    try:
        update_board_state_by_user_id(user_id, request.state)
    except ValueError:
        raise HTTPException(status_code=404, detail="Board not found")
    return {"state": request.state}


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
    if not ai_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="AI service is not configured. OPENROUTER_API_KEY is missing.",
        )
    return ai_service.test_connectivity()


@app.post(
    "/api/ai/chat",
    response_model=AIChatResponse,
    tags=["ai"],
    summary="Chat with AI using board context",
    description="Send the user's prompt and current board state to the AI. Applies any returned board updates and persists them.",
)
def ai_chat(request: AIChatRequest):
    if not ai_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="AI service is not configured. OPENROUTER_API_KEY is missing.",
        )

    state = get_board_state_by_user_id(request.userId)
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
        update_board_state_by_user_id(request.userId, json.dumps(next_board_state))
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
