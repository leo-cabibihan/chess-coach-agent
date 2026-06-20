from __future__ import annotations

from pathlib import Path

from .analysis import analyze_parsed_game
from .importers import fetch_chesscom_pgn, fetch_lichess_pgn
from .knowledge import retrieve_notes
from .models import AnalyzeResponse, ImportRequest, TrendSummary
from .monitoring import log_event
from .pgn import parse_pgn_text


class ChessCoachAgent:
    """Tool-using chess coach orchestrator.

    The course rubric asks for an LLM agent with multiple tools. This class keeps the tools
    explicit and testable, then lets the OpenRouter layer handle natural-language coaching
    when a key is configured.
    """

    def import_pgn_text(self, pgn: str, player: str, max_games: int = 1) -> AnalyzeResponse:
        parsed = parse_pgn_text(pgn, player=player, max_games=max_games)
        analyses = [analyze_parsed_game(game, player=player) for game in parsed]
        log_event("analysis_completed", {"player": player, "games": len(analyses)})
        return AnalyzeResponse(analyses=analyses)

    async def import_platform_games(self, request: ImportRequest) -> AnalyzeResponse:
        if request.platform == "chess.com":
            pgn = await fetch_chesscom_pgn(request.username, request.max_games)
        else:
            pgn = await fetch_lichess_pgn(request.username, request.max_games)
        log_event("games_imported", {"platform": request.platform, "username": request.username})
        return self.import_pgn_text(pgn, player=request.username, max_games=request.max_games)

    def retrieve_chess_principles(self, query: str) -> list[str]:
        return [f"{note.title}: {note.snippet}" for note in retrieve_notes(query)]

    def generate_trend_summary(self, pgn: str, player: str) -> TrendSummary:
        parsed = parse_pgn_text(pgn, player=player, max_games=200)
        record = {"win": 0, "loss": 0, "draw": 0, "unknown": 0}
        themes: dict[str, int] = {}
        recent = []
        for game in parsed:
            record[game.metadata.player_result] = record.get(game.metadata.player_result, 0) + 1
            analysis = analyze_parsed_game(game, player=player)
            for moment in analysis.moments:
                themes[moment.theme] = themes.get(moment.theme, 0) + 1
        if parsed:
            score = record.get("win", 0) + record.get("draw", 0) * 0.5
            recent.append(
                {
                    "label": "sample",
                    "games": len(parsed),
                    "score_pct": round(score / len(parsed) * 100, 1),
                    "avg_elo": None,
                }
            )
        return TrendSummary(total_games=len(parsed), record=record, themes=themes, recent=recent)


def sample_pgn() -> str:
    return (Path(__file__).resolve().parents[2] / "data" / "sample_games" / "kfctofu_sample.pgn").read_text(
        encoding="utf-8"
    )
