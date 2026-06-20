# Course Mapping

| Buildcamp topic | Project artifact |
| --- | --- |
| RAG and search | `backend/src/chess_coach_agent/knowledge.py`, `backend/data/knowledge/` |
| Structured output | `backend/src/chess_coach_agent/models.py` Pydantic models |
| Agents and tools | `ChessCoachAgent` orchestrates import, analysis, retrieval, trends, and LLM chat |
| Project structure | Python package under `backend/src`, React app under `frontend/src` |
| Testing agents | `backend/tests/` covers parsing, tools, API, retrieval, and eval runner |
| Monitoring | `backend/src/chess_coach_agent/monitoring.py` writes JSONL events |
| Offline evaluation | `backend/src/chess_coach_agent/evaluation.py`, `backend/data/eval/critical_moments.jsonl` |
| Project scorer | `scripts/score_project.py` self-checks the capstone rubric |

## Agent Tools

- `import_pgn_text`: parse pasted/uploaded PGN and analyze games.
- `import_platform_games`: fetch games from Chess.com or Lichess.
- `retrieve_chess_principles`: retrieve chess teaching notes for themes.
- `generate_trend_summary`: summarize record and recurring themes from games.
- `EngineAnalyzer.analyse`: use Stockfish when present; fall back to legal-move heuristics.
- `answer_question`: call OpenRouter for coach chat with retrieved context.

## Tuning Evidence

The evaluation dataset is intentionally small but hand-crafted. Future tuning should add positions
from kfctofu's own losses and compare:

- Stockfish depth 6 vs 9 vs 12,
- heuristic-only fallback vs engine-backed labels,
- keyword retrieval vs chunked retrieval,
- direct LLM explanation vs retrieval-grounded explanation.
