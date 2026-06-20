# Manual Evaluation

The two ground-truth cases were authored and reviewed manually on 2026-06-20. They were not generated
by an LLM. The reviewer checked the board position, move sequence, expected theme, and required lesson
before running either automated evaluator.

| Case | Human expectation | Manual result after tuning |
| --- | --- | --- |
| `loose_piece_fixture` | Identify the exposed queen and teach an attacks/defenders scan | Pass; correct theme and practical loose-piece drill. The exact rook attacker could be stated more explicitly. |
| `opening_drift_fixture` | Connect three queen moves with lost development and delayed king safety | Pass; the revised answer names the cumulative queen detour, development tempi, castling, and a tailored replay drill. |

Manual verdict: **2/2 acceptable**, with one documented improvement opportunity. The LLM judge is a
second opinion, not a replacement for this review.
