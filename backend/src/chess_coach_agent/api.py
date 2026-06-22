from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .agent import ChessCoachAgent, sample_pgn
from .importers import fetch_platform_pgn, preview_pgn_games
from .llm import answer_question
from .models import (
    AnalyzeRequest,
    AnalyzeResponse,
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    GamePreviewResponse,
    ImportRequest,
)
from .monitoring import log_event, monitoring_summary
from .adaptive_api import router as adaptive_router
from .db import init_db, session_scope
from .repositories import persist_analyses


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Chess Coach Agent API", version="0.2.0", lifespan=lifespan)
agent = ChessCoachAgent()
app.include_router(adaptive_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/sample")
def sample() -> dict[str, str]:
    return {"player": "kfctofu", "pgn": sample_pgn()}


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    log_event("analysis_requested", {"player": request.player, "max_games": request.max_games})
    started = time.perf_counter()
    response = agent.import_pgn_text(request.pgn, player=request.player, max_games=request.max_games)
    with session_scope() as session:
        persist_analyses(session, request.platform, request.player, response)
    log_event(
        "analysis_timing",
        {"duration_ms": round((time.perf_counter() - started) * 1000, 2), "games": len(response.analyses)},
    )
    return response


@app.post("/api/import", response_model=AnalyzeResponse)
async def import_games(request: ImportRequest) -> AnalyzeResponse:
    response = await agent.import_platform_games(request)
    with session_scope() as session:
        persist_analyses(session, request.platform, request.username, response)
    return response


@app.post("/api/games/preview", response_model=GamePreviewResponse)
async def preview_games(request: ImportRequest) -> GamePreviewResponse:
    pgn = await fetch_platform_pgn(request.platform, request.username, request.max_games)
    games = preview_pgn_games(pgn, request.username, request.platform, request.max_games)
    log_event(
        "games_previewed",
        {"platform": request.platform, "username": request.username, "games": len(games)},
    )
    return GamePreviewResponse(username=request.username, platform=request.platform, games=games)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    log_event("chat_requested", {"has_analysis": request.analysis is not None})
    started = time.perf_counter()
    response = await answer_question(request.question, request.analysis)
    log_event(
        "chat_completed",
        {
            "used_llm": response.used_llm,
            "retrieved_notes": len(response.retrieved_notes),
            "tools_used": response.tools_used,
            "trace_id": response.trace_id,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "usage": response.usage.model_dump() if response.usage else None,
        },
    )
    return response


@app.post("/api/feedback")
def feedback(request: FeedbackRequest) -> dict[str, str]:
    log_event("moment_feedback", request.model_dump())
    return {"status": "recorded"}


@app.get("/api/monitoring")
def monitoring() -> dict:
    return monitoring_summary()


@app.get("/api/trends")
def trends() -> dict:
    return agent.generate_trend_summary(sample_pgn(), player="kfctofu").model_dump()


frontend_value = os.getenv("FRONTEND_DIST", "")
frontend_dist = Path(frontend_value) if frontend_value else None
if frontend_dist and (frontend_dist / "index.html").exists():
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def frontend(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        requested = (frontend_dist / full_path).resolve()
        if requested.is_relative_to(frontend_dist.resolve()) and requested.is_file():
            return FileResponse(requested)
        return FileResponse(frontend_dist / "index.html")
else:
    @app.get("/", include_in_schema=False)
    def local_frontend() -> RedirectResponse:
        return RedirectResponse("http://127.0.0.1:5173/")
