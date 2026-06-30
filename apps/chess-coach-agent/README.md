# Chess Coach Agent

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/leo-cabibihan/chess-coach-agent)

**Live app:** <https://chess-coach-agent.onrender.com/>

Chess Coach Agent is an adaptive AI Engineering Buildcamp capstone. It turns a player's Chess.com,
Lichess, or uploaded PGN games into a durable learning loop:

```text
Import games -> Detect weaknesses -> Practice -> Evaluate -> Adapt
```

The product is inspired by modern chess-coach UIs: the left side explains the AI analysis and the
right side shows the board, players, and move history. The agent focuses on improvement instead of
raw engine output.

## Problem

Club players collect hundreds of online games but rarely convert them into a focused training plan.
Engine analysis can say a move is worse, but it often does not explain the human pattern: loose
pieces, missed forcing moves, king-safety neglect, opening drift, or poor endgame conversion.

This project solves that by combining full-history game sync, engine-backed analysis,
deterministic theme explanations, direct board drills, and spaced repetition. Retrieval and
PydanticAI remain available for offline evaluation, not the live practice loop.

## What It Does

- Upload or paste PGN.
- Sync a player's Chess.com or Lichess history in one action; already analyzed games are skipped.
- Parse games into structured moves and metadata.
- Find a variable number of critical moments using Lichess-style winning-chance-loss thresholds.
- Compare the move played against the engine or fallback best candidate.
- Generate deterministic explanations (what happened, better plan, principle, drill) from verified
  engine losses, theme detectors, and BM25 lesson snippets.
- Persist games, player memory, quizzes, and review schedules in
  Postgres (SQLite is the credential-free local fallback).
- Build direct practice sessions from the player's highest-value mistakes and blunders.
- Grade legal SAN/UCI candidate moves with Stockfish, then adapt difficulty by theme.
- Resurface failed positions after 1 day, hinted successes after 3, and clean successes after 7,
  doubling successful review intervals up to 30 days.
- Attach curated lesson snippets to each analysis through BM25 retrieval; recompute player weakness memory from imports, moments, and quiz attempts without embedding raw PGNs or FENs.
- Run a PydanticAI agent with twelve documented tools when practice sessions are created; rank stored
  mistakes, write grounded quiz copy, and fall back to deterministic templates without an API key.
- Validate every coaching answer as structured Pydantic output with evidence and confidence.
- Trace live practice-agent runs with Logfire and display quality, agent fallback, and feedback metrics.
- Show the analysis in a React frontend with a board and move history.

## Routed Frontend

The React app uses TanStack Router with intent preloading and scroll restoration:

- `/` is the player dashboard: rating, weaknesses, due positions, progress, and continue training.
- `/games` combines automatic full-history sync with the analyzed-game evidence library. Sync runs
  as a durable job, reports progress, and analyzes only games that are not already stored.
- `/analyze` remains as a compatibility redirect to the Games import panel.
- `/games/:gameId?moment=:momentId` makes game and critical-moment selection URL-addressable.
- `/practice/:sessionId` is a focused board drill with Stockfish grading and review scheduling.
- Retired `/coach` URLs redirect to `/practice`; there is no user-facing chatbot.
- `/progress` charts rating, results, themes, quiz accuracy, mastery, and transfer to games.
- `/quality` is a hidden reviewer/admin route for evaluation, retrieval, quiz, hint, and feedback
  metrics.

TanStack Query owns server state. Browser session storage is retained only as an offline cache for
the current import and viewed analyses. See `docs/architecture.md` for the data flow and memory model.

## Course Rubric Coverage

- **Problem description:** this README states the user problem and project goal.
- **Knowledge base and retrieval:** 20 hand-authored queries compare title, BM25, vector, and hybrid
  RRF retrieval on hit rate, MRR, source correctness, and latency. The benchmark keeps BM25 as the
  production default until hybrid clears every quality and latency gate.
- **Agents and LLM:** a PydanticAI agent with twelve documented tools runs when practice sessions are
  created; it ranks stored moments and writes quiz copy, with deterministic fallback when no API key
  is configured. Stockfish still grades every move attempt.
- **Code organization:** backend is a Python package under `backend/src`; frontend is a Vite React app.
- **Testing:** 13 test modules / 22 pytest cases cover registered tool order, agent evaluation fixtures,
  legal move grading, adaptive difficulty, durable training flows, and judge tests without network
  credentials.
- **Evaluation:** four layers — deterministic theme detection, retrieval benchmark, analysis-copy judge,
  and agent scenario evaluation with structured `JudgeFeedback`.
- **Monitoring:** Logfire traces live PydanticAI practice-agent runs; the Quality page displays local
  analysis, retrieval, practice-agent fallback rate, hint use, and feedback metrics.
- **Reproducibility:** sample PGN data is included; setup commands are below.
- **Bonus:** React UI, Docker, docker-compose, Makefile, uv dependency workflow, and GitHub Actions CI are included.

## Quickstart

Backend:

