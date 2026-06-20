from __future__ import annotations

import httpx


async def fetch_chesscom_pgn(username: str, max_games: int = 20) -> str:
    headers = {"User-Agent": "chess-coach-agent/0.1 educational capstone"}
    async with httpx.AsyncClient(timeout=30, headers=headers) as client:
        archives = await client.get(f"https://api.chess.com/pub/player/{username}/games/archives")
        archives.raise_for_status()
        urls = archives.json().get("archives", [])[-6:]
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
