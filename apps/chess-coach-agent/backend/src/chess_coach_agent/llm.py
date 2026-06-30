from __future__ import annotations

import os
from dataclasses import dataclass, field
from textwrap import dedent
from typing import Any

import chess
import logfire
from .env_bootstrap import load_project_env  # noqa: F401
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from .engine import EngineAnalyzer
from .knowledge import retrieve_notes
from .models import CoachAnalysis, CoachPanel, CoachingOutput
from .coach_tools import (
    build_training_session,
    compare_moves,
    evaluate_candidate_move,
    generate_position_quiz,
    inspect_game,
    inspect_player_moments,
    rank_practice_moments,
    write_quiz_copy,
)


from .openrouter_client import OPENROUTER_BASE_URL, complete_with_openrouter
logfire.configure(
    service_name="chess-coach-agent",
    send_to_logfire="if-token-present",
    console=False,
)
logfire.instrument_pydantic_ai()


@dataclass
class CoachDependencies:
    analysis: CoachAnalysis | None = None
    player_id: str | None = None
    platform: str | None = None
    username: str | None = None
    session_id: str | None = None
    panel: CoachPanel | None = None
    plan_id: str | None = None
    practice_theme: str | None = None
    practice_position_count: int = 5
    ranked_moment_ids: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    retrieved_titles: list[str] = field(default_factory=list)

    def record(self, tool_name: str) -> None:
        self.tools_used.append(tool_name)


def _model_name() -> str:
    from .openrouter_client import model_name

    return model_name()


def _openrouter_model() -> OpenAIChatModel | None:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return None
    provider = OpenAIProvider(base_url=OPENROUTER_BASE_URL, api_key=api_key)
    return OpenAIChatModel(_model_name(), provider=provider)  # type: ignore[arg-type]


def search_chess_principles(ctx: RunContext[CoachDependencies], query: str) -> list[dict[str, Any]]:
    """Search the evaluated chess knowledge base for principles relevant to the question."""
    ctx.deps.record("search_chess_principles")
    notes = retrieve_notes(query, top_k=3)
    ctx.deps.retrieved_titles.extend(note.title for note in notes)
    return [
        {"title": note.title, "snippet": note.snippet, "retrieval_score": note.score}
        for note in notes
    ]


def inspect_critical_moments(ctx: RunContext[CoachDependencies]) -> list[dict[str, Any]]:
    """Return grounded engine and heuristic facts from the current or stored game."""
    ctx.deps.record("inspect_critical_moments")
    if not ctx.deps.analysis and ctx.deps.platform and ctx.deps.username:
        return inspect_player_moments(ctx)
    if not ctx.deps.analysis:
        return []
    return [
        {
            "move_number": moment.move_number,
            "phase": moment.phase,
            "theme": moment.theme,
            "played_move": moment.played_san,
            "engine_candidate": moment.best_san,
            "evaluation_swing": moment.eval_swing,
            "principle": moment.principle,
        }
        for moment in ctx.deps.analysis.moments[:4]
    ]


def inspect_position(ctx: RunContext[CoachDependencies], fen: str) -> dict[str, Any]:
    """Inspect a legal FEN with Stockfish and list immediate forcing moves."""
    ctx.deps.record("inspect_position")
    try:
        board = chess.Board(fen)
    except ValueError:
        return {"error": "The supplied FEN is invalid."}

    analyzer = EngineAnalyzer()
    try:
        line = analyzer.analyse(board, board.turn)
    finally:
        analyzer.close()
    best_move = board.san(line.best_move) if line.best_move in board.legal_moves else None
    checks = [board.san(move) for move in board.legal_moves if board.gives_check(move)][:8]
    captures = [board.san(move) for move in board.legal_moves if board.is_capture(move)][:8]
    return {
        "side_to_move": "white" if board.turn == chess.WHITE else "black",
        "best_move": best_move,
        "evaluation_pawns": line.score_cp / 100 if line.score_cp is not None else None,
        "checks": checks,
        "captures": captures,
    }


def build_training_drill(ctx: RunContext[CoachDependencies], theme: str = "") -> dict[str, str]:
    """Build a concrete drill from the dominant weakness in the current game."""
    ctx.deps.record("build_training_drill")
    moment = ctx.deps.analysis.moments[0] if ctx.deps.analysis and ctx.deps.analysis.moments else None
    selected_theme = theme or (moment.theme if moment else "candidate_move_discipline")
    prompt = (
        moment.drill_prompt
        if moment
        else "Solve five positions and write every check, capture, and threat before moving."
    )
    return {"theme": selected_theme, "exercise": prompt}


COACH_INSTRUCTIONS = dedent(
    """
    You are a precise chess improvement coach. Relevant player memory and game positions may
    already be included in the verified context. Use tools only when the question needs evidence
    not already present; do not call tools merely to satisfy a quota.
    Treat engine evaluations, legal moves, and supplied game facts as evidence; never invent a
    variation or claim a move is forced without support. Separate what the player did from the
    reusable lesson.     Give one manageable drill. When the user asks to practice, inspect stored moments, rank them by weakness,
    create a training session from stored games, then write quiz prompts and hints.
    Use saved-game tools instead of inventing positions. Return the requested structured coaching object.
    """
).strip()


def create_coach_agent(model: Any = None) -> Agent[CoachDependencies, CoachingOutput]:
    selected_model = model if model is not None else _openrouter_model()
    return Agent(
        selected_model,
        deps_type=CoachDependencies,
        output_type=CoachingOutput,
        instructions=COACH_INSTRUCTIONS,
        tools=[
            search_chess_principles,
            inspect_critical_moments,
            inspect_player_moments,
            inspect_position,
            build_training_drill,
            inspect_game,
            compare_moves,
            rank_practice_moments,
            generate_position_quiz,
            evaluate_candidate_move,
            build_training_session,
            write_quiz_copy,
        ],
        retries=1,
    )


__all__ = ["complete_with_openrouter", "create_coach_agent", "CoachDependencies"]
