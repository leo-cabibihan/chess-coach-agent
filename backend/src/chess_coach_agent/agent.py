from __future__ import annotations

from pathlib import Path

from .analysis import analyze_parsed_game
from .models import AnalyzeResponse
from .monitoring import log_event
from .pgn import parse_pgn_text


class ChessCoachAgent:
    """Parse PGNs and run the deterministic game-analysis pipeline."""

    def import_pgn_text(self, pgn: str, player: str, max_games: int = 1) -> AnalyzeResponse:
        parsed = parse_pgn_text(pgn, player=player, max_games=max_games)
        analyses = [analyze_parsed_game(game, player=player) for game in parsed]
        themes = [moment.theme for analysis in analyses for moment in analysis.moments]
        log_event(
            "analysis_completed",
            {"player": player, "games": len(analyses), "moments": len(themes), "themes": themes},
        )
        return AnalyzeResponse(analyses=analyses)

def sample_pgn() -> str:
    return (Path(__file__).resolve().parents[2] / "data" / "sample_games" / "kfctofu_sample.pgn").read_text(
        encoding="utf-8"
    )
