from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any, Literal

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
    judgment: Literal["inaccuracy", "mistake", "blunder"]
    win_probability_loss: float
    move_accuracy: float
    trainable: bool = False
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
    platform: Literal["chess.com", "lichess", "pgn"] = "pgn"


class AnalyzeResponse(BaseModel):
    analyses: list[CoachAnalysis]
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ChatRequest(BaseModel):
    question: str
    analysis: CoachAnalysis | None = None


class CoachingOutput(BaseModel):
    answer: str = Field(description="A concise, practical answer in Markdown")
    evidence: list[str] = Field(
        default_factory=list,
        description="Concrete engine, move, or retrieved-principle facts supporting the answer",
    )
    recommended_move: str | None = Field(
        default=None,
        description="A legal SAN move when the supplied analysis supports one",
    )
    principle: str = Field(description="The main reusable chess principle")
    drill: str = Field(description="A specific practice exercise based on the player's game")
    confidence: float = Field(ge=0, le=1)


class SyncGamesRequest(BaseModel):
    username: str
    platform: Literal["chess.com", "lichess"]
    max_games: int = Field(default=2000, ge=1, le=5000)


class SyncJobView(BaseModel):
    id: str
    platform: str
    username: str
    status: Literal["queued", "fetching", "analyzing", "complete", "failed"]
    total_games: int
    analyzed_games: int
    skipped_games: int
    error: str = ""
    created_at: datetime
    updated_at: datetime


class GamePreview(BaseModel):
    game_id: str
    pgn: str
    source: Literal["chess.com", "lichess"]
    white: str
    black: str
    result: str
    date: str
    time_control: str = ""
    link: str = ""
    player_color: Literal["white", "black", "unknown"]
    player_result: Literal["win", "loss", "draw", "unknown"]
    player_elo: int | None = None
    opponent: str
    opponent_elo: int | None = None


class FeedbackRequest(BaseModel):
    moment_id: str
    game_id: str
    rating: Literal["helpful", "not_helpful"]
    theme: str
    fen: str
    comment: str = ""


Platform = Literal["chess.com", "lichess", "pgn"]
Difficulty = Literal["beginner", "intermediate", "advanced"]


class PlayerProfile(BaseModel):
    id: str
    platform: Platform
    username: str
    current_rating: int | None = None
    recurring_themes: dict[str, float] = Field(default_factory=dict)
    quiz_accuracy: dict[str, float] = Field(default_factory=dict)
    mastered_positions: int = 0
    due_positions: int = 0


class BoardPanel(BaseModel):
    type: Literal["board"] = "board"
    fen: str
    title: str
    description: str = ""


class QuizPanel(BaseModel):
    type: Literal["quiz"] = "quiz"
    training_session_id: str
    position_id: str
    fen: str
    question: str
    choices: list[str] = Field(default_factory=list)
    theme: str
    difficulty: Difficulty
    hint: str | None = None


class EvaluationPanel(BaseModel):
    type: Literal["evaluation"] = "evaluation"
    position_id: str
    fen: str
    submitted_move: str
    best_move: str
    legal: bool
    correct: bool
    cp_loss: float | None = None
    explanation: str
    next_review_at: datetime


CoachPanel = Annotated[
    BoardPanel | QuizPanel | EvaluationPanel,
    Field(discriminator="type"),
]


class CoachSessionCreate(BaseModel):
    platform: Platform = "lichess"
    username: str = "kfctofu"
    focus_theme: str | None = None


class CoachMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class CoachMessageView(BaseModel):
    id: str
    sequence: int
    role: Literal["user", "assistant"]
    content: str
    trace_id: str | None = None
    created_at: datetime


class CoachSessionView(BaseModel):
    id: str
    player: PlayerProfile
    status: str
    focus_theme: str
    summary: str = ""
    messages: list[CoachMessageView] = Field(default_factory=list)
    active_panel: CoachPanel | None = None
    created_at: datetime


class CoachSessionSummaryView(BaseModel):
    id: str
    focus_theme: str
    message_count: int
    preview: str
    created_at: datetime
    updated_at: datetime


class CoachMessageAccepted(BaseModel):
    message_id: str
    session_id: str


class TrainingSessionCreate(BaseModel):
    platform: Platform = "lichess"
    username: str = "kfctofu"
    theme: str | None = None
    moment_id: str | None = None
    position_count: int = Field(default=5, ge=1, le=10)


class TrainingPositionView(BaseModel):
    id: str
    order: int
    fen: str
    choices: list[str]
    theme: str
    difficulty: Difficulty
    prompt: str = "What would you play in this position?"
    hint: str | None = None


class TrainingSessionView(BaseModel):
    id: str
    player_id: str
    focus_themes: list[str]
    difficulty: Difficulty
    status: str
    positions: list[TrainingPositionView]


class QuizAttemptCreate(BaseModel):
    position_id: str
    move: str
    hints_used: int = Field(default=0, ge=0, le=5)
    elapsed_ms: int = Field(default=0, ge=0)


class ProgressSummary(BaseModel):
    player: PlayerProfile
    total_games: int
    record: dict[str, int]
    rating_history: list[dict[str, Any]]
    theme_frequency: dict[str, int]
    quiz_accuracy: dict[str, float]
    recent_attempts: int
    transfer_score: float | None = None
