from chess_coach_agent.knowledge import retrieve_notes


def test_retrieval_finds_tactical_vision():
    notes = retrieve_notes("checks captures threats forcing tactic")
    titles = [note.title for note in notes]
    assert "Tactical Vision" in titles
