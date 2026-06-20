from __future__ import annotations

import chess

from .engine import EngineAnalyzer, PIECE_VALUES
from .knowledge import retrieve_notes
from .models import CoachAnalysis, CriticalMoment
from .pgn import ParsedGame, phase_for_board


THEME_PRINCIPLES = {
    "loose_piece": "Loose pieces fall off. Before making a move, scan every undefended piece that your opponent can attack or capture.",
    "missed_tactic": "Forcing moves come first: checks, captures, threats, and only then quiet improving moves.",
    "king_safety": "An exposed king changes the value of every tactic. Finish development and remove back-rank weaknesses before grabbing material.",
    "opening_drift": "In the opening, repeated queen moves and undeveloped minors usually give the opponent free tempos.",
    "endgame_conversion": "In simplified positions, activity and pawn races matter more than one-move material grabs.",
}


def _castled(board: chess.Board, color: bool) -> bool:
    king = board.king(color)
    if king is None:
        return False
    return king in ({chess.G1, chess.C1} if color == chess.WHITE else {chess.G8, chess.C8})


def _undefended_attacked_value(board: chess.Board, color: bool) -> int:
    best = 0
    for square, piece in board.piece_map().items():
        if piece.color != color or piece.piece_type not in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
            continue
        if board.attackers(not color, square) and not board.attackers(color, square):
            best = max(best, PIECE_VALUES[piece.piece_type])
    return best


def _moment_text(theme: str, played: str, best: str | None, swing: float | None) -> tuple[str, str, str, str]:
    best_text = best or "the engine's candidate"
    swing_text = f" The evaluation changed by about {swing:.2f} pawns." if swing is not None else ""
    summary = f"{played} was a critical moment; {best_text} gave a cleaner plan.{swing_text}"
    what = {
        "loose_piece": f"{played} left material tactically vulnerable.",
        "missed_tactic": f"{played} missed a forcing resource in the position.",
        "king_safety": f"{played} did not address king safety or back-rank pressure.",
        "opening_drift": f"{played} spent time without improving development enough.",
        "endgame_conversion": f"{played} made the conversion harder in a simplified position.",
    }.get(theme, f"{played} changed the character of the position.")
    better = f"Look at {best_text} first and ask what threat it creates or prevents."
    drill = "Set the position on a board and list candidate checks, captures, and threats before choosing."
    return summary, what, better, drill


def analyze_parsed_game(parsed: ParsedGame, player: str = "kfctofu", max_moments: int = 4) -> CoachAnalysis:
    analyzer = EngineAnalyzer()
    player_color = chess.WHITE if parsed.metadata.player_color == "white" else chess.BLACK
    board = parsed.game.board()
    moments: list[CriticalMoment] = []
    queen_moves = 0

    for move_record, move in zip(parsed.moves, parsed.game.mainline_moves(), strict=False):
        before = board.copy(stack=False)
        mover = before.turn
        played_san = before.san(move)
        before_line = analyzer.analyse(before, player_color)
        best_san = before.san(before_line.best_move) if before_line.best_move in before.legal_moves else None
        board.push(move)
        after = board.copy(stack=False)
        after_line = analyzer.analyse(after, player_color)

        if mover != player_color:
            continue

        swing = None
        if before_line.score_cp is not None and after_line.score_cp is not None:
            swing = (before_line.score_cp - after_line.score_cp) / 100

        theme = ""
        severity = 0.0
        moving_piece = before.piece_at(move.from_square)
        loose_value = _undefended_attacked_value(after, player_color)
        if loose_value >= 300:
            theme = "loose_piece"
            severity = loose_value / 100
        if swing is not None and swing >= 1.2 and not theme:
            theme = "missed_tactic"
            severity = max(severity, swing)
        if board.fullmove_number <= 12 and moving_piece and moving_piece.piece_type == chess.QUEEN:
            queen_moves += 1
            if queen_moves >= 2 and not theme:
                theme = "opening_drift"
                severity = 2.0 + queen_moves
        if before.fullmove_number >= 10 and not _castled(after, player_color) and not theme:
            theme = "king_safety"
            severity = 2.0
        if phase_for_board(after) == "endgame" and swing is not None and swing >= 0.8 and not theme:
            theme = "endgame_conversion"
            severity = swing
        if not theme:
            continue

        fen_best = None
        if before_line.best_move in before.legal_moves:
            best_board = before.copy(stack=False)
            best_board.push(before_line.best_move)
            fen_best = best_board.fen()
        summary, what, better, drill = _moment_text(theme, played_san, best_san, swing)
        moments.append(
            CriticalMoment(
                id=f"{parsed.game_id}-{move_record.ply}",
                game_id=parsed.game_id,
                ply=move_record.ply,
                move_number=move_record.move_number,
                phase=phase_for_board(before),  # type: ignore[arg-type]
                theme=theme,
                played_san=played_san,
                best_san=best_san,
                fen_before=before.fen(),
                fen_after=after.fen(),
                fen_best=fen_best,
                eval_before=before_line.score_cp / 100 if before_line.score_cp is not None else None,
                eval_after=after_line.score_cp / 100 if after_line.score_cp is not None else None,
                eval_swing=swing,
                severity=round(severity, 2),
                summary=summary,
                what_happened=what,
                better_plan=better,
                principle=THEME_PRINCIPLES.get(theme, THEME_PRINCIPLES["missed_tactic"]),
                drill_prompt=drill,
            )
        )

    moments = sorted(moments, key=lambda m: m.severity, reverse=True)[:max_moments]
    if not moments and parsed.moves:
        first_player = next((m for m in parsed.moves if m.is_player_move), parsed.moves[0])
        moments.append(
            CriticalMoment(
                id=f"{parsed.game_id}-baseline",
                game_id=parsed.game_id,
                ply=first_player.ply,
                move_number=first_player.move_number,
                phase="opening",
                theme="missed_tactic",
                played_san=first_player.san,
                best_san=None,
                fen_before=first_player.fen_before,
                fen_after=first_player.fen_after,
                severity=1.0,
                summary="No major tactical collapse was found, so this is a baseline candidate moment.",
                what_happened="Use this position to practice candidate move discipline.",
                better_plan="List checks, captures, and threats before evaluating quiet moves.",
                principle=THEME_PRINCIPLES["missed_tactic"],
                drill_prompt="Spend three minutes finding all legal checks and captures.",
            )
        )
    themes = ", ".join(sorted({m.theme.replace("_", " ") for m in moments}))
    notes = retrieve_notes(themes, top_k=3)
    training_plan = [
        f"Replay {len(moments)} critical positions without moving pieces, then write three candidate moves.",
        "For each loss, mark whether the mistake was tactical, positional, or time-management related.",
        "Do a daily five-position drill from your own games before playing new blitz games.",
    ]
    return CoachAnalysis(
        game=parsed.metadata,
        moves=parsed.moves,
        moments=moments,
        summary=f"Found {len(moments)} coachable moments. Main themes: {themes or 'candidate move discipline'}.",
        training_plan=training_plan,
        retrieval_notes=[f"{n.title}: {n.snippet}" for n in notes],
    )
