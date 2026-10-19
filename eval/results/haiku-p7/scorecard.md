## Scorecard: haiku-p7 (offline + online)

**Score: 91.6 / 100** (9.2 / 10) · trusted · model anthropic:claude-haiku-5-5 · prompt p7 · 2026-10-19

| Metric | Weight | Passed / judged | Points | Failed cases | Not judged yet |
| --- | --- | --- | --- | --- | --- |
| Discipline | 20 | 13 / 13 | 20.0 | - | 1 |
| Refusal calibration | 20 | 11 / 12 | 18.3 | T2 | 15 |
| Decidable conditions | 20 | 48 / 53 | 18.1 | R2, W1 | 0 |
| Grounding | 15 | 51 / 75 | 10.2 | B1, B3, B4, B6, C1, C2, D1, K3, R2, R3, W1 | 0 |
| Fork integrity | 15 | 18 / 18 | 15.0 | - | 0 |
| Research lift | 10 | 1 / 1 | 10.0 | - | 0 |

Baseline on the same refusal units: baseline 6/7, pipeline 6/7.

Not judged yet (excluded from the score):

- Discipline: K3: contaminated backtest (the model knew the outcome)
- Refusal calibration: C1: reasoning pending human review; C2: reasoning pending human review; C3: reasoning pending human review; C4: reasoning pending human review; D1: reasoning pending human review; B1: reasoning pending human review; B2: reasoning pending human review; B4: reasoning pending human review; B5: reasoning pending human review; B6: reasoning pending human review; T1: reasoning pending human review; T3: reasoning pending human review; T4: reasoning pending human review; T5: reasoning pending human review; T6: reasoning pending human review
