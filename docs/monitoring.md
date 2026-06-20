# Monitoring

The app records local JSONL events in `backend/data/logs/events.jsonl`. The React **Quality
monitoring** dashboard calls `GET /api/monitoring` and displays total events, completed analyses,
feedback volume, helpful rate, and event-count bars.

Recorded events include `analysis_requested`, `analysis_completed`, `games_imported`,
`chat_requested`, `chat_completed`, and `moment_feedback`. Chat completion events record whether the
OpenRouter model was used. Analysis completion events record game, moment, and theme counts.

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
