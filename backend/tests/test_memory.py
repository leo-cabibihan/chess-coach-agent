import uuid

from chess_coach_agent.db import init_db, session_scope
from chess_coach_agent.memory import memory_context, summarize_if_needed
from chess_coach_agent.repositories import add_message, create_coach_session


def test_session_summary_becomes_retrievable_episodic_memory():
    init_db()
    username = f"memory-{uuid.uuid4().hex}"
    with session_scope() as session:
        first = create_coach_session(session, "lichess", username, "loose_pieces")
        for index in range(12):
            role = "user" if index % 2 == 0 else "assistant"
            add_message(session, first.id, role, "Fork awareness and loose knight review.")
        summary = summarize_if_needed(session, first.id)
        assert summary is not None

        second = create_coach_session(session, "lichess", username, "loose_pieces")
        context = memory_context(session, second, summary.summary)
        assert "Relevant earlier coaching memories" in context
        assert "Fork awareness" in context
