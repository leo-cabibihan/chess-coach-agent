from chess_coach_agent.agent import sample_pgn
from chess_coach_agent.pgn import parse_pgn_text


def test_parse_sample_pgn_extracts_moves_and_metadata():
    games = parse_pgn_text(sample_pgn(), player="kfctofu", max_games=1)
    assert len(games) == 1
    assert games[0].metadata.white
    assert games[0].metadata.black
    assert len(games[0].moves) > 10
