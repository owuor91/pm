from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.db import (
    init_db,
    get_board_state_by_user_id,
    get_user_by_credentials,
    update_board_state_by_user_id,
)

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
            "name": "health",
            "description": "Service health check endpoints.",
        },
    ],
)

static_dir = Path(__file__).resolve().parent / "static"
next_dir = static_dir / "_next"
if next_dir.exists():
    app.mount("/_next", StaticFiles(directory=next_dir), name="next")

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


@app.get("/api/hello")
def hello():
    return {"message": "hello"}
