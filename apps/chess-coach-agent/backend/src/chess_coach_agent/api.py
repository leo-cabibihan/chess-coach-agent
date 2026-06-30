from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .env_bootstrap import load_project_env  # noqa: F401 — loads backend/.env on import

from .agent import ChessCoachAgent, sample_pgn
from .models import (
    AnalyzeRequest,
    AnalyzeResponse,
    FeedbackRequest,
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
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/llm/status")
def llm_status() -> dict[str, object]:
    from .llm import _openrouter_model
    from .openrouter_client import model_name, request_timeout

    configured = bool(os.getenv("OPENROUTER_API_KEY"))
    return {
        "configured": configured,
        "model": model_name() if configured else None,
        "timeout_seconds": request_timeout(),
        "pydantic_agent_ready": _openrouter_model() is not None if configured else False,
        "practice_path": "pydantic_agent" if configured else "deterministic_fallback",
    }


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


@app.post("/api/feedback")
def feedback(request: FeedbackRequest) -> dict[str, str]:
    log_event("moment_feedback", request.model_dump())
    return {"status": "recorded"}


@app.get("/api/monitoring")
def monitoring() -> dict:
    return monitoring_summary()


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