```bash
cd backend
uv sync --extra dev
uv run alembic upgrade head
uv run python -m chess_coach_agent.ingest_knowledge
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

Docker (starts React, FastAPI, Stockfish, Postgres, pgvector, migrations, and lesson ingestion):

```bash
docker compose up --build
```

## Cloud Deployment

The root `Dockerfile` builds React, installs Stockfish, runs Alembic and idempotent lesson ingestion,
then serves the frontend and FastAPI from one container. `render.yaml` provisions the web service
and managed Postgres database with `/api/health` checks.

1. Push this repository to GitHub.
2. Rotate the OpenRouter key if it has ever been shared, then keep the replacement out of Git.
3. In Render, create a **Blueprint** from the repository. Render reads `render.yaml` and prompts for
   `OPENROUTER_API_KEY` because it is declared with `sync: false`.
4. Deploy and verify `/api/health`, `/`, game import, `/practice`, a quiz attempt, `/progress`, and
   `/quality`.

The free configuration stores monitoring JSONL under `/tmp`, so metrics reset when the service
restarts or redeploys. For persistent monitoring, attach a paid disk at `/var/data` and set
`MONITORING_LOG_PATH=/var/data/events.jsonl`, or move events to managed Postgres.

## OpenRouter

Copy env vars into `backend/.env` (the API loads `.env` from `backend/`, repo root, or cwd):

```bash
bash scripts/setup_llm.sh          # create backend/.env if missing
bash scripts/setup_llm.sh --verify # ping OpenRouter + agent smoke check
```

Or manually:

```bash
export OPENROUTER_API_KEY=...
export OPENROUTER_MODEL=minimax/minimax-m3
```

`GET /api/llm/status` reports whether the practice agent will use PydanticAI or deterministic fallback.

You can override the default with any OpenRouter model, for example `minimax/minimax-m3`. The twelve
documented tools are
`search_chess_principles`, `inspect_critical_moments`, `inspect_player_moments`, `inspect_position`,
`build_training_drill`, `inspect_game`, `compare_moves`, `rank_practice_moments`,
`generate_position_quiz`, `evaluate_candidate_move`, `build_training_session`, and `write_quiz_copy`.
Chess-critical logic remains grounded in PGN parsing, legal move generation, Stockfish, stored player
evidence, and cited lessons.

There is no user-facing chat UI. The practice page is the agent surface: starting a session invokes
the tool loop to rank stored mistakes and write grounded quiz prompts. BM25/vector retrieval and the
LLM judge remain available for reproducible offline evaluation.

Critical moments are not quota-filled. Stockfish evaluations are converted to winning chances, then
losses of 0.10, 0.20, and 0.30 are labeled inaccuracy, mistake, and blunder. Mistakes and blunders
are preferred for drills; thematic heuristics explain an already verified engine loss rather than
inventing training moments. See [`docs/moment_selection.md`](docs/moment_selection.md).

MiniMax M3 cost estimates use the current OpenRouter rates configured in the app. Override them for
a different model with `OPENROUTER_INPUT_COST_PER_MILLION` and
`OPENROUTER_OUTPUT_COST_PER_MILLION`.

## Stockfish

If Stockfish is installed, set:

```bash
export STOCKFISH_PATH=/opt/homebrew/bin/stockfish
```

If no engine is available, the app falls back to legal-move and material heuristics so the capstone
still runs for reviewers.

## Evaluation

Evaluation runs in four layers:

| Layer | Module | Question |
| --- | --- | --- |
| Foundation | `evaluation.py` | Did Stockfish/heuristics detect the right theme? |
| Retrieval | `retrieval_evaluation.py` | Which search strategy should production use? |
| Analysis copy | `judge_evaluation.py` | Is deterministic explanation prose grounded and coach-like? |
| Agent | `agent_evaluation.py` | Does the PydanticAI agent route tools and answer correctly? |

Run deterministic theme evaluation and the 20-query retrieval benchmark:

```bash
cd backend
uv run python -m chess_coach_agent.evaluation --dataset data/eval/critical_moments.jsonl
uv run python -m chess_coach_agent.retrieval_evaluation --dataset data/eval/retrieval.jsonl --output data/eval/retrieval_results.json
```

Run the analysis-copy judge and compare concise vs grounded formats:

```bash
cd backend
uv run python -m chess_coach_agent.judge_evaluation --dataset data/eval/critical_moments.jsonl --tune
```

Run the offline agent scenario suite (TestModel routing + heuristic judge; no network required):

```bash
cd backend
uv run python -m chess_coach_agent.agent_evaluation --dataset data/eval/agent_scenarios.jsonl
uv run pytest tests/test_agent_eval.py tests/test_tools.py -q
```

Add `--live` to `agent_evaluation` when you want OpenRouter to score real agent runs. The regular
test suite uses a controlled fake judge and TestModel routing, so CI stays deterministic. Measured
results are in `docs/evaluation_results.md`; manual reviews are in `docs/manual_evaluation.md`.

## Monitoring and Feedback

The `/quality` dashboard reads `GET /api/monitoring` and displays analyses, retrieval, practice-agent
runs, fallback rate, hint use, evaluation runs, and feedback. Set `LOGFIRE_TOKEN` to send live
PydanticAI practice-agent traces to Logfire. Without a token, local JSONL monitoring remains active.
Helpful/not-helpful buttons on each critical moment write feedback events. Export those events with:

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

## Documentation

| Doc | Purpose |
| --- | --- |
| [`docs/architecture.md`](docs/architecture.md) | Learning loop, storage, retrieval, and HTTP flow |
| [`docs/moment_selection.md`](docs/moment_selection.md) | Lichess-style winning-chance thresholds and theme rules |
| [`docs/evaluation_results.md`](docs/evaluation_results.md) | Retrieval benchmark and MiniMax judge tuning |
| [`docs/manual_evaluation.md`](docs/manual_evaluation.md) | Hand-reviewed ground-truth coaching cases |
| [`docs/monitoring.md`](docs/monitoring.md) | JSONL events, Logfire, feedback, and `/quality` dashboard |
| [`docs/chess-coach-presentation.html`](docs/chess-coach-presentation.html) | Optional single-page codebase guide for presentations |

The UI direction is inspired by modern chess-coach products that pair analysis text with a board and
move list. Screenshots live in `docs/presentation-assets/`.
