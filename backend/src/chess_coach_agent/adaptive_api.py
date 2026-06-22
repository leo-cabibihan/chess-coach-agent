from __future__ import annotations

import json
import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from .db import session_scope
from .db_models import CoachSessionRow, CriticalMomentRow, GameRow, MessageRow, PlayerRow, StreamEventRow
from .llm import answer_question
from .memory import latest_message_history, memory_context, summarize_if_needed
from .models import (
    BoardPanel,
    AnalyzeResponse,
    CoachMessageAccepted,
    CoachMessageCreate,
    CoachSessionCreate,
    CoachSessionView,
    EvaluationPanel,
    PlayerProfile,
    ProgressSummary,
    QuizAttemptCreate,
    TrainingSessionCreate,
    TrainingSessionView,
)
from .monitoring import log_event
from .repositories import (
    add_message,
    add_stream_event,
    create_coach_session,
    get_or_create_player,
    load_analyses,
    player_profile,
    progress_summary,
    session_view,
    training_session_view,
)
from .training import build_training_session, evaluate_attempt, quiz_panel


router = APIRouter(prefix="/api")


@router.get("/games/{platform}/{username}", response_model=AnalyzeResponse)
def get_analyzed_games(platform: str, username: str) -> AnalyzeResponse:
    with session_scope() as session:
        return load_analyses(session, platform, username)


@router.get("/players/{platform}/{username}", response_model=PlayerProfile)
def get_player(platform: str, username: str) -> PlayerProfile:
    with session_scope() as session:
        player = get_or_create_player(session, platform, username)
        return player_profile(session, player)


@router.post("/coach/sessions", response_model=CoachSessionView)
def start_coach_session(request: CoachSessionCreate) -> CoachSessionView:
    with session_scope() as session:
        row = create_coach_session(session, request.platform, request.username, request.focus_theme)
        view = session_view(session, row.id)
        if view is None:
            raise HTTPException(500, "Coach session could not be created")
        log_event("coach_session_started", {"session_id": row.id, "player_id": row.player_id})
        return view


@router.get("/coach/sessions/{session_id}", response_model=CoachSessionView)
def get_coach_session(session_id: str) -> CoachSessionView:
    with session_scope() as session:
        view = session_view(session, session_id)
        if view is None:
            raise HTTPException(404, "Coach session not found")
        return view


def _default_panel(session, coach_session: CoachSessionRow, content: str):
    lowered = content.lower()
    player = session.get(PlayerRow, coach_session.player_id)
    if player and any(word in lowered for word in ("quiz", "practice", "train", "drill")):
        plan = build_training_session(
            session, player.platform, player.username, coach_session.focus_theme, 5
        )
        return quiz_panel(session, plan.id)
    moment = session.scalar(
        select(CriticalMomentRow)
        .join(GameRow, CriticalMomentRow.game_id == GameRow.id)
        .where(GameRow.player_id == coach_session.player_id)
        .order_by(CriticalMomentRow.severity.desc())
    )
    if moment:
        return BoardPanel(
            fen=moment.fen_before,
            title=f"Move {moment.move_number}: {moment.theme.replace('_', ' ')}",
            description=f"Played {moment.played_san}; engine candidate {moment.best_san or 'unavailable'}.",
        )
    return None


async def _process_coach_message(
    session_id: str,
    assistant_id: str,
    content: str,
    history: list[dict],
    context: str,
    player_data: tuple[str, str, str],
) -> None:
    try:
        response = await answer_question(
            content,
            None,
            player_id=player_data[0],
            platform=player_data[1],
            username=player_data[2],
            session_id=session_id,
            message_history=history,
            memory_context=context,
        )
        with session_scope() as session:
            coach_session = session.get(CoachSessionRow, session_id)
            assistant = session.get(MessageRow, assistant_id)
            if coach_session is None or assistant is None:
                return
            assistant.content = response.answer
            assistant.message_history = response.message_history
            assistant.trace_id = response.trace_id
            for tool in response.tools_used:
                add_stream_event(session, assistant.id, "tool_started", {"tool": tool})
                add_stream_event(session, assistant.id, "tool_completed", {"tool": tool})
            for index in range(0, len(response.answer), 120):
                add_stream_event(
                    session,
                    assistant.id,
                    "text_delta",
                    {"text": response.answer[index : index + 120]},
                )
            panel = response.panel or None
            if panel is None:
                fallback_panel = _default_panel(session, coach_session, content)
                panel = fallback_panel.model_dump(mode="json") if fallback_panel else None
            if panel:
                add_stream_event(session, assistant.id, "panel_ready", panel)
            if response.usage:
                add_stream_event(
                    session, assistant.id, "usage", response.usage.model_dump(mode="json")
                )
                coach_session.accumulated_tokens += response.usage.total_tokens
            add_stream_event(
                session,
                assistant.id,
                "complete",
                {
                    "message_id": assistant.id,
                    "trace_id": response.trace_id,
                    "used_llm": response.used_llm,
                },
            )
            summarize_if_needed(session, session_id)
            log_event(
                "coach_turn_completed",
                {
                    "session_id": session_id,
                    "message_id": assistant.id,
                    "tools_used": response.tools_used,
                    "used_llm": response.used_llm,
                },
            )
    except Exception as exc:
        with session_scope() as session:
            if session.get(MessageRow, assistant_id):
                add_stream_event(session, assistant_id, "error", {"message": str(exc)})
                add_stream_event(session, assistant_id, "complete", {"message_id": assistant_id})
        log_event("stream_failed", {"session_id": session_id, "error": str(exc)})


