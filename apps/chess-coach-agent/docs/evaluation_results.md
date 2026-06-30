# Evaluation Results

Evaluation was run on 2026-06-20 with the hand-written datasets in `backend/data/eval/`.

## Layer overview

| Layer | Module | Latest result |
| --- | --- | --- |
| Foundation | `evaluation.py` | **11/11** theme detection on varied fixtures |
| Retrieval | `retrieval_evaluation.py` | BM25 production default (see below) |
| Analysis copy | `judge_evaluation.py` | Grounded format **5.5/6** after prompt tuning |
| Agent | `agent_evaluation.py` | **10/10** offline scenario pass rate (TestModel + heuristic judge) |

The deterministic critical-moment suite was expanded on 2026-06-21 from two manually scored
coaching cases to 11 regression positions. It currently detects the expected theme in **11/11**
positions, including loose queens, rooks, bishops, and knights; repeated opening queen moves;
king-safety neglect for both colors; and immediate tactical collapses. The original two cases remain
the manually reviewed subset used for the published coaching-quality result below.

## Retrieval Selection

The retrieval benchmark now contains 20 hand-authored queries. It also measures source correctness
and median local latency. Exact machine timings vary, so the checked-in JSON is the authoritative
run artifact.

| Strategy | Hit rate at 3 | MRR | Source correctness | Median latency |
| --- | ---: | ---: | ---: | ---: |
| Title-only | 0.35 | 0.35 | 0.65 | 0.084 ms |
| BM25 | 0.95 | 0.858 | 0.95 | 0.124 ms |
| Vector | 0.95 | 0.725 | 0.95 | 0.338 ms |
| Hybrid RRF | 1.00 | 0.850 | 1.00 | 0.671 ms |

Hybrid did not qualify because it missed BM25 on MRR and exceeded twice BM25's median latency.
BM25 therefore remains the measured production default. This decision is made by code, not a
hard-coded claim: hybrid becomes the default only when it equals or exceeds BM25 on hit rate and
MRR while remaining below the two-times latency guardrail. See
`backend/data/eval/retrieval_results.json` for all per-query ranks.

## MiniMax Judge and Prompt Tuning

The judge scored theme correctness, factual grounding, and coaching quality from 0 to 2 each.

| Format | Average score | Pass rate |
| --- | ---: | ---: |
| Concise | 3.0/6 | 50% |
| Grounded, before tuning | 5.0/6 | 100% |
| Grounded, after tuning | 5.5/6 | 100% |

MiniMax identified that the opening-drift answer did not explicitly connect repeated queen moves to
lost development tempi and delayed king safety. The explanation and drill were rewritten around that
feedback. On the next judge run, opening drift improved from `4/6` to `6/6`.

## Agent scenario evaluation

Ten hand-authored scenarios in `agent_scenarios.jsonl` evaluate the PydanticAI agent's tool routing
and structured answers using course-style `JudgeFeedback` models in `judge.py`. The offline run uses
expected tool lists plus a heuristic judge so CI stays credential-free:

| Metric | Result |
| --- | ---: |
| Scenarios | 10 |
| Offline pass rate | 100% |

Add `--live` to score real OpenRouter agent runs against the same scenarios.

Commands:

```bash
cd backend
uv run python -m chess_coach_agent.agent_evaluation --dataset data/eval/agent_scenarios.jsonl
uv run python -m chess_coach_agent.retrieval_evaluation --dataset data/eval/retrieval.jsonl --output data/eval/retrieval_results.json
uv run python -m chess_coach_agent.judge_evaluation --dataset data/eval/critical_moments.jsonl --tune
```

The dataset is intentionally small. Scores establish that the workflow functions; they are not a
claim of general chess-coaching accuracy.
