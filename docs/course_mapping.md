# Course Mapping

| Buildcamp topic | Project artifact |
| --- | --- |
| RAG and search | BM25 retrieval, baseline comparison, eight-query hand-crafted benchmark |
| Structured output | PydanticAI validates `CoachingOutput` evidence, principle, drill, move, and confidence fields |
| Agents and tools | PydanticAI registers four tools and records real tool execution history |
| Project structure | Python package under `backend/src`, React app under `frontend/src` |
| Testing agents | Unit/API tests and `test_judge.py` for the LLM-judge pipeline |
| Monitoring | Logfire agent traces plus JSONL usage/cost events, React dashboard, and moment feedback |
| Offline evaluation | Deterministic labels, MiniMax judge, prompt comparison, and manual review |
| Project scorer | `scripts/score_project.py` self-checks the capstone rubric |

## Agent Tools

- `import_pgn_text`: parse pasted/uploaded PGN and analyze games.
- `import_platform_games`: fetch games from Chess.com or Lichess.
- `retrieve_chess_principles`: retrieve chess teaching notes for themes.
- `generate_trend_summary`: summarize record and recurring themes from games.
- `EngineAnalyzer.analyse`: use Stockfish when present; fall back to legal-move heuristics.
- `answer_question`: call OpenRouter for coach chat with retrieved context.

For coach chat, MiniMax uses PydanticAI's native tool loop to call at least two of
`search_chess_principles`, `inspect_critical_moments`, `inspect_position`, and
`build_training_drill`. PydanticAI validates the final structured output. Missing credentials or
provider errors fall back to deterministic structured coaching so the workflow remains reliable.

## Tuning Evidence

- BM25 achieved `1.00` MRR and `100%` hit rate at 3; the title baseline achieved `0.25` on both.
- MiniMax scored the grounded response format `5.0/6` with a `100%` pass rate versus `3.0/6`
  and `50%` for the concise format.
- MiniMax's feedback was used to rewrite the opening-drift explanation and drill. The grounded score
  then increased to `5.5/6`, and the opening-drift case increased from `4/6` to `6/6`.

Full commands and case-level results are in `docs/evaluation_results.md`.
