FROM node:22-slim AS frontend-build

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FRONTEND_DIST=/app/frontend/dist \
    STOCKFISH_PATH=/usr/games/stockfish

RUN apt-get update \
    && apt-get install -y --no-install-recommends stockfish \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

WORKDIR /app/backend
COPY backend/pyproject.toml ./
COPY backend/src ./src
COPY backend/data ./data
COPY backend/alembic.ini ./
COPY backend/migrations ./migrations
RUN uv pip install --system -e .

COPY --from=frontend-build /build/frontend/dist /app/frontend/dist

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && python -m chess_coach_agent.ingest_knowledge && uvicorn chess_coach_agent.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
