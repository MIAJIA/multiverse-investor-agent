## Scorecard: haiku-p6m (offline)

**Total: 77.2 / 100** = code 89.5 x 0.5 + LLM judge 6.5/10 x 0.5 · trusted · model anthropic:claude-haiku-5-5 · prompt p6 · 2026-10-19

| Metric | Weight | Passed / judged | Points | Failed cases | Not judged yet |
| --- | --- | --- | --- | --- | --- |
| Discipline | 20 | 10 / 10 | 20.0 | - | 2 |
| Refusal calibration | 20 | 11 / 12 | 18.3 | T2 | 2 |
| Decidable conditions | 20 | 40 / 49 | 16.3 | B2, B3, B4, K3, R2 | 0 |
| Grounding | 15 | 43 / 59 | 10.9 | B1, B2, B3, B4, C1, D1, K3, R2, R3 | 0 |
| Fork integrity | 15 | 18 / 18 | 15.0 | - | 0 |
| Research lift | 10 | n/a | n/a | - | 0 |

**LLM judge (overall quality, claude-sonnet-5-5): 6.5 / 10** over 18 cases; poor: B2, B3, T2. It counts for 0.5 of the total.

Metrics with no judged units are left out and the score is scaled over the remaining 90 points of weight.

Baseline on the same refusal units: baseline 6/7, pipeline 6/7.

Not judged yet (excluded from the score):

- Discipline: R3: backtest undetermined, pending human review; K3: backtest undetermined, pending human review
- Refusal calibration: C3: reasoning pending human review; B5: reasoning pending human review
