# Chess Coach Agent

Chess Coach Agent is an AI Engineering Buildcamp capstone project. It turns a player's Chess.com,
Lichess, or uploaded PGN games into coachable critical moments, practical explanations, and drills.

The product is inspired by modern chess-coach UIs: the left side explains the AI analysis and the
right side shows the board, players, and move history. The agent focuses on improvement instead of
raw engine output.

## Problem

Club players collect hundreds of online games but rarely convert them into a focused training plan.
Engine analysis can say a move is worse, but it often does not explain the human pattern: loose
pieces, missed forcing moves, king-safety neglect, opening drift, or poor endgame conversion.

This project solves that by combining game import, engine-backed analysis, chess-principle retrieval,
OpenRouter commentary, deterministic fallback explanations, and daily challenge prompts.

## What It Does

- Upload or paste PGN.
- Load games from Chess.com or Lichess through backend import tools.
- Parse games into structured moves and metadata.
- Find up to four critical moments per game.
- Compare the move played against the engine or fallback best candidate.
- Explain what happened, the better plan, the chess principle, and a drill.
- Retrieve chess-principle notes from a local knowledge base.
- Ask follow-up questions through OpenRouter when `OPENROUTER_API_KEY` is configured.
- Log analysis/chat events locally for monitoring and future evaluation data.
- Show the analysis in a React frontend with a board and move history.

## Course Rubric Coverage

- **Problem description:** this README states the user problem and project goal.
- **Knowledge base and retrieval:** `backend/data/knowledge/` contains chess principle notes; retrieval is tested.
- **Agents and LLM:** `backend/src/chess_coach_agent/agent.py` orchestrates multiple tools; `llm.py` uses OpenRouter when configured.
- **Code organization:** backend is a Python package under `backend/src`; frontend is a Vite React app.
- **Testing:** backend tests cover PGN parsing, analysis, retrieval, API, and evaluation runner.
- **Evaluation:** `backend/data/eval/critical_moments.jsonl` is a hand-crafted dataset with expected tactical themes.
- **Monitoring:** `monitoring.py` writes JSONL events; docs explain how logs become future eval rows.
- **Reproducibility:** sample PGN data is included; setup commands are below.
- **Bonus:** React UI, Docker, docker-compose, Makefile, uv dependency workflow, and GitHub Actions CI are included.

## Quickstart

Backend:

```bash
cd backend
uv sync --extra dev
uv run pytest -q
uv run uvicorn chess_coach_agent.api:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open: <http://127.0.0.1:5173>

One-command local workflow:

```bash
make install
make test
make dev
```

Docker:

```bash
docker compose up --build
```

## OpenRouter

The app works without a model key by using deterministic coach text. To enable LLM commentary:

```bash
export OPENROUTER_API_KEY=...
export OPENROUTER_MODEL=openai/gpt-4o-mini
```

The model is only used for follow-up coaching explanations. The chess-critical logic remains grounded
in PGN parsing, legal move generation, optional Stockfish, and local chess-principle retrieval.

## Stockfish

If Stockfish is installed, set:

```bash
export STOCKFISH_PATH=/opt/homebrew/bin/stockfish
```

If no engine is available, the app falls back to legal-move and material heuristics so the capstone
still runs for reviewers.

## Evaluation

Run the hand-crafted evaluation:

```bash
cd backend
uv run python -m chess_coach_agent.evaluation --dataset data/eval/critical_moments.jsonl
```

Run the capstone self-scorer:

```bash
python3 scripts/score_project.py
```

## Reference

The UI direction is inspired by the Reddit post "Built a chess coach to help players improve by
explaining critical moments in your games" and by the provided screenshot in `docs/reference-ui.png`.
The implementation is original and adapted to this capstone rubric.
