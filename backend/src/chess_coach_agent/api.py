from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

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


app = FastAPI(title="Chess Coach Agent API", version="0.1.0")
agent = ChessCoachAgent()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse("http://127.0.0.1:5173/")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/sample")
def sample() -> dict[str, str]:
    return {"player": "kfctofu", "pgn": sample_pgn()}


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    log_event("analysis_requested", {"player": request.player, "max_games": request.max_games})
    return agent.import_pgn_text(request.pgn, player=request.player, max_games=request.max_games)


@app.post("/api/import", response_model=AnalyzeResponse)
async def import_games(request: ImportRequest) -> AnalyzeResponse:
    return await agent.import_platform_games(request)


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
    response = await answer_question(request.question, request.analysis)
    log_event("chat_completed", {"used_llm": response.used_llm, "retrieved_notes": len(response.retrieved_notes)})
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
