from __future__ import annotations

import math

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

ANALYSIS_VERSION = "lichess-win-chance-v1"


def winning_chances(score_cp: int) -> float:
    """Map a player-POV engine score to Lichess-style winning chances [-1, 1]."""
    cp = max(-1000, min(1000, score_cp))
    return 2 / (1 + math.exp(-0.00368208 * cp)) - 1


def classify_win_chance_loss(loss: float) -> str | None:
    if loss >= 0.30:
        return "blunder"
    if loss >= 0.20:
        return "mistake"
    if loss >= 0.10:
        return "inaccuracy"
    return None


def move_accuracy(win_probability_loss: float) -> float:
    win_percent_loss = max(0.0, win_probability_loss * 50)
    raw = 103.1668100711649 * math.exp(-0.04354415386753951 * win_percent_loss)
    return max(0.0, min(100.0, raw - 3.166924740191411 + 1))


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


def _king_danger(board: chess.Board, color: bool) -> int:
    king = board.king(color)
    if king is None:
        return 0
    zone = chess.SquareSet(chess.BB_KING_ATTACKS[king] | chess.BB_SQUARES[king])
    return sum(bool(board.attackers(not color, square)) for square in zone)


def _moment_text(
    theme: str,
    judgment: str,
    played: str,
    best: str | None,
    win_percent_loss: float,
) -> tuple[str, str, str, str]:
    best_text = best or "the engine's candidate"
    summary = (
        f"{played} was a {judgment}; {best_text} preserved about "
        f"{win_percent_loss:.1f} more percentage points of winning chances."
    )
    what = {
        "loose_piece": f"{played} left material tactically vulnerable.",
        "missed_tactic": f"{played} missed a forcing resource in the position.",
        "king_safety": f"{played} did not address king safety or back-rank pressure.",
        "opening_drift": (
            f"{played} continued an early queen detour. Repeated queen moves gave away development "
            "tempi and delayed king safety."
        ),
        "endgame_conversion": f"{played} made the conversion harder in a simplified position.",
    }.get(theme, f"{played} changed the character of the position.")
    better = {
        "opening_drift": (
            f"Prefer {best_text} and compare developed minor pieces before moving the queen again. "
            "Choose the move that brings you closer to castling."
        ),
        "loose_piece": f"Look at {best_text}, then count attackers and defenders on every rook, bishop, knight, and queen.",
    }.get(theme, f"Look at {best_text} first and ask what threat it creates or prevents.")
    drill = {
        "opening_drift": (
            "Replay the first ten moves and mark every queen move, developed minor piece, and missed "
            "chance to castle. Find a development move for each unnecessary queen tempo."
        ),
        "loose_piece": (
            "Set the position on a board, identify every attacked and undefended piece, then list checks, "
            "captures, and threats."
        ),
    }.get(theme, "Set the position on a board and list candidate checks, captures, and threats before choosing.")
    return summary, what, better, drill


def analyze_parsed_game(
    parsed: ParsedGame,
    player: str = "kfctofu",
    max_moments: int | None = None,
) -> CoachAnalysis:
    analyzer = EngineAnalyzer()
    player_color = chess.WHITE if parsed.metadata.player_color == "white" else chess.BLACK
    board = parsed.game.board()
    moments: list[CriticalMoment] = []
    queen_moves = 0

    try:
        for move_record, move in zip(parsed.moves, parsed.game.mainline_moves(), strict=False):
            before = board.copy(stack=False)
            mover = before.turn
            played_san = before.san(move)
            if mover != player_color:
                board.push(move)
                continue

            moving_piece = before.piece_at(move.from_square)
            if moving_piece and moving_piece.piece_type == chess.QUEEN:
                queen_moves += 1

            before_line = analyzer.analyse(before, player_color)
            best_san = (
                before.san(before_line.best_move)
                if before_line.best_move in before.legal_moves
                else None
            )
            board.push(move)
            after = board.copy(stack=False)
            after_line = analyzer.analyse(after, player_color)

            swing = None
            chance_loss = None
            judgment = None
            if before_line.score_cp is not None and after_line.score_cp is not None:
                swing = (before_line.score_cp - after_line.score_cp) / 100
                chance_loss = max(
                    0.0,
                    winning_chances(before_line.score_cp)
                    - winning_chances(after_line.score_cp),
                )
                judgment = classify_win_chance_loss(chance_loss)

            if before_line.best_move == move or judgment is None or chance_loss is None:
                continue

            theme = "missed_tactic"
            loose_before = _undefended_attacked_value(before, player_color)
            loose_after = _undefended_attacked_value(after, player_color)
            if loose_after >= 300 and loose_after > loose_before:
                theme = "loose_piece"
            elif (
                board.fullmove_number <= 12
                and moving_piece
                and moving_piece.piece_type == chess.QUEEN
            ):
                if queen_moves >= 2:
                    theme = "opening_drift"
            elif (
                before.fullmove_number >= 10
                and not _castled(after, player_color)
                and _king_danger(after, player_color) > _king_danger(before, player_color)
            ):
                theme = "king_safety"
            elif phase_for_board(after) == "endgame":
                theme = "endgame_conversion"

            fen_best = None
            if before_line.best_move in before.legal_moves:
                best_board = before.copy(stack=False)
                best_board.push(before_line.best_move)
                fen_best = best_board.fen()
            win_percent_loss = chance_loss * 50
            summary, what, better, drill = _moment_text(
                theme, judgment, played_san, best_san, win_percent_loss
            )
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
                    severity=round(win_percent_loss, 2),
                    judgment=judgment,
                    win_probability_loss=round(win_percent_loss, 2),
                    move_accuracy=round(move_accuracy(chance_loss), 1),
                    trainable=judgment in ("mistake", "blunder"),
                    summary=summary,
                    what_happened=what,
                    better_plan=better,
                    principle=THEME_PRINCIPLES.get(theme, THEME_PRINCIPLES["missed_tactic"]),
                    drill_prompt=drill,
                )
            )
    finally:
        analyzer.close()

    moments = sorted(moments, key=lambda m: m.ply)
    if max_moments is not None:
        moments = sorted(moments, key=lambda m: m.severity, reverse=True)[:max_moments]
        moments.sort(key=lambda m: m.ply)
    themes = ", ".join(sorted({m.theme.replace("_", " ") for m in moments}))
    notes = retrieve_notes(themes, top_k=3)
    trainable_count = sum(moment.trainable for moment in moments)
    training_plan = (
        [
            f"Replay the {trainable_count} mistake/blunder positions without moving pieces, then write three candidate moves.",
            "For each loss, mark whether the mistake was tactical, positional, or time-management related.",
            "Do a daily five-position drill from your own games before playing new blitz games.",
        ]
        if moments
        else [
            "No move crossed the inaccuracy threshold in this game.",
            "Review the opening and endgame plans without manufacturing a tactical drill.",
        ]
    )
    return CoachAnalysis(
        game=parsed.metadata,
        moves=parsed.moves,
        moments=moments,
        summary=f"Found {len(moments)} coachable moments. Main themes: {themes or 'candidate move discipline'}.",
        training_plan=training_plan,
        retrieval_notes=[ANALYSIS_VERSION, *[f"{n.title}: {n.snippet}" for n in notes]],
    )
