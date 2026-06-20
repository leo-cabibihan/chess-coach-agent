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
- Browse up to 50 Chess.com or Lichess games before choosing which ones to analyze.
- Parse games into structured moves and metadata.
- Find up to four critical moments per game.
- Compare the move played against the engine or fallback best candidate.
- Explain what happened, the better plan, the chess principle, and a drill.
- Retrieve chess-principle notes with the benchmark-selected BM25 search strategy.
- Ask follow-up questions through OpenRouter when `OPENROUTER_API_KEY` is configured.
- Let MiniMax select multiple coaching tools before synthesizing each follow-up answer.
- Log analysis/chat events, collect moment feedback, and display quality metrics.
- Show the analysis in a React frontend with a board and move history.

## Routed Frontend

The React app uses TanStack Router with intent preloading and scroll restoration:

- `/analyze` separates online import from pasted PGN. Online import first loads a metadata-only game
  picker; the user can filter by result and select up to ten games before running Stockfish.
- `/games` is the analyzed-game library.
- `/games/:gameId?moment=:momentId` makes game and critical-moment selection URL-addressable.
- `/coach` provides focused MiniMax chat with selectable game context.
- `/quality` displays monitoring and feedback metrics.

The active workspace is stored in browser session storage so route refreshes preserve analyzed games.

## Course Rubric Coverage

- **Problem description:** this README states the user problem and project goal.
- **Knowledge base and retrieval:** BM25 was selected through an eight-query retrieval benchmark.
- **Agents and LLM:** `backend/src/chess_coach_agent/agent.py` orchestrates multiple tools; `llm.py` uses OpenRouter when configured.
- **Code organization:** backend is a Python package under `backend/src`; frontend is a Vite React app.
- **Testing:** unit/API tests plus a mocked LLM-judge test run without network credentials.
- **Evaluation:** MiniMax judges coaching output against a hand-crafted, manually reviewed dataset and compares prompt formats.
- **Monitoring:** a React dashboard displays JSONL metrics; thumbs feedback can be exported as evaluation candidates.
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

## Cloud Deployment

The root `Dockerfile` builds the React app, installs Stockfish, and serves the frontend and FastAPI
from one container. `render.yaml` defines a Render web service with `/api/health` checks.

1. Push this repository to GitHub.
2. Rotate the OpenRouter key if it has ever been shared, then keep the replacement out of Git.
3. In Render, create a **Blueprint** from the repository. Render reads `render.yaml` and prompts for
   `OPENROUTER_API_KEY` because it is declared with `sync: false`.
4. Deploy and verify `/api/health`, `/analyze`, game preview, selected-game analysis, and coach chat.

The free configuration stores monitoring JSONL under `/tmp`, so metrics reset when the service
restarts or redeploys. For persistent monitoring, attach a paid disk at `/var/data` and set
`MONITORING_LOG_PATH=/var/data/events.jsonl`, or move events to managed Postgres.

## OpenRouter

The app works without a model key by using deterministic coach text. To enable LLM commentary:

```bash
export OPENROUTER_API_KEY=...
export OPENROUTER_MODEL=minimax/minimax-m3
```

The model is used for follow-up coaching and optional LLM-judge evaluation. Chess-critical logic
remains grounded in PGN parsing, legal move generation, optional Stockfish, and retrieved principles.

## Stockfish

If Stockfish is installed, set:

```bash
export STOCKFISH_PATH=/opt/homebrew/bin/stockfish
```

If no engine is available, the app falls back to legal-move and material heuristics so the capstone
still runs for reviewers.

## Evaluation

Run deterministic theme evaluation and the retrieval benchmark:

```bash
cd backend
uv run python -m chess_coach_agent.evaluation --dataset data/eval/critical_moments.jsonl
uv run python -m chess_coach_agent.retrieval_evaluation --dataset data/eval/retrieval.jsonl
```

Run the live MiniMax judge and compare the concise and grounded formats:

```bash
cd backend
uv run python -m chess_coach_agent.judge_evaluation --dataset data/eval/critical_moments.jsonl --tune
```

The live judge requires `OPENROUTER_API_KEY`. The regular test suite uses a controlled fake judge,
so CI stays deterministic. Measured results and the resulting prompt change are in
`docs/evaluation_results.md`; manual reviews are in `docs/manual_evaluation.md`.

## Monitoring and Feedback

The dashboard at the bottom of the React app reads `GET /api/monitoring`. Helpful/not-helpful
buttons on each critical moment write feedback events. Export those events for review with:

```bash
cd backend
uv run python -m chess_coach_agent.monitoring \
  --export-candidates data/eval/feedback_candidates.jsonl
```

Candidate rows are deliberately marked `review_status: candidate`; a person must review them before
merging them into the hand-crafted ground truth dataset. See `docs/monitoring.md`.

Run the capstone self-scorer:

```bash
python3 scripts/score_project.py
```

## Reference

The UI direction is inspired by the Reddit post "Built a chess coach to help players improve by
explaining critical moments in your games" and by the provided screenshot in `docs/reference-ui.png`.
The implementation is original and adapted to this capstone rubric.
