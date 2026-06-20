FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ .
RUN npm run build
RUN mkdir -p /app/frontend/static/_next/static
RUN cp -r .next/static/* /app/frontend/static/_next/static
RUN cp .next/server/app/index.html /app/frontend/static/index.html
RUN cp -r public/* /app/frontend/static/ 2>/dev/null || true

FROM python:3.12-slim AS base

WORKDIR /app
RUN python -m pip install --upgrade pip
RUN python -m pip install fastapi uvicorn

COPY backend/ ./backend
COPY --from=frontend-build /app/frontend/static ./backend/static
WORKDIR /app

EXPOSE 8000
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
