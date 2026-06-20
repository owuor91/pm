from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .db import init_db

app = FastAPI(title="Project Management MVP Backend")

static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():
    app.mount("/_next", StaticFiles(directory=static_dir / "_next"), name="next")

init_db()


@app.get("/")
def root():
    return FileResponse(static_dir / "index.html")


@app.get("/favicon.ico")
def favicon():
    return FileResponse(static_dir / "favicon.ico")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/hello")
def hello():
    return {"message": "hello"}
