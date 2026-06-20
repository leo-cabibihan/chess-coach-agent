from __future__ import annotations

import os
from textwrap import dedent

import httpx
from dotenv import load_dotenv

from .knowledge import retrieve_notes
from .models import ChatResponse, CoachAnalysis


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

load_dotenv()


def _model_name() -> str:
    return os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")


async def explain_with_openrouter(prompt: str) -> tuple[str, bool]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return "", False
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": "Chess Coach Agent",
    }
    body = {
        "model": _model_name(),
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a precise chess coach. Ground every explanation in engine facts, "
                    "legal moves, and named chess principles. Keep advice concrete and never pretend "
                    "a move is forced if the context does not prove it."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.25,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(OPENROUTER_URL, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip(), True
    except Exception:
        return "", False


async def answer_question(question: str, analysis: CoachAnalysis | None) -> ChatResponse:
    notes = retrieve_notes(question, top_k=3)
    analysis_context = ""
    if analysis:
        moment_lines = [
            f"- {m.theme} on move {m.move_number}: played {m.played_san}, best {m.best_san or 'unknown'}, {m.summary}"
            for m in analysis.moments
        ]
        analysis_context = "\n".join(moment_lines)
    prompt = dedent(
        f"""
        User question:
        {question}

        Current game analysis:
        {analysis_context or "No game analysis was provided."}

        Retrieved chess principles:
        {chr(10).join(f"- {note.title}: {note.snippet}" for note in notes) or "None"}

        Answer as a practical coach. Include one drill if useful.
        """
    ).strip()
    answer, used_llm = await explain_with_openrouter(prompt)
    if not answer:
        if analysis and analysis.moments:
            first = analysis.moments[0]
            answer = (
                f"The biggest lesson is **{first.theme.replace('_', ' ')}** around move "
                f"{first.move_number}. You played {first.played_san}; "
                f"{first.best_san or 'the engine suggestion'} was a better candidate. "
                f"Drill it by setting up the FEN and spending 3 minutes listing forcing moves."
            )
        elif notes:
            answer = f"I found this principle: {notes[0].snippet}"
        else:
            answer = "Ask me about a game after running analysis, or upload a PGN first."
    return ChatResponse(answer=answer, used_llm=used_llm, retrieved_notes=[n.title for n in notes])
