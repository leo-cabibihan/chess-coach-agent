# Adaptive Platform Architecture

## Learning Loop

```text
Chess.com / Lichess / PGN
        |
        v
PGN parser + Stockfish detectors
        |
        +--> games, analyses, critical moments --> Progress analytics
        |
        v
PydanticAI coach (MiniMax tool routing and explanations)
        |
        +--> typed board / quiz / flashcard / evaluation / plan panel
        |
        v
Stockfish move grading --> quiz attempt --> review schedule --> player memory
        ^                                                       |
        +---------------- adaptive difficulty ------------------+
```

Stockfish and deterministic legality checks are authoritative for chess claims. MiniMax selects
tools, explains evidence, and chooses teaching activities. If OpenRouter is unavailable, the turn
finishes with deterministic coaching and the durable session remains usable.

## Storage

Postgres is the production system of record; SQLite is the credential-free local fallback.
SQLAlchemy repositories isolate persistence from FastAPI routes, and Alembic owns schema changes.
The schema stores players, games, analyses, moments, coach sessions, messages, summaries, memories,
plans, positions, attempts, flashcards, schedules, lesson chunks, and replayable SSE events.

Player identity is normalized `(platform, username)`. Chess.com and Lichess handles are separate
profiles. Browser session storage is only an offline cache for the most recently viewed analyses.

## Memory

- **Recent:** the last six conversation turns are passed as PydanticAI `message_history`.
- **Summary:** after 12 messages or 8,000 tokens, the session is compacted into a durable summary.
- **Player:** rating, themes, accuracy, mastery, and due counts are deterministically recomputed.
- **Episodic:** up to three older same-player summaries above cosine similarity 0.65 are retrieved.

The LLM cannot directly mutate player memory. Only imports, Stockfish results, attempts, hint use,
and explicit feedback update it.

## Retrieval

Raw PGNs, FENs, evaluations, and attempts are relational and are never embedded. pgvector stores
384-dimensional FastEmbed vectors for curated lesson chunks and compact session summaries. Lesson
retrieval compares title search, BM25, vector cosine search, and hybrid reciprocal-rank fusion. The
20-query benchmark controls the production strategy through explicit quality and latency gates.

## HTTP Flow

`POST /api/coach/sessions` creates a durable player-scoped session. A message is processed through
PydanticAI and recorded with typed panel output. `GET .../stream?message_id=...` replays persisted
SSE events with sequence IDs; `Last-Event-ID` resumes after a disconnect. Training endpoints create
plans and grade legal SAN or UCI moves with Stockfish before updating spaced repetition.

The React app uses TanStack Router for addressable workflows and TanStack Query for server state.
Recharts renders progress trends. `WorkspaceContext` retains only import and transient selection
state plus the offline analysis cache.
