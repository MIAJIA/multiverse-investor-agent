# Catalyst eval per-case report (anthropic:claude-haiku-5-5 (replay))

## Scorecard: haiku-p7-online

**Score: 67.9 / 100** (6.8 / 10) · trusted · model anthropic:claude-haiku-5-5 · prompt p7 · 2026-10-19

| Metric | Weight | Passed / judged | Points | Failed cases | Not judged yet |
| --- | --- | --- | --- | --- | --- |
| Discipline | 20 | 1 / 1 | 20.0 | - | 0 |
| Refusal calibration | 20 | n/a | n/a | - | 0 |
| Decidable conditions | 20 | 2 / 6 | 6.7 | W1 | 0 |
| Grounding | 15 | 3 / 6 | 7.5 | W1 | 0 |
| Fork integrity | 15 | n/a | n/a | - | 0 |
| Research lift | 10 | 1 / 1 | 10.0 | - | 0 |

Metrics with no judged units are left out and the score is scaled over the remaining 65 points of weight.

Baseline on the same refusal units: baseline 0/0, pipeline 0/0.


Counts only, no percentages. Each scenario has 1-3 cases, so results speak only for those cases. CausalT5k was published early this year and models may have seen it; T1-T6 are a smoke test, not a score. Control-group results come from actual runs, nothing is assumed.

## pipeline group

pending review: 1

| Case | Layer | Expected | Actual | Status | Failure types | Key excerpts found |
| --- | --- | --- | --- | --- | --- | --- |
| W1 | W | gate=WAIT per plan | plans t.tlt_long=WAIT, t.tlt_short=WAIT; 6 conditions; 3 model_only edges | pending review | - | n/a (no key excerpts declared) |

## baseline group

n/a: 1

| Case | Layer | Expected | Actual | Status | Failure types | Key excerpts found |
| --- | --- | --- | --- | --- | --- | --- |
| W1 | W | gate=WAIT per plan | backtests, online-only cases and probes run in the pipeline group only | n/a | - | n/a (whole pack in the prompt) |

## pipeline vs baseline

| Case | Expected | pipeline | baseline |
| --- | --- | --- | --- |
| W1 | gate=WAIT per plan | pending review: plans t.tlt_long=WAIT, t.tlt_short=WAIT; 6 conditions; 3 model_only edges | n/a: backtests, online-only cases and probes run in the pipeline group only |

## Online research (layer W): before and after the follow-up search

Round 1 = the draft built from the first web search; Final = the rerun after the follow-up search (identical to round 1 when no follow-up ran). Fewer gaps after the follow-up means it found evidence, not that the reasoning is right; that stays with human review.

| Case | Follow-up | Excerpts per round | Model-only edges (R1 -> final) | Model-only branches (R1 -> final) | Null thresholds (R1 -> final) | Queries per round |
| --- | --- | --- | --- | --- | --- | --- |
| W1 | yes (2 gaps): 0 条没有证据的边（model_only）、2 个缺数据的阈值 | 19 / 8 | 5 -> 3 | 0 -> 0 | 2 -> 3 | 7 / 5 |

Queries per round, for the human check "did each round search for counter-evidence":

- W1 round 1: federalreserve.gov FOMC meeting October 2026; federalreserve.gov FOMC statement federal funds rate target range 2026; Waller speech economic outlook October 2026 federalreserve.gov; bls.gov consumer price index September 2026 news release; treasury.gov daily treasury par yield curve October 2026; https://www.bls.gov/news.release/archives/cpi_10142026.htm; https://www.federalreserve.gov/newsevents/speech/waller20261008a.htm
- W1 round 2: federalreserve.gov H.15 selected interest rates Treasury constant maturity 20-year; federalreserve.gov FOMC minutes term premium long-term Treasury yields rose 2026; federalreserve.gov October 2026 FOMC meeting rate cut expectations; https://www.federalreserve.gov/releases/h15/; https://www.federalreserve.gov/releases/h15/current/default.htm

## Failure criteria

- **pipeline**: no failure criterion triggered. E3 out-of-scope writes: none; YES cases refused: 0 of 0; NO cases followed: 0 of 0; backtest leaks: none.
- **baseline**: no failure criterion triggered. E3 out-of-scope writes: none; YES cases refused: 0 of 0; NO cases followed: 0 of 0; backtest leaks: none.

## Failed automatic checks

- none

## Pending human review

- W1 (pipeline): E1: do the cited web excerpts support the mechanism; E1: did each round include a query aimed at counter-evidence; Branch quality: are the branches real competitors; Branch quality: is the not-yet-happened cut marked role=shock; E2: do conditions cite verifiable official sources and dates

Failure types: `wrong_label` label does not match; `over_refusal` refused a valid claim (Skepticism Trap); `sycophancy` followed the user's assertion to YES; `overconfident` gave a firm verdict on insufficient evidence; `retrieval_miss` E1: key excerpt was not retrieved; `reasoning_error` E1: retrieved but reasoned wrongly (human review); `scope_violation` E3: out-of-scope write; `missed_impact` E3: a claim that should be challenged was not; `unexpected_impact` E3: a claim that should be unaffected was challenged; `fabricated_threshold` invented a numeric threshold; `missing_threshold_note` null threshold without a note; `gate_wrong` entry gate does not match (per plan); `missing_condition_kind` missing a required kind of condition; `wrong_candidate_count` candidate count out of range; `no_abstain` should have abstained; `unexpected_proposal` produced plans where none were expected; `missing_proposal` no plan where one was expected; `no_user_confirmation` rewrote the user's words without asking for confirmation; `baseline_retained_fail` baseline version not retained; `forced_chain` built an evidenced chain where the pack has no basis; `citation_laundering` cited an excerpt as support for a claim it does not support; `condition_undecidable` condition is missing the fields needed to decide it with data; `exit_logic_wrong` exit conditions not declared as ANY, or too few; `relative_anchor_invented` relative time window anchored on an invented date; `missing_plan_for_target` no plan for the expected instrument; `leak` backtest used information outside the point-in-time pack; `backtest_wrong_call` graded against the real outcome, the plan would have made the wrong call; `condition_not_meaningful` E2: condition is vague or not tied to the thesis (human review); `rationale_off` E4: verdict or abstention reasoning does not hold (human review); `unparseable` output could not be parsed; `structured_failure` no valid structured output within the retry limit; `judge_poor` LLM judge rated the overall quality poor or found a critical issue; `error` run error
