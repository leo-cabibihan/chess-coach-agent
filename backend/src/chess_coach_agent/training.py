from __future__ import annotations

from datetime import UTC, datetime, timedelta

import chess
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .db_models import (
    CriticalMomentRow,
    FlashcardRow,
    GameRow,
    PlayerRow,
    QuizAttemptRow,
    ReviewScheduleRow,
    TrainingPlanRow,
    TrainingPositionRow,
)
from .engine import EngineAnalyzer
from .models import EvaluationPanel, FlashcardItem, FlashcardsPanel, QuizPanel
from .repositories import get_or_create_player, recompute_player_memory, training_session_view


def difficulty_for(session: Session, player: PlayerRow, theme: str) -> str:
    attempts = session.scalars(
        select(QuizAttemptRow)
        .join(TrainingPositionRow, QuizAttemptRow.position_id == TrainingPositionRow.id)
        .where(QuizAttemptRow.player_id == player.id, TrainingPositionRow.theme == theme)
    ).all()
    if len(attempts) >= 3:
        accuracy = sum(item.correct for item in attempts[-10:]) / min(len(attempts), 10)
        if accuracy < 0.4:
            return "beginner"
        if accuracy > 0.8:
            return "advanced"
        return "intermediate"
    rating = player.current_rating or 1400
    return "beginner" if rating < 1200 else "advanced" if rating > 1800 else "intermediate"


def _move_choices(fen: str, correct_move: str, difficulty: str) -> list[str]:
    if difficulty == "advanced":
        return []
    board = chess.Board(fen)
    choices = [correct_move]
    for move in board.legal_moves:
        san = board.san(move)
        if san != correct_move:
            choices.append(san)
        if len(choices) >= (3 if difficulty == "beginner" else 4):
            break
    return choices


def build_training_session(
    session: Session,
    platform: str,
    username: str,
    theme: str | None = None,
    position_count: int = 5,
) -> TrainingPlanRow:
    player = get_or_create_player(session, platform, username)
    moment_query = (
        select(CriticalMomentRow)
        .join(GameRow, CriticalMomentRow.game_id == GameRow.id)
        .where(GameRow.player_id == player.id, CriticalMomentRow.best_san.is_not(None))
        .order_by(CriticalMomentRow.severity.desc())
    )
    if theme:
        moment_query = moment_query.where(CriticalMomentRow.theme == theme)
    moments = session.scalars(moment_query.limit(position_count)).all()
    if not moments and theme:
        moments = session.scalars(
            select(CriticalMomentRow)
            .join(GameRow, CriticalMomentRow.game_id == GameRow.id)
            .where(GameRow.player_id == player.id, CriticalMomentRow.best_san.is_not(None))
            .order_by(CriticalMomentRow.severity.desc())
            .limit(position_count)
        ).all()
    selected_theme = theme or (moments[0].theme if moments else "candidate_move_discipline")
    difficulty = difficulty_for(session, player, selected_theme)
    plan = TrainingPlanRow(
        player_id=player.id,
        focus_themes=list(dict.fromkeys(item.theme for item in moments)) or [selected_theme],
        difficulty=difficulty,
    )
    session.add(plan)
    session.flush()
    for index, moment in enumerate(moments, start=1):
        correct = moment.best_san or ""
        session.add(
            TrainingPositionRow(
                plan_id=plan.id,
                moment_id=moment.id,
                position_order=index,
                fen=moment.fen_before,
                correct_move=correct,
                choices=_move_choices(moment.fen_before, correct, difficulty),
                theme=moment.theme,
                difficulty=difficulty,
                explanation=(moment.explanation or {}).get("what_happened", ""),
            )
        )
    session.flush()
    return plan


def quiz_panel(session: Session, plan_id: str, position_id: str | None = None) -> QuizPanel | None:
    plan_view = training_session_view(session, plan_id)
    if not plan_view or not plan_view.positions:
        return None
    position = next((item for item in plan_view.positions if item.id == position_id), plan_view.positions[0])
    hint = None
    row = session.get(TrainingPositionRow, position.id)
    if row and position.difficulty == "beginner":
        hint = f"Start with checks and captures. The engine move begins with {row.correct_move[:1]}."
    return QuizPanel(
        training_session_id=plan_id,
        position_id=position.id,
        fen=position.fen,
        question="What would you play in this position?",
        choices=position.choices,
        theme=position.theme,
        difficulty=position.difficulty,
        hint=hint,
    )


def _parse_move(board: chess.Board, submitted: str) -> chess.Move | None:
    try:
        return board.parse_san(submitted)
    except ValueError:
        try:
            move = chess.Move.from_uci(submitted)
            return move if move in board.legal_moves else None
        except ValueError:
            return None


