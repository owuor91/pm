#!/usr/bin/env sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$FRONTEND_DIR/.." && pwd)"

cd "$FRONTEND_DIR"
npm run build

export PM_STATIC_DIR="$FRONTEND_DIR/out"
export PM_DB_PATH="$(mktemp -d)/pm_e2e.db"

cd "$REPO_ROOT"
exec uv run --project backend uvicorn backend.app:app --host 127.0.0.1 --port 3000
