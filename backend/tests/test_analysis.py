from chess_coach_agent.agent import ChessCoachAgent, sample_pgn
from chess_coach_agent.analysis import (
    classify_win_chance_loss,
    move_accuracy,
    winning_chances,
)


def test_agent_returns_critical_moments_for_sample():
    response = ChessCoachAgent().import_pgn_text(sample_pgn(), player="kfctofu", max_games=2)
    assert len(response.analyses) == 2
    assert len({len(analysis.moments) for analysis in response.analyses}) > 1
    for analysis in response.analyses:
        assert analysis.moments
        assert analysis.training_plan
        assert analysis.moves
        assert all(moment.win_probability_loss >= 5 for moment in analysis.moments)
        assert all(
            moment.judgment in {"inaccuracy", "mistake", "blunder"}
            for moment in analysis.moments
        )


def test_lichess_style_win_chance_thresholds():
    assert classify_win_chance_loss(0.099) is None
    assert classify_win_chance_loss(0.10) == "inaccuracy"
    assert classify_win_chance_loss(0.20) == "mistake"
    assert classify_win_chance_loss(0.30) == "blunder"
    assert winning_chances(-300) < winning_chances(0) < winning_chances(300)
    assert move_accuracy(0) == 100
    assert move_accuracy(0.30) < move_accuracy(0.10)
