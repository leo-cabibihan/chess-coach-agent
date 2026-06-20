from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .agent import ChessCoachAgent, sample_pgn
from .llm import answer_question
from .models import AnalyzeRequest, AnalyzeResponse, ChatRequest, ChatResponse, ImportRequest
from .monitoring import log_event


app = FastAPI(title="Chess Coach Agent API", version="0.1.0")
agent = ChessCoachAgent()

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
    return agent.import_pgn_text(request.pgn, player=request.player, max_games=request.max_games)


@app.post("/api/import", response_model=AnalyzeResponse)
async def import_games(request: ImportRequest) -> AnalyzeResponse:
    return await agent.import_platform_games(request)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    log_event("chat_requested", {"has_analysis": request.analysis is not None})
    return await answer_question(request.question, request.analysis)


@app.get("/api/trends")
def trends() -> dict:
    return agent.generate_trend_summary(sample_pgn(), player="kfctofu").model_dump()
