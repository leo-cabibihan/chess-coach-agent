from __future__ import annotations

import json
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
    return await complete_with_openrouter(
        system=(
            "You are a precise chess coach. Ground every explanation in engine facts, "
            "legal moves, and named chess principles. Keep advice concrete and never pretend "
            "a move is forced if the context does not prove it."
        ),
        prompt=prompt,
        temperature=0.25,
    )


async def complete_with_openrouter(
    system: str,
    prompt: str,
    temperature: float = 0.0,
) -> tuple[str, bool]:
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
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
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
    tool_catalog = (
        "retrieve_principles: search the chess knowledge base for relevant teaching notes; "
        "inspect_critical_moments: inspect engine and heuristic facts from the current game; "
        "build_training_drill: turn the main detected theme into a concrete practice exercise."
    )
    planning_prompt = dedent(
        f"""
        Question: {question}
        Game analysis available: {analysis is not None}

        Available tools:
        {tool_catalog}

        Choose at least two useful tools. Return JSON only:
        {{"tools": ["tool_name", "tool_name"]}}
        """
    ).strip()
    plan_text, planned_with_llm = await complete_with_openrouter(
        "You route chess coaching questions to tools. Return valid JSON only.",
        planning_prompt,
        temperature=0.0,
    )
    selected_tools = _parse_tool_plan(plan_text) if planned_with_llm else []
    observations, retrieved_titles = _execute_coach_tools(selected_tools, question, analysis)

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

        Tool observations selected by the planning step:
        {chr(10).join(f"- {item}" for item in observations) or "No model-selected tools were available."}

        Answer as a practical coach. Include one drill if useful.
        """
    ).strip()
    answer, used_llm = await explain_with_openrouter(prompt) if planned_with_llm else ("", False)
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
    return ChatResponse(
        answer=answer,
        used_llm=used_llm,
        retrieved_notes=list(dict.fromkeys([*retrieved_titles, *(note.title for note in notes)])),
    )


def _parse_tool_plan(text: str) -> list[str]:
    allowed = {"retrieve_principles", "inspect_critical_moments", "build_training_drill"}
    try:
        start, end = text.find("{"), text.rfind("}")
        payload = json.loads(text[start : end + 1])
        selected = [name for name in payload.get("tools", []) if name in allowed]
    except (ValueError, TypeError, json.JSONDecodeError):
        selected = []
    if len(set(selected)) < 2:
        return ["retrieve_principles", "inspect_critical_moments"]
    return list(dict.fromkeys(selected))


def _execute_coach_tools(
    selected_tools: list[str],
    question: str,
    analysis: CoachAnalysis | None,
) -> tuple[list[str], list[str]]:
    observations: list[str] = []
    retrieved_titles: list[str] = []
    for tool in selected_tools:
        if tool == "retrieve_principles":
            tool_notes = retrieve_notes(question, top_k=3)
            retrieved_titles.extend(note.title for note in tool_notes)
            observations.append(
                "retrieve_principles => "
                + (" | ".join(f"{note.title}: {note.snippet}" for note in tool_notes) or "no matching notes")
            )
        elif tool == "inspect_critical_moments":
            if analysis and analysis.moments:
                facts = " | ".join(
                    f"move {moment.move_number}: {moment.played_san}, theme {moment.theme}, "
                    f"candidate {moment.best_san or 'unknown'}"
                    for moment in analysis.moments[:4]
                )
                observations.append(f"inspect_critical_moments => {facts}")
            else:
                observations.append("inspect_critical_moments => no analyzed game supplied")
        elif tool == "build_training_drill":
            if analysis and analysis.moments:
                moment = analysis.moments[0]
                observations.append(f"build_training_drill => {moment.drill_prompt}")
            else:
                observations.append(
                    "build_training_drill => solve five positions using checks, captures, and threats"
                )
    return observations, retrieved_titles
