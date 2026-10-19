## Scorecard: haiku-p7 (offline + online)

**Total: 78.3 / 100** = code 91.6 x 0.5 + LLM judge 6.5/10 x 0.5 · trusted · model anthropic:claude-haiku-5-5 · prompt p7 · 2026-10-19

| Metric | Weight | Passed / judged | Points | Failed cases | Not judged yet |
| --- | --- | --- | --- | --- | --- |
| Discipline | 20 | 13 / 13 | 20.0 | - | 1 |
| Refusal calibration | 20 | 11 / 12 | 18.3 | T2 | 2 |
| Decidable conditions | 20 | 48 / 53 | 18.1 | R2, W1 | 0 |
| Grounding | 15 | 51 / 75 | 10.2 | B1, B3, B4, B6, C1, C2, D1, K3, R2, R3, W1 | 0 |
| Fork integrity | 15 | 18 / 18 | 15.0 | - | 0 |
| Research lift | 10 | 1 / 1 | 10.0 | - | 0 |

**LLM judge (overall quality, claude-sonnet-5-5): 6.5 / 10** over 19 cases; poor: B2, T2. It counts for 0.5 of the total.

Baseline on the same refusal units: baseline 6/7, pipeline 6/7.

Not judged yet (excluded from the score):

- Discipline: K3: contaminated backtest (the model knew the outcome)
- Refusal calibration: C3: reasoning pending human review; B5: reasoning pending human review
