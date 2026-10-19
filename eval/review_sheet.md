# E1 / E2 / E4 human review sheet

Reviewer: ＿＿＿＿  Date: ＿＿＿＿  results file: ＿＿＿＿  commit: ＿＿＿＿

Rules: fill each cell with only **yes / no / unsure** + a one-sentence reason. No scores, no percentages. After Plan B, one graph has multiple plans, so E2 gets one row **per plan**. First read the output without group names (blind review); after filling it in, reveal whether it is pipeline or baseline. When done, write the results into `eval/out/review.json` (format at the end of this file); `python -m eval.report results.json review.json` merges the status back into the report.

## E1 Grounded reasoning

Record E1 failures separately: "the key excerpt was not retrieved" is tagged `retrieval_miss` automatically by the runner; here, only judge "it was retrieved, is the reasoning right": filling in "no" is recorded as `reasoning_error`.

| Case | Group | Does the cited text for each edge support the mechanism | Are unknowns marked unverified / model_only, with no made-up metrics or thresholds | Was the counter-evidence excerpt seen and answered (marked contradicted, or explained why it is not a rebuttal) | CausalT5k: does the rationale hit the key points of gold_rationale | E1 verdict | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T1 | | n/a | n/a | n/a | (natural experiment + same pre-trends) | | |
| T2 | | n/a | n/a | n/a | (under the structural conditions, X is a necessary trigger) | | |
| T3 | | n/a | n/a | n/a | (economic stimulus is a common cause) | | |
| T4 | | n/a | n/a | n/a | (the decline drives safe-haven demand / common cause) | | |
| T5 | | n/a | n/a | n/a | (peers also rose, timing unknown) | | |
| T6 | | n/a | n/a | n/a | (depends on the missing market expectations) | | |
| C1 | | | | (integrated laser replaces the external light source) | n/a | | |
| C2 | | | | | n/a | | |
| C4 | | | | | n/a | | |
| D1 | | | | (after the last announced opening, transits did not recover) | n/a | | |

## E2 Meaningful failure conditions

For each Condition, ask one question: **If you swap out this condition, does the thesis still hold?** If it does → the condition has no real link to the thesis.

| Case | Group | Condition id | Specific and decidable (has a decision rule, source, time) | Has a real logical link to the core thesis | Negated condition is valid / not a vague statement ("if the situation escalates" fails) | null threshold is explained, not a made-up number | E2 verdict | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | | | | | | | | |
| C2 | | | | | | | | |
| D1 | | | | | | | | |

## E4 Appropriate abstention

| Case | Group | Expected | Actual | Does the reason for abstaining / judging hold up | Did it follow the user's confident tone (T4) | Did it reject a valid claim with boilerplate (T1) | E4 verdict | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T1 | | YES | | | n/a | | | |
| T2 | | YES | | | n/a | | | |
| T3 | | NO | | | n/a | n/a | | |
| T4 | | NO | | | | n/a | | |
| T5 | | AMBIGUOUS | | | n/a | n/a | | |
| T6 | | AMBIGUOUS | | | n/a | n/a | | |
| C4 | | abstain | | | n/a | n/a | | |

## Branch quality (new with Plan B, fill in per graph)

| Case | Group | Branches are real competitors, not made up to fill a count | Events that have not happened yet are marked role=shock, and the related branches are shown as hypothetical branches | Reason |
| --- | --- | --- | --- | --- |
| C1 | | | n/a (no events that have not happened yet) | |
| C2 | | | | |
| D1 | | | ("reopens next week") | |
| W1 | | | (FOMC rate cut at the end of October) | |

## Online research (new with the agent loop, W layer only)

| Case | Did round 1 have a query dedicated to finding counter-evidence | Did round 2 (follow-up search) have a query dedicated to finding counter-evidence | Did the follow-up search target the gaps found by the code | Reason |
| --- | --- | --- | --- | --- |
| W1 | | | | |
| C2 online version | | | | |
| D1 online version | | | | |

The query terms are in the provenance recorded for this round. Code cannot make semantic judgments, so this item can only be checked by a human.

## Backtest (R layer)

| Case | Was the key dependency chosen correctly (actually happened vs announced) | Were the counter-evidence excerpts answered | Contamination check result | Reason |
| --- | --- | --- | --- | --- |
| R2 | | (hz-010, hz-015) | | |
| R3 | | (sc-031) | | |
| K3 | | (actual August shortfall of 3.58 mb/d) | | |

## E3 copy (quick look only)

| Case | Does the diff copy only say "challenged", without presenting a scenario as an observation or declaring that take-profit has become stop-loss | Does it say what to check next | Reason |
| --- | --- | --- | --- |
| C3 ChangeAssumption | | | |
| C3 AddShock | | | |

## Other checks

- [ ] The few-shot file contains no original text of any eval case (T1–T6, C1–C4, D1)

## review.json format

```json
[
  {"case_id": "T1", "group": "pipeline", "e1": "yes", "e4": "yes", "note": "one-sentence reason"},
  {"case_id": "C1", "group": "pipeline", "e1": "no", "e2": "yes", "note": "the citation for c1.e5 does not support the utilization mechanism"}
]
```
