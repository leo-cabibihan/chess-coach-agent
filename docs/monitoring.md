# Monitoring

PydanticAI runs are instrumented with Logfire and grouped under a `coach_session` span when
`LOGFIRE_TOKEN` is configured. The app also records local JSONL events in
`backend/data/logs/events.jsonl`, so monitoring works for local and credential-free review.

The React **Quality monitoring** dashboard calls `GET /api/monitoring` and displays total events,
completed analyses, LLM calls, input/output tokens, estimated model cost, average chat latency,
feedback volume, helpful rate, tool usage, and event-count bars.

Recorded events include `analysis_requested`, `analysis_completed`, `games_previewed`, `games_imported`,
`chat_requested`, `chat_completed`, and `moment_feedback`. Chat completion events record whether the
OpenRouter model was used, its model usage, estimated cost, executed tools, trace ID, and latency.
Analysis completion events record game, moment, theme, and timing data.

To send traces to Logfire, create a project token and set it before starting the API:

```bash
export LOGFIRE_TOKEN=...
uv run uvicorn chess_coach_agent.api:app --host 127.0.0.1 --port 8000
```

## User Feedback

Each critical moment has helpful and not-helpful buttons. `POST /api/feedback` records the moment ID,
game ID, detected theme, position FEN, rating, and optional comment. Feedback immediately appears in
the dashboard after it refreshes.

## Logs to Evaluation Candidates

Convert feedback events into a review queue:

```bash
cd backend
uv run python -m chess_coach_agent.monitoring \
  --export-candidates data/eval/feedback_candidates.jsonl
```

The exporter includes the FEN, expected theme, feedback rating, and reviewer comment. Every exported
row has `review_status: candidate`; it must be manually verified before joining the ground truth set.
This keeps user feedback useful without silently treating noisy ratings as truth.

Print the same summary used by the dashboard with:

```bash
uv run python -m chess_coach_agent.monitoring --summary
```