@router.post("/coach/sessions/{session_id}/messages", response_model=CoachMessageAccepted)
async def create_coach_message(
    session_id: str,
    request: CoachMessageCreate,
    background_tasks: BackgroundTasks,
) -> CoachMessageAccepted:
    with session_scope() as session:
        coach_session = session.get(CoachSessionRow, session_id)
        if coach_session is None:
            raise HTTPException(404, "Coach session not found")
        player = session.get(PlayerRow, coach_session.player_id)
        if player is None:
            raise HTTPException(404, "Player not found")
        add_message(session, session_id, "user", request.content)
        assistant = add_message(session, session_id, "assistant", "")
        add_stream_event(session, assistant.id, "tool_started", {"tool": "coach_planning"})
        history = latest_message_history(session, session_id)
        context = memory_context(session, coach_session, request.content)
        player_data = (player.id, player.platform, player.username)

    background_tasks.add_task(
        _process_coach_message,
        session_id,
        assistant.id,
        request.content,
        history,
        context,
        player_data,
    )
    return CoachMessageAccepted(message_id=assistant.id, session_id=session_id)


@router.get("/coach/sessions/{session_id}/stream")
async def stream_coach_message(
    session_id: str, message_id: str, request: Request
) -> StreamingResponse:
    try:
        after = int(request.headers.get("last-event-id", "0"))
    except ValueError:
        after = 0

    async def event_iterator() -> AsyncIterator[str]:
        last_sequence = after
        for _ in range(300):
            if await request.is_disconnected():
                return
            with session_scope() as session:
                message = session.get(MessageRow, message_id)
                if message is None or message.session_id != session_id:
                    yield "event: error\ndata: {\"message\":\"Message not found\"}\n\n"
                    return
                events = session.scalars(
                    select(StreamEventRow)
                    .where(
                        StreamEventRow.message_id == message_id,
                        StreamEventRow.sequence > last_sequence,
                    )
                    .order_by(StreamEventRow.sequence)
                ).all()
                for event in events:
                    last_sequence = event.sequence
                    yield (
                        f"id: {event.sequence}\n"
                        f"event: {event.event_type}\n"
                        f"data: {json.dumps(event.payload, default=str)}\n\n"
                    )
                    if event.event_type == "complete":
                        return
            await asyncio.sleep(0.2)
        log_event("stream_failed", {"session_id": session_id, "reason": "stream_timeout"})
        yield "event: error\ndata: {\"message\":\"Coach turn timed out\"}\n\n"

    return StreamingResponse(event_iterator(), media_type="text/event-stream")


@router.post("/training/sessions", response_model=TrainingSessionView)
def create_training_session(request: TrainingSessionCreate) -> TrainingSessionView:
    with session_scope() as session:
        plan = build_training_session(
            session,
            request.platform,
            request.username,
            request.theme,
            request.position_count,
        )
        view = training_session_view(session, plan.id)
        if view is None:
            raise HTTPException(500, "Training session could not be created")
        log_event(
            "training_session_created",
            {"training_session_id": plan.id, "positions": len(view.positions), "difficulty": plan.difficulty},
        )
        return view


@router.get("/training/sessions/{training_session_id}", response_model=TrainingSessionView)
def get_training_session(training_session_id: str) -> TrainingSessionView:
    with session_scope() as session:
        view = training_session_view(session, training_session_id)
        if view is None:
            raise HTTPException(404, "Training session not found")
        return view


@router.post(
    "/training/sessions/{training_session_id}/attempts",
    response_model=EvaluationPanel,
)
def submit_training_attempt(
    training_session_id: str, request: QuizAttemptCreate
) -> EvaluationPanel:
    with session_scope() as session:
        view = training_session_view(session, training_session_id)
        if view is None or request.position_id not in {item.id for item in view.positions}:
            raise HTTPException(404, "Training position not found in this session")
        try:
            result = evaluate_attempt(
                session,
                request.position_id,
                request.move,
                request.hints_used,
                request.elapsed_ms,
            )
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        log_event(
            "quiz_attempted",
            {
                "training_session_id": training_session_id,
                "position_id": request.position_id,
                "correct": result.correct,
                "legal": result.legal,
                "hints_used": request.hints_used,
            },
        )
        return result


@router.get("/progress/{platform}/{username}", response_model=ProgressSummary)
def get_progress(platform: str, username: str) -> ProgressSummary:
    with session_scope() as session:
        return progress_summary(session, platform, username)
