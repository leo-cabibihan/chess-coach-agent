from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .db_models import (
    CoachSessionRow,
    CriticalMomentRow,
    GameRow,
    MessageRow,
    PlayerMemoryRow,
    SessionSummaryRow,
)
from .embeddings import cosine_similarity, embed_text
from .monitoring import log_event


def latest_message_history(session: Session, coach_session_id: str) -> list[dict]:
    recent = session.scalars(
        select(MessageRow)
        .where(MessageRow.session_id == coach_session_id, MessageRow.role == "assistant")
        .order_by(MessageRow.sequence.desc())
        .limit(6)
    ).all()
    latest = next((item for item in recent if item.message_history), None)
    return latest.message_history[-12:] if latest else []


def memory_context(session: Session, coach_session: CoachSessionRow, query: str) -> str:
    memory = session.get(PlayerMemoryRow, coach_session.player_id)
    lines = []
    if memory:
        lines.extend(
            [
                f"Recurring themes: {memory.recurring_themes or 'not enough data'}",
                f"Quiz accuracy: {memory.quiz_accuracy or 'no attempts yet'}",
                f"Due positions: {memory.due_positions}; mastered positions: {memory.mastered_positions}",
            ]
        )
    if coach_session.summary:
        lines.append(f"Current session summary: {coach_session.summary}")

    query_vector = embed_text(query)
    older = session.scalars(
        select(SessionSummaryRow).where(
            SessionSummaryRow.player_id == coach_session.player_id,
            SessionSummaryRow.session_id != coach_session.id,
        )
    ).all()
    ranked = sorted(
        (
            (cosine_similarity(query_vector, item.embedding or []), item.summary)
            for item in older
        ),
        reverse=True,
    )
    relevant = [summary for score, summary in ranked[:3] if score >= 0.65]
    log_event(
        "memory_retrieved",
        {
            "player_id": coach_session.player_id,
            "session_id": coach_session.id,
            "candidate_count": len(older),
            "retrieved_count": len(relevant),
        },
    )
    if relevant:
        lines.append("Relevant earlier coaching memories: " + " | ".join(relevant))
    return "\n".join(lines)


def game_evidence_context(
    session: Session, coach_session: CoachSessionRow, query: str, limit: int = 5
) -> tuple[str, int]:
    theme_terms = {
        "loose_piece": ("loose", "hanging", "undefended", "piece"),
        "missed_tactic": ("tactic", "forcing", "check", "capture", "fork", "pin"),
        "king_safety": ("king", "castle", "mate", "back rank"),
        "opening_drift": ("opening", "develop", "queen", "tempo"),
        "endgame_conversion": ("endgame", "convert", "pawn", "simplif"),
    }
    lowered = query.lower()
    requested = {
        theme
        for theme, terms in theme_terms.items()
        if any(term in lowered for term in terms)
    }
    rows = session.execute(
        select(CriticalMomentRow, GameRow)
        .join(GameRow, CriticalMomentRow.game_id == GameRow.id)
        .where(GameRow.player_id == coach_session.player_id)
    ).all()
    ranked = sorted(
        rows,
        key=lambda pair: (
            pair[0].theme in requested,
            pair[1].player_result == "loss",
            pair[0].severity,
            pair[1].played_at,
        ),
        reverse=True,
    )[:limit]
    log_event(
        "game_evidence_retrieved",
        {
            "player_id": coach_session.player_id,
            "session_id": coach_session.id,
            "candidate_count": len(rows),
            "retrieved_count": len(ranked),
            "themes": sorted(requested),
        },
    )
    if not ranked:
        return "No analyzed game positions are stored for this player yet.", 0
    lines = ["Relevant analyzed game positions:"]
    for moment, game in ranked:
        opponent = game.black if game.player_color == "white" else game.white
        lines.append(
            f"- Game {game.external_game_id} vs {opponent} ({game.player_result}, {game.played_at}), "
            f"move {moment.move_number}: played {moment.played_san}, engine candidate "
            f"{moment.best_san or 'unavailable'}, theme {moment.theme}, severity "
            f"{moment.severity:.2f}, FEN {moment.fen_before}"
        )
    return "\n".join(lines), len(ranked)


def summarize_if_needed(session: Session, coach_session_id: str) -> SessionSummaryRow | None:
    coach_session = session.get(CoachSessionRow, coach_session_id)
    if coach_session is None:
        return None
    message_count = session.scalar(
        select(func.count(MessageRow.id)).where(MessageRow.session_id == coach_session_id)
    ) or 0
    previous = session.scalar(
        select(SessionSummaryRow)
        .where(SessionSummaryRow.session_id == coach_session_id)
        .order_by(SessionSummaryRow.through_sequence.desc())
    )
    if message_count < 12 and coach_session.accumulated_tokens < 8000:
        return None
    if previous and previous.through_sequence >= message_count - 2:
        return None
    messages = session.scalars(
        select(MessageRow)
        .where(MessageRow.session_id == coach_session_id)
        .order_by(MessageRow.sequence)
    ).all()
    compact = " ".join(
        f"{item.role}: {item.content[:320].replace(chr(10), ' ')}" for item in messages[-12:]
    )[:2200]
    summary_text = f"Focus: {coach_session.focus_theme}. {compact}"
    row = SessionSummaryRow(
        session_id=coach_session.id,
        player_id=coach_session.player_id,
        through_sequence=messages[-1].sequence,
        summary=summary_text,
        embedding=embed_text(summary_text),
    )
    session.add(row)
    coach_session.summary = summary_text
    coach_session.accumulated_tokens = 0
    session.flush()
    return row
