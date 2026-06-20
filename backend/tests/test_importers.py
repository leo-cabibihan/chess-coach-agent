from chess_coach_agent.agent import sample_pgn
from chess_coach_agent.importers import preview_pgn_games


def test_preview_pgn_games_returns_selectable_metadata_and_unique_ids():
    games = preview_pgn_games(sample_pgn(), "kfctofu", "chess.com", max_games=8)
    assert len(games) == 8
    assert len({game.game_id for game in games}) == 8
    assert games[0].opponent
    assert games[0].player_result in {"win", "loss", "draw", "unknown"}
    assert "[Event " in games[0].pgn
