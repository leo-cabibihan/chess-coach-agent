from unittest.mock import AsyncMock, patch

import httpx
import pytest

from chess_coach_agent.adaptive_api import _sync_failure_message
from chess_coach_agent.agent import sample_pgn
from chess_coach_agent.importers import chesscom_user_agent, fetch_chesscom_pgn, preview_pgn_games


def test_preview_pgn_games_returns_selectable_metadata_and_unique_ids():
    games = preview_pgn_games(sample_pgn(), "kfctofu", "chess.com", max_games=8)
    assert len(games) == 8
    assert len({game.game_id for game in games}) == 8
    assert games[0].opponent
    assert games[0].player_result in {"win", "loss", "draw", "unknown"}
    assert "[Event " in games[0].pgn


def test_chesscom_user_agent_includes_contact():
    assert "contact:" in chesscom_user_agent()


@pytest.mark.asyncio
async def test_fetch_chesscom_pgn_uses_lowercase_handle():
    request = httpx.Request("GET", "https://api.chess.com/pub/player/magnuscarlsen/games/archives")
    response = httpx.Response(200, request=request, json={"archives": []})
    client = AsyncMock()
    client.get = AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)

    with patch("chess_coach_agent.importers._http_client", return_value=client):
        await fetch_chesscom_pgn("MagnusCarlsen", max_games=1)

    assert client.get.await_args_list[0].args[0].endswith("/magnuscarlsen/games/archives")


def test_sync_failure_message_for_chesscom_403():
    request = httpx.Request("GET", "https://api.chess.com/pub/player/foo/games/archives")
    response = httpx.Response(403, request=request)
    exc = httpx.HTTPStatusError("blocked", request=request, response=response)
    message = _sync_failure_message(exc)
    assert "403" in message
    assert "CHESSCOM_API_CONTACT" in message
