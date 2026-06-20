# Monitoring

The app records local JSONL events in `backend/data/logs/events.jsonl`.

Recorded events:

- `analysis_requested`
- `analysis_completed`
- `games_imported`
- `chat_requested`

Each row includes a UTC timestamp and request metadata. These logs are intentionally simple so they
remain reproducible without cloud credentials.

## Feedback to Evaluation Data

The next iteration should add thumbs-up/down feedback in the React UI. Reviewed feedback rows can be
promoted into `backend/data/eval/critical_moments.jsonl` by adding:

- the PGN or FEN,
- the player,
- the expected theme,
- reviewer notes explaining why the label is correct.

This supports the monitoring bonus criterion: logs and feedback can become future ground truth.

## Optional Production Monitoring

For a deployed version, ship the JSONL events to an OpenTelemetry backend or Logfire. Useful charts:

- analyses per user,
- average number of critical moments,
- most common themes,
- OpenRouter success/fallback rate,
- evaluation pass rate over time.
