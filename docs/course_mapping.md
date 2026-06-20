# Course Mapping

| Buildcamp topic | Project artifact |
| --- | --- |
| RAG and search | BM25 retrieval, baseline comparison, eight-query hand-crafted benchmark |
| Structured output | `backend/src/chess_coach_agent/models.py` Pydantic models |
| Agents and tools | `ChessCoachAgent` orchestrates import, analysis, retrieval, trends, and LLM chat |
| Project structure | Python package under `backend/src`, React app under `frontend/src` |
| Testing agents | Unit/API tests and `test_judge.py` for the LLM-judge pipeline |
| Monitoring | JSONL events, `/api/monitoring`, React dashboard, and moment feedback |
| Offline evaluation | Deterministic labels, MiniMax judge, prompt comparison, and manual review |
| Project scorer | `scripts/score_project.py` self-checks the capstone rubric |

## Agent Tools

- `import_pgn_text`: parse pasted/uploaded PGN and analyze games.
- `import_platform_games`: fetch games from Chess.com or Lichess.
- `retrieve_chess_principles`: retrieve chess teaching notes for themes.
- `generate_trend_summary`: summarize record and recurring themes from games.
- `EngineAnalyzer.analyse`: use Stockfish when present; fall back to legal-move heuristics.
- `answer_question`: call OpenRouter for coach chat with retrieved context.

For coach chat, MiniMax first returns a JSON tool plan choosing at least two of
`retrieve_principles`, `inspect_critical_moments`, and `build_training_drill`. The application executes
those tools and sends their observations back to MiniMax for the final answer. Invalid plans fall
back to retrieval plus position inspection so the workflow remains reliable.

## Tuning Evidence

- BM25 achieved `1.00` MRR and `100%` hit rate at 3; the title baseline achieved `0.25` on both.
- MiniMax scored the grounded response format `5.0/6` with a `100%` pass rate versus `3.0/6`
  and `50%` for the concise format.
- MiniMax's feedback was used to rewrite the opening-drift explanation and drill. The grounded score
  then increased to `5.5/6`, and the opening-drift case increased from `4/6` to `6/6`.

Full commands and case-level results are in `docs/evaluation_results.md`.
