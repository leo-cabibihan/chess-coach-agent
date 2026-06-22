# Evaluation Results

Evaluation was run on 2026-06-20 with the hand-written datasets in `backend/data/eval/`.

The deterministic critical-moment suite was expanded on 2026-06-21 from two manually scored
coaching cases to 11 regression positions. It currently detects the expected theme in **11/11**
positions, including loose queens, rooks, bishops, and knights; repeated opening queen moves;
king-safety neglect for both colors; and immediate tactical collapses. The original two cases remain
the manually reviewed subset used for the published coaching-quality result below.

## Retrieval Selection

| Strategy | Hit rate at 3 | Mean reciprocal rank |
| --- | ---: | ---: |
| Title-only baseline | 0.25 | 0.25 |
| BM25 full-text | 1.00 | 1.00 |

BM25 won all eight queries and is the default used by `retrieve_notes`.

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

Commands:

```bash
cd backend
uv run python -m chess_coach_agent.retrieval_evaluation --dataset data/eval/retrieval.jsonl
uv run python -m chess_coach_agent.judge_evaluation --dataset data/eval/critical_moments.jsonl --tune
```

The dataset is intentionally small. Scores establish that the workflow functions; they are not a
claim of general chess-coaching accuracy.
