from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .db_models import CoachSessionRow, MessageRow, PlayerMemoryRow, SessionSummaryRow
from .embeddings import cosine_similarity, embed_text
from .monitoring import log_event


def latest_message_history(session: Session, coach_session_id: str) -> list[dict]:
    latest = session.scalar(
        select(MessageRow)
        .where(MessageRow.session_id == coach_session_id, MessageRow.role == "assistant")
        .order_by(MessageRow.sequence.desc())
    )
    return latest.message_history[-12:] if latest and latest.message_history else []


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
