#!/usr/bin/env sh
set -e

IMAGE_NAME="pm-mvp-backend"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

docker build -t "$IMAGE_NAME" "$REPO_ROOT"

docker run --rm -d -p 8000:8000 --name "$IMAGE_NAME" --env-file "$REPO_ROOT/.env" "$IMAGE_NAME"
echo "Started container '$IMAGE_NAME' at http://localhost:8000"