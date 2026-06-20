FROM python:3.12-slim AS base

WORKDIR /app

RUN python -m pip install --upgrade pip
RUN python -m pip install fastapi uvicorn

COPY backend/ ./backend
WORKDIR /app/backend

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
