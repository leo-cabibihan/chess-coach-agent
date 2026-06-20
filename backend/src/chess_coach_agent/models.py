from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class MoveRecord(BaseModel):
    ply: int
    move_number: int
    color: Literal["white", "black"]
    san: str
    uci: str
    fen_before: str
    fen_after: str
    is_player_move: bool = False


class CriticalMoment(BaseModel):
    id: str
    game_id: str
    ply: int
    move_number: int
    phase: Literal["opening", "middlegame", "endgame"]
    theme: str
    played_san: str
    best_san: str | None = None
    fen_before: str
    fen_after: str
    fen_best: str | None = None
    eval_before: float | None = None
    eval_after: float | None = None
    eval_swing: float | None = None
    severity: float = 0
    summary: str
    what_happened: str
    better_plan: str
    principle: str
    drill_prompt: str


class GameMetadata(BaseModel):
    game_id: str
    source: str = "pgn"
    white: str
    black: str
    result: str
    date: str = "????.??.??"
    link: str = ""
    eco: str = ""
    time_control: str = ""
    player_color: Literal["white", "black", "unknown"] = "unknown"
    player_result: Literal["win", "loss", "draw", "unknown"] = "unknown"
    player_elo: int | None = None


class CoachAnalysis(BaseModel):
    game: GameMetadata
    moves: list[MoveRecord]
    moments: list[CriticalMoment]
    summary: str
    training_plan: list[str]
    retrieval_notes: list[str] = Field(default_factory=list)


class AnalyzeRequest(BaseModel):
    pgn: str
    player: str = "kfctofu"
    max_games: int = 1


class AnalyzeResponse(BaseModel):
    analyses: list[CoachAnalysis]
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ChatRequest(BaseModel):
    question: str
    analysis: CoachAnalysis | None = None


class ChatResponse(BaseModel):
    answer: str
    used_llm: bool = False
    retrieved_notes: list[str] = Field(default_factory=list)


class ImportRequest(BaseModel):
    username: str
    platform: Literal["chess.com", "lichess"]
    max_games: int = 20


class FeedbackRequest(BaseModel):
    moment_id: str
    game_id: str
    rating: Literal["helpful", "not_helpful"]
    theme: str
    fen: str
    comment: str = ""


class TrendPoint(BaseModel):
    label: str
    games: int
    score_pct: float
    avg_elo: float | None = None


class TrendSummary(BaseModel):
    total_games: int
    record: dict[str, int]
    themes: dict[str, int]
    recent: list[TrendPoint]
