#!/usr/bin/env sh
set -e

IMAGE_NAME="pm-mvp-backend"

docker build -t "$IMAGE_NAME" ..

docker run --rm -d -p 8000:8000 --name "$IMAGE_NAME" "$IMAGE_NAME"
echo "Started container '$IMAGE_NAME' at http://localhost:8000"