from __future__ import annotations

import io

import chess.pgn
import httpx

from .models import GamePreview
from .pgn import parse_pgn_text


async def fetch_chesscom_pgn(username: str, max_games: int = 20) -> str:
    headers = {"User-Agent": "chess-coach-agent/0.1 educational capstone"}
    async with httpx.AsyncClient(timeout=30, headers=headers) as client:
        archives = await client.get(f"https://api.chess.com/pub/player/{username}/games/archives")
        archives.raise_for_status()
        urls = archives.json().get("archives", [])
        chunks: list[str] = []
        for url in reversed(urls):
            pgn_url = url + "/pgn"
            response = await client.get(pgn_url)
            response.raise_for_status()
            chunks.append(response.text)
            if sum(chunk.count("[Event ") for chunk in chunks) >= max_games:
                break
    return "\n\n".join(chunks)


async def fetch_lichess_pgn(username: str, max_games: int = 20) -> str:
    headers = {"Accept": "application/x-chess-pgn", "User-Agent": "chess-coach-agent/0.1 educational capstone"}
    url = f"https://lichess.org/api/games/user/{username}?max={max_games}&pgnInJson=false&clocks=true&evals=false"
    async with httpx.AsyncClient(timeout=45, headers=headers) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


async def fetch_platform_pgn(platform: str, username: str, max_games: int) -> str:
    if platform == "chess.com":
        return await fetch_chesscom_pgn(username, max_games)
    return await fetch_lichess_pgn(username, max_games)


def preview_pgn_games(
    pgn_text: str,
    username: str,
    platform: str,
    max_games: int = 50,
) -> list[GamePreview]:
    handle = io.StringIO(pgn_text)
    previews: list[GamePreview] = []
    while len(previews) < max_games:
        game = chess.pgn.read_game(handle)
        if game is None:
            break
        exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=True)
        game_pgn = game.accept(exporter)
        parsed = parse_pgn_text(game_pgn, player=username, max_games=1)
        if not parsed:
            continue
        metadata = parsed[0].metadata
        headers = game.headers
        if metadata.player_color == "white":
            opponent = metadata.black
            opponent_elo_raw = headers.get("BlackElo", "")
        elif metadata.player_color == "black":
            opponent = metadata.white
            opponent_elo_raw = headers.get("WhiteElo", "")
        else:
            opponent = metadata.black
            opponent_elo_raw = ""
        try:
            opponent_elo = int(opponent_elo_raw)
        except ValueError:
            opponent_elo = None
        previews.append(
            GamePreview(
                game_id=metadata.game_id,
                pgn=game_pgn,
                source=platform,  # type: ignore[arg-type]
                white=metadata.white,
                black=metadata.black,
                result=metadata.result,
                date=metadata.date,
                time_control=metadata.time_control,
                link=metadata.link,
                player_color=metadata.player_color,
                player_result=metadata.player_result,
                player_elo=metadata.player_elo,
                opponent=opponent,
                opponent_elo=opponent_elo,
            )
        )
    return previews
