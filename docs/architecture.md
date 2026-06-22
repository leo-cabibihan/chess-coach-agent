# Adaptive Platform Architecture

## Learning Loop

```text
Chess.com / Lichess / PGN
        |
        v
Durable full-history sync + PGN parser + Stockfish detectors
        |
        +--> games, analyses, critical moments --> Progress analytics
        |
        v
Direct practice selection from stored mistakes
        |
        +--> typed board / quiz / evaluation panel
        |
        v
Stockfish move grading --> quiz attempt --> review schedule --> player memory
        ^                                                       |
        +---------------- adaptive difficulty ------------------+
```

Stockfish and deterministic legality checks are authoritative for chess claims. The user-facing
workflow does not wait for an LLM: it selects stored mistakes, grades moves, and schedules review
deterministically. PydanticAI and MiniMax remain isolated to agent and judge evaluation workflows.

## Storage

Postgres is the production system of record; SQLite is the credential-free local fallback.
SQLAlchemy repositories isolate persistence from FastAPI routes, and Alembic owns schema changes.
The active product schema stores players, games, analyses, moments, sync jobs, player memory, plans,
positions, attempts, schedules, and lesson chunks. Retired chat tables remain in the historical
Alembic migration and can be removed in a later schema migration.

Player identity is normalized `(platform, username)`. Chess.com and Lichess handles are separate
profiles. Browser session storage is only an offline cache for the most recently viewed analyses.

## Player Memory

Rating, recurring themes, quiz accuracy, mastery, and due counts are deterministically recomputed.
Only imports, Stockfish results, attempts, hint use, and explicit feedback update player state. The
former conversation-memory prototype remains covered by isolated tests but is not on a production
HTTP path after the chat experience was retired.

## Retrieval

Raw PGNs, FENs, evaluations, and attempts are relational and are never embedded. pgvector stores
384-dimensional FastEmbed vectors for curated lesson chunks and compact session summaries. Lesson
retrieval compares title search, BM25, vector cosine search, and hybrid reciprocal-rank fusion. The
20-query benchmark controls the production strategy through explicit quality and latency gates.

Training ranks the player's stored critical moments by trainability and severity. Structured chess
facts are queried relationally rather than embedded as prose.

## HTTP Flow

Training endpoints create plans from real mistakes and grade legal SAN or UCI moves with Stockfish
before updating spaced repetition. The React app exposes this directly at `/practice`; legacy coach
URLs redirect there and no chat UI is shipped.

`POST /api/games/sync` creates or resumes one active sync job per player. The server fetches up to
5,000 games, skips external game IDs with existing analyses, and persists progress for polling via
`GET /api/games/sync/{job_id}`. This replaces manual per-game selection.

The React app uses TanStack Router for addressable workflows and TanStack Query for server state.
Recharts renders progress trends. `WorkspaceContext` retains only import and transient selection
state plus the offline analysis cache.

### API surface

| Method | Path | Role |
| --- | --- | --- |
| `GET` | `/api/health` | Liveness check for Render and local dev |
| `GET` | `/api/sample` | Bundled sample PGN for empty workspaces |
| `POST` | `/api/analyze` | Paste/import PGN and persist analyses |
| `POST` | `/api/feedback` | Helpful / not-helpful ratings on a moment |
| `GET` | `/api/monitoring` | JSONL-derived quality summary for `/quality` |
| `POST` | `/api/games/sync` | Start or resume full-history sync job |
| `GET` | `/api/games/sync/{job_id}` | Poll sync progress |
| `GET` | `/api/games/{platform}/{username}` | Load persisted analyses for the library |
| `GET` | `/api/players/{platform}/{username}` | Player profile and weakness memory |
| `POST` | `/api/training/sessions` | Create a practice session from stored mistakes |
| `GET` | `/api/training/sessions/{id}` | Fetch session positions |
| `POST` | `/api/training/sessions/{id}/attempts` | Grade a move and update review schedule |
| `GET` | `/api/progress/{platform}/{username}` | Rating, theme accuracy, mastery, transfer trends |

There is no public `/api/chat` or coach-session route in the shipped product. PydanticAI and the
LLM judge run only through offline evaluation commands documented in the README.
