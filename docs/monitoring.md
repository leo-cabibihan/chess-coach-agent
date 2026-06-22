# Monitoring

Offline PydanticAI evaluation runs are instrumented with Logfire when `LOGFIRE_TOKEN` is configured.
The app also records local JSONL events in
`backend/data/logs/events.jsonl`, so monitoring works for local and credential-free review.

The React **Quality monitoring** dashboard calls `GET /api/monitoring` and displays total events,
completed analyses, optional evaluation calls, feedback volume, helpful rate, tool usage, training
sessions, quiz accuracy, hint use, retrieval method, and event-count bars.

Active product events include `analysis_requested`, `analysis_timing`, `analysis_completed`,
`games_sync_completed`, `games_sync_failed`, `training_session_created`, `quiz_attempted`, and
`moment_feedback`. Historical chat and stream event fields are still accepted by the dashboard so
older JSONL logs remain readable. `analysis_completed` records game, moment, and theme counts;
`analysis_timing` records paste-import duration from `POST /api/analyze`.

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
