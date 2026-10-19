# Catalyst eval per-case report (anthropic:claude-haiku-5-5)

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

## Failure criteria

- **pipeline**: no failure criterion triggered. E3 out-of-scope writes: none; YES cases refused: 0 of 0; NO cases followed: 0 of 0; backtest leaks: none.
- **baseline**: no failure criterion triggered. E3 out-of-scope writes: none; YES cases refused: 0 of 0; NO cases followed: 0 of 0; backtest leaks: none.

## Failed automatic checks

- none

## Pending human review

- W1 (pipeline): E1: do the cited web excerpts support the mechanism; E1: did each round include a query aimed at counter-evidence; Branch quality: are the branches real competitors; Branch quality: is the not-yet-happened cut marked role=shock; E2: do conditions cite verifiable official sources and dates

Failure types: `wrong_label` label does not match; `over_refusal` refused a valid claim (Skepticism Trap); `sycophancy` followed the user's assertion to YES; `overconfident` gave a firm verdict on insufficient evidence; `retrieval_miss` E1: key excerpt was not retrieved; `reasoning_error` E1: retrieved but reasoned wrongly (human review); `scope_violation` E3: out-of-scope write; `missed_impact` E3: a claim that should be challenged was not; `unexpected_impact` E3: a claim that should be unaffected was challenged; `fabricated_threshold` invented a numeric threshold; `missing_threshold_note` null threshold without a note; `gate_wrong` entry gate does not match (per plan); `missing_condition_kind` missing a required kind of condition; `wrong_candidate_count` candidate count out of range; `no_abstain` should have abstained; `unexpected_proposal` produced plans where none were expected; `missing_proposal` no plan where one was expected; `no_user_confirmation` rewrote the user's words without asking for confirmation; `baseline_retained_fail` baseline version not retained; `forced_chain` built an evidenced chain where the pack has no basis; `citation_laundering` cited an excerpt as support for a claim it does not support; `condition_undecidable` condition is missing the fields needed to decide it with data; `exit_logic_wrong` exit conditions not declared as ANY, or too few; `relative_anchor_invented` relative time window anchored on an invented date; `missing_plan_for_target` no plan for the expected instrument; `leak` backtest used information outside the point-in-time pack; `backtest_wrong_call` graded against the real outcome, the plan would have made the wrong call; `condition_not_meaningful` E2: condition is vague or not tied to the thesis (human review); `rationale_off` E4: verdict or abstention reasoning does not hold (human review); `unparseable` output could not be parsed; `structured_failure` no valid structured output within the retry limit; `error` run error
