from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from textwrap import dedent
from typing import Any

import chess
import httpx
import logfire
from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from .engine import EngineAnalyzer
from .knowledge import retrieve_notes
from .models import ChatResponse, CoachAnalysis, CoachingOutput, ModelUsage


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_URL = f"{OPENROUTER_BASE_URL}/chat/completions"

load_dotenv()
logfire.configure(
    service_name="chess-coach-agent",
    send_to_logfire="if-token-present",
    console=False,
)
logfire.instrument_pydantic_ai()


@dataclass
class CoachDependencies:
    analysis: CoachAnalysis | None = None
    tools_used: list[str] = field(default_factory=list)
    retrieved_titles: list[str] = field(default_factory=list)

    def record(self, tool_name: str) -> None:
        self.tools_used.append(tool_name)


def _model_name() -> str:
    return os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")


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
    """Return grounded engine and heuristic facts from the currently selected game."""
    ctx.deps.record("inspect_critical_moments")
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
    You are a precise chess improvement coach. Use at least two tools before answering.
    Treat engine evaluations, legal moves, and supplied game facts as evidence; never invent a
    variation or claim a move is forced without support. Separate what the player did from the
    reusable lesson. Give one manageable drill. Return the requested structured coaching object.
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
            inspect_position,
            build_training_drill,
        ],
        retries=2,
    )


def _analysis_prompt(question: str, analysis: CoachAnalysis | None) -> str:
    if not analysis:
        context = "No analyzed game was supplied. Use retrieved principles and state that limitation."
    else:
        moments = "\n".join(
            f"- move {moment.move_number}: played {moment.played_san}; candidate "
            f"{moment.best_san or 'unknown'}; theme {moment.theme}; FEN {moment.fen_before}"
            for moment in analysis.moments[:4]
        )
        context = dedent(
            f"""
            Game: {analysis.game.white} vs {analysis.game.black}, player result {analysis.game.player_result}
            Critical moments:
            {moments}
            """
        ).strip()
    return f"Question:\n{question}\n\nVerified game context:\n{context}"


def _fallback_coaching(question: str, analysis: CoachAnalysis | None) -> tuple[CoachingOutput, list[str], list[str]]:
    notes = retrieve_notes(question, top_k=3)
    if analysis and analysis.moments:
        moment = analysis.moments[0]
        coaching = CoachingOutput(
            answer=(
                f"The biggest lesson is **{moment.theme.replace('_', ' ')}** around move "
                f"{moment.move_number}. You played {moment.played_san}; "
                f"{moment.best_san or 'the engine candidate'} was the stronger option."
            ),
            evidence=[moment.summary, moment.what_happened],
            recommended_move=moment.best_san,
            principle=moment.principle,
            drill=moment.drill_prompt,
            confidence=0.72 if moment.best_san else 0.55,
        )
        return coaching, ["inspect_critical_moments", "build_training_drill"], [note.title for note in notes]
    principle = notes[0].snippet if notes else "Start with checks, captures, and threats."
    coaching = CoachingOutput(
        answer="Analyze or select a game so I can ground the answer in your positions.",
        evidence=[principle],
        recommended_move=None,
        principle=principle,
        drill="Solve five positions and list every check, capture, and threat before choosing a move.",
        confidence=0.4,
    )
    return coaching, ["search_chess_principles", "build_training_drill"], [note.title for note in notes]


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    known_prices = {
        "minimax/minimax-m3": (0.30, 1.20),
        "openai/gpt-4o-mini": (0.15, 0.60),
    }
    default_input, default_output = known_prices.get(_model_name(), (0.0, 0.0))
    input_rate = float(os.getenv("OPENROUTER_INPUT_COST_PER_MILLION", str(default_input)))
    output_rate = float(os.getenv("OPENROUTER_OUTPUT_COST_PER_MILLION", str(default_output)))
    return round((input_tokens * input_rate + output_tokens * output_rate) / 1_000_000, 8)


async def answer_question(question: str, analysis: CoachAnalysis | None) -> ChatResponse:
    trace_id = uuid.uuid4().hex
    model = _openrouter_model()
    if model is None:
        coaching, tools_used, titles = _fallback_coaching(question, analysis)
        return ChatResponse(
            answer=coaching.answer,
            coaching=coaching,
            used_llm=False,
            tools_used=tools_used,
            retrieved_notes=titles,
            trace_id=trace_id,
        )

    deps = CoachDependencies(analysis=analysis)
    try:
        with logfire.span(
            "coach_session",
            trace_id=trace_id,
            model=_model_name(),
            has_analysis=analysis is not None,
        ):
            result = await create_coach_agent(model).run(_analysis_prompt(question, analysis), deps=deps)
        usage = result.usage
        model_usage = ModelUsage(
            model=_model_name(),
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            requests=usage.requests,
            tool_calls=usage.tool_calls,
            estimated_cost_usd=_estimate_cost(usage.input_tokens, usage.output_tokens),
        )
        return ChatResponse(
            answer=result.output.answer,
            coaching=result.output,
            used_llm=True,
            tools_used=list(dict.fromkeys(deps.tools_used)),
            retrieved_notes=list(dict.fromkeys(deps.retrieved_titles)),
            usage=model_usage,
            trace_id=trace_id,
        )
    except Exception as exc:
        logfire.warn("coach_session_failed", trace_id=trace_id, error=str(exc))
        coaching, tools_used, titles = _fallback_coaching(question, analysis)
        return ChatResponse(
            answer=coaching.answer,
            coaching=coaching,
            used_llm=False,
            tools_used=tools_used,
            retrieved_notes=titles,
            trace_id=trace_id,
        )


async def explain_with_openrouter(prompt: str) -> tuple[str, bool]:
    return await complete_with_openrouter(
        system="You are a precise chess coach. Ground every explanation in supplied evidence.",
        prompt=prompt,
        temperature=0.25,
    )


async def complete_with_openrouter(
    system: str,
    prompt: str,
    temperature: float = 0.0,
) -> tuple[str, bool]:
    """Small raw completion helper retained for the independent LLM-judge pipeline."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return "", False
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": "Chess Coach Agent",
    }
    body = {
        "model": _model_name(),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(OPENROUTER_URL, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip(), True
    except Exception:
        return "", False
