from chess_coach_agent.agent import ChessCoachAgent, sample_pgn


def test_agent_returns_critical_moments_for_sample():
    response = ChessCoachAgent().import_pgn_text(sample_pgn(), player="kfctofu", max_games=1)
    assert response.analyses
    analysis = response.analyses[0]
    assert analysis.moments
    assert analysis.training_plan
    assert analysis.moves
