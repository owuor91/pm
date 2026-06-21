FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM ghcr.io/astral-sh/uv:python3.12-alpine

WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --no-dev --frozen

COPY backend/ ./backend
COPY --from=frontend-build /app/frontend/out ./backend/static

RUN mkdir -p /data
ENV PM_DB_PATH=/data/pm.db

EXPOSE 8000
CMD ["uv", "run", "--no-dev", "uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
