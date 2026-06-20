from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Project Management MVP Backend")

static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():
    app.mount("/_next", StaticFiles(directory=static_dir / "_next"), name="next")


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
