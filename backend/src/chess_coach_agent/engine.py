from __future__ import annotations

import os
import shutil
from dataclasses import dataclass

import chess
import chess.engine


PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}


@dataclass
class EngineLine:
    best_move: chess.Move | None
    score_cp: int | None


def stockfish_path() -> str | None:
    configured = os.getenv("STOCKFISH_PATH")
    if configured and os.path.exists(configured):
        return configured
    return shutil.which("stockfish")


def material_score(board: chess.Board, color: bool) -> int:
    total = 0
    for piece_type, value in PIECE_VALUES.items():
        total += len(board.pieces(piece_type, color)) * value
        total -= len(board.pieces(piece_type, not color)) * value
    return total


def simple_position_score(board: chess.Board, pov: bool) -> int:
    if board.is_checkmate():
        return -100000 if board.turn == pov else 100000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    score = material_score(board, pov)
    mobility = len(list(board.legal_moves)) if board.turn == pov else -len(list(board.legal_moves))
    return score + mobility * 3


class EngineAnalyzer:
    def __init__(self, depth: int = 9, engine_path: str | None = None) -> None:
        self.depth = depth
        self.engine_path = engine_path or stockfish_path()

    def analyse(self, board: chess.Board, pov: bool) -> EngineLine:
        if not self.engine_path:
            return EngineLine(best_move=_fallback_best_move(board), score_cp=simple_position_score(board, pov))
        try:
            with chess.engine.SimpleEngine.popen_uci(self.engine_path) as engine:
                info = engine.analyse(board, chess.engine.Limit(depth=self.depth))
                score = info["score"].pov(pov).score(mate_score=100000)
                pv = info.get("pv", [])
                return EngineLine(best_move=pv[0] if pv else None, score_cp=score)
        except Exception:
            return EngineLine(best_move=_fallback_best_move(board), score_cp=simple_position_score(board, pov))


def _fallback_best_move(board: chess.Board) -> chess.Move | None:
    best: chess.Move | None = None
    best_gain = -10_000
    for move in board.legal_moves:
        gain = 0
        if board.is_capture(move):
            victim = board.piece_at(move.to_square)
            attacker = board.piece_at(move.from_square)
            if victim and attacker:
                gain += PIECE_VALUES[victim.piece_type] - PIECE_VALUES[attacker.piece_type] // 10
        if board.gives_check(move):
            gain += 80
        if gain > best_gain:
            best_gain = gain
            best = move
    return best or next(iter(board.legal_moves), None)
