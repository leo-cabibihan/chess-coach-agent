from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass

import chess
import chess.pgn

from .models import GameMetadata, MoveRecord


@dataclass
class ParsedGame:
    game_id: str
    metadata: GameMetadata
    moves: list[MoveRecord]
    game: chess.pgn.Game


def _result_for_player(headers: chess.pgn.Headers, player: str) -> tuple[str, str]:
    player_l = player.lower()
    white = headers.get("White", "").lower() == player_l
    black = headers.get("Black", "").lower() == player_l
    if not white and not black:
        return "unknown", "unknown"
    result = headers.get("Result", "*")
    color = "white" if white else "black"
    if result == "1/2-1/2":
        return color, "draw"
    if (white and result == "1-0") or (black and result == "0-1"):
        return color, "win"
    if result in {"1-0", "0-1"}:
        return color, "loss"
    return color, "unknown"


def parse_pgn_text(pgn_text: str, player: str = "kfctofu", max_games: int = 20) -> list[ParsedGame]:
    handle = io.StringIO(pgn_text)
    parsed: list[ParsedGame] = []
    while len(parsed) < max_games:
        game = chess.pgn.read_game(handle)
        if game is None:
            break
        headers = game.headers
        raw_id = "|".join(
            [
                headers.get("Site", ""),
                headers.get("Link", ""),
                headers.get("Date", ""),
                headers.get("UTCTime", headers.get("StartTime", "")),
                headers.get("White", ""),
                headers.get("Black", ""),
                headers.get("Result", ""),
            ]
        )
        game_id = hashlib.sha1(raw_id.encode("utf-8")).hexdigest()[:12]
        player_color, player_result = _result_for_player(headers, player)
        elo_key = "WhiteElo" if player_color == "white" else "BlackElo"
        try:
            player_elo = int(headers.get(elo_key, ""))
        except ValueError:
            player_elo = None
        metadata = GameMetadata(
            game_id=game_id,
            source="pgn",
            white=headers.get("White", "White"),
            black=headers.get("Black", "Black"),
            result=headers.get("Result", "*"),
            date=headers.get("Date", "????.??.??"),
            link=headers.get("Link") or headers.get("Site", ""),
            eco=headers.get("ECO", ""),
            time_control=headers.get("TimeControl", ""),
            player_color=player_color,  # type: ignore[arg-type]
            player_result=player_result,  # type: ignore[arg-type]
            player_elo=player_elo,
        )
        board = game.board()
        moves: list[MoveRecord] = []
        for ply, move in enumerate(game.mainline_moves(), start=1):
            san = board.san(move)
            color = "white" if board.turn == chess.WHITE else "black"
            fen_before = board.fen()
            board.push(move)
            moves.append(
                MoveRecord(
                    ply=ply,
                    move_number=(ply + 1) // 2,
                    color=color,  # type: ignore[arg-type]
                    san=san,
                    uci=move.uci(),
                    fen_before=fen_before,
                    fen_after=board.fen(),
                    is_player_move=color == player_color,
                )
            )
        parsed.append(ParsedGame(game_id=game_id, metadata=metadata, moves=moves, game=game))
    return parsed


def phase_for_board(board: chess.Board) -> str:
    non_pawn = sum(
        len(board.pieces(piece_type, chess.WHITE)) + len(board.pieces(piece_type, chess.BLACK))
        for piece_type in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN)
    )
    queens = len(board.pieces(chess.QUEEN, chess.WHITE)) + len(board.pieces(chess.QUEEN, chess.BLACK))
    if board.fullmove_number <= 12:
        return "opening"
    if non_pawn <= 8 or queens == 0:
        return "endgame"
    return "middlegame"
