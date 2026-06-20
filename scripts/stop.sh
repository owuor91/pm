#!/usr/bin/env sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONTAINER_NAME="pm-mvp-backend"

cd "$REPO_ROOT"

if docker ps --filter "name=$CONTAINER_NAME" --format '{{.Names}}' | grep -q "$CONTAINER_NAME"; then
  docker stop "$CONTAINER_NAME"
  echo "Stopped container '$CONTAINER_NAME'"
else
  echo "No running container named '$CONTAINER_NAME' found"
fi