def evaluate_attempt(
    session: Session,
    position_id: str,
    submitted_move: str,
    hints_used: int = 0,
    elapsed_ms: int = 0,
) -> EvaluationPanel:
    position = session.get(TrainingPositionRow, position_id)
    if position is None:
        raise ValueError("Training position not found")
    plan = session.get(TrainingPlanRow, position.plan_id)
    if plan is None:
        raise ValueError("Training plan not found")
    board = chess.Board(position.fen)
    move = _parse_move(board, submitted_move.strip())
    legal = move is not None
    cp_loss = None
    correct = False
    if move:
        submitted_san = board.san(move)
        correct = submitted_san == position.correct_move
        analyzer = EngineAnalyzer()
        pov = board.turn
        try:
            before = analyzer.analyse(board, pov)
            board.push(move)
            after = analyzer.analyse(board, pov)
        finally:
            analyzer.close()
        if before.score_cp is not None and after.score_cp is not None:
            cp_loss = round(max(0, before.score_cp - after.score_cp) / 100, 2)
            correct = correct or cp_loss <= 0.5

    attempt = QuizAttemptRow(
        player_id=plan.player_id,
        position_id=position.id,
        submitted_move=submitted_move,
        correct=correct,
        legal=legal,
        cp_loss=cp_loss,
        hints_used=hints_used,
        elapsed_ms=elapsed_ms,
    )
    session.add(attempt)

    schedule = session.scalar(
        select(ReviewScheduleRow).where(ReviewScheduleRow.position_id == position.id)
    )
    now = datetime.now(UTC)
    if schedule is None:
        schedule = ReviewScheduleRow(
            player_id=plan.player_id,
            position_id=position.id,
            due_at=now,
            interval_days=1,
            consecutive_successes=0,
        )
        session.add(schedule)
    if not correct:
        schedule.interval_days = 1
        schedule.consecutive_successes = 0
    elif hints_used:
        schedule.interval_days = 3
        schedule.consecutive_successes += 1
    else:
        schedule.consecutive_successes += 1
        schedule.interval_days = min(30, 7 * (2 ** max(0, schedule.consecutive_successes - 1)))
    schedule.due_at = now + timedelta(days=schedule.interval_days)
    session.flush()
    recompute_player_memory(session, plan.player_id)

    explanation = (
        f"{submitted_move} is a strong engine-approved candidate. {position.explanation}"
        if correct
        else f"The stronger move is {position.correct_move}. {position.explanation}"
    )
    if not legal:
        explanation = "That move is not legal in this position. Check the board and try again."
    return EvaluationPanel(
        position_id=position.id,
        fen=position.fen,
        submitted_move=submitted_move,
        best_move=position.correct_move,
        legal=legal,
        correct=correct,
        cp_loss=cp_loss,
        explanation=explanation,
        next_review_at=schedule.due_at,
    )


def generate_flashcards(
    session: Session, player_id: str, theme: str | None = None, limit: int = 5
) -> FlashcardsPanel:
    query = (
        select(CriticalMomentRow)
        .join(GameRow, CriticalMomentRow.game_id == GameRow.id)
        .where(GameRow.player_id == player_id)
        .order_by(CriticalMomentRow.severity.desc())
    )
    if theme:
        query = query.where(CriticalMomentRow.theme == theme)
    moments = session.scalars(query.limit(limit)).all()
    cards: list[FlashcardItem] = []
    for moment in moments:
        existing = session.scalar(
            select(FlashcardRow).where(
                FlashcardRow.player_id == player_id,
                FlashcardRow.moment_id == moment.id,
            )
        )
        if existing is None:
            existing = FlashcardRow(
                player_id=player_id,
                moment_id=moment.id,
                fen=moment.fen_before,
                prompt="What is the strongest move and the underlying principle?",
                answer=f"{moment.best_san or 'Find a forcing move'} — {(moment.explanation or {}).get('principle', moment.theme)}",
                theme=moment.theme,
            )
            session.add(existing)
            session.flush()
        cards.append(
            FlashcardItem(
                id=existing.id,
                fen=existing.fen,
                prompt=existing.prompt,
                answer=existing.answer,
                theme=existing.theme,
            )
        )
    return FlashcardsPanel(title=f"{theme or 'Personal'} review deck", cards=cards)


def attempt_count(session: Session, player_id: str) -> int:
    return session.scalar(select(func.count(QuizAttemptRow.id)).where(QuizAttemptRow.player_id == player_id)) or 0
