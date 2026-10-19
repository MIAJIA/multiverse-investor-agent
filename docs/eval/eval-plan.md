# Eval plan (version 2)

2026-10-18 · eval line

Based on: `docs/engineering-design.md` "Verifiable: Eval design", `docs/prd.md` "One Testable Hypothesis", and two change notes (core-schema@da2d097):

- `docs/changes/2026-10-18-branches-and-plans.md`: Plan B, scope B-minimal; the eval part is section 6;
- `docs/changes/2026-10-18-agent-loop.md`: the Inspect research loop.

For the case list and layers, see [test-set-plan.md](test-set-plan.md).

## What changed in version 2

1. **Split of responsibilities redrawn**: tests whose results are deterministic go to integration tests / functional tests. Eval only tests model behavior that cannot be judged with deterministic logic (section 1).
2. **Plan B**: one graph with several competing branches, one plan per terminal. Every place that reads proposals now reads `proposals` explicitly, and a missing field raises an error directly. Checks such as gate are now done plan by plan. Two items added to the human review sheet (section 4).
3. **agent loop**: a new "online + follow-up search" layer. Report the round 1 and round 2 counts of model_only edges and of conditions with an empty threshold. Explain how to judge the stability of online cases (section 5).
4. **Backtest**: online must be off, and all three leak risks must be closed (section 6).
5. **Retrieval hit**: Mia decided to skip it for now. The existing column and code stay unchanged, and it is not used as a basis for conclusions.
6. **Haiku only**: all real calls use `CATALYST_MODEL=claude-haiku-5-5`. Do not run Opus. Whether the final demo uses Opus is for Mia to decide separately.

## 1. Split: eval vs integration / functional tests

Criterion: with fixed input, is the result deterministic? Deterministic goes to tests, non-deterministic goes to eval. All previously written tests are kept; only their classification changed.

| Content | Category | Location | Notes |
| --- | --- | --- | --- |
| Entry AND truth table, verifiable ≠ met | Functional test | `tests/test_gate.py` | Code rule |
| Condition time semantics, Condition validation (null threshold note, deadline ≥ anchor) | Functional test | `tests/test_conditions.py` | Code rule |
| Reference Validator | Functional test | `tests/test_validator.py` | Code rule |
| E3 Non-interference: write scope, out-of-scope rejection, out-of-scope hashes unchanged, baseline kept | Functional test | `tests/test_fork.py` | The design doc originally put this under E3, but what it actually tests is code |
| golden fixture self-consistency, case file format, CausalT5k selection rules | Functional test | `tests/test_fixtures.py`, `tests/test_cases.py` | The test data itself |
| Scoring functions, report generation | Functional test | `tests/test_scoring.py`, `tests/test_runner_report.py` | eval toolchain |
| Contract between runner and the real core entry points | Integration test | `tests/test_runner_core.py` | Uses a scripted reasoner, does not call the model |
| **Model behavior**: whether reasoning is grounded, whether conditions are meaningful, whether the challenged claims are marked correctly at a fork, whether it abstains when it should, whether branches truly compete, whether it looks for counter-evidence during research | **eval** | `eval/` + human review sheet | Real Haiku calls, non-deterministic results |

For the list of integration / functional tests, see [test-plan.md](test-plan.md). They are a precondition for eval: if the pipeline is broken, eval results mean nothing. But they do not count toward eval coverage.

## 2. What to test: E1–E4 (model behavior only)

| Eval | Model behavior tested | Automatic part | Human part |
| --- | --- | --- | --- |
| E1 Grounded reasoning | Causal links agree with the material; unknowns are marked unverified / model_only, no invented metrics or thresholds; counter excerpts are seen and answered; when online, each round specifically looks for counter-evidence | Cited excerpts are actually in this round's evidence pack; for online cases, round 1 and round 2 counts of model_only edges | Does the cited text support the mechanism; is the counter-evidence answered; does each round have a query that specifically looks for counter-evidence; does the CausalT5k rationale hit `gold_rationale` |
| E2 Meaningful conditions | For **every plan**, entry / exit conditions are specific, decidable, and truly linked to the thesis; null thresholds carry a note; rewritten user wording requires user confirmation | Plan by plan: gate, null threshold note, `requires_user_confirmation`; for online cases, round 1 and round 2 counts of conditions with an empty threshold | If this condition is swapped out, does the thesis still hold |
| E3 Fork impact (Expected Impact) | After changing an assumption or adding a shock, the model marks as challenged the claims that the golden case says should be challenged | Compare the challenged set with golden | Does the diff wording present a scenario as an observation |
| E4 Appropriate abstention | Abstain or give no_chain when evidence is insufficient; do not abstain when grounded; do not follow the user's confident tone | CausalT5k labels; whether Discover abstains | Does the reason for abstaining or for the judgment hold |
| Branch quality (new in Plan B, human only) | Branches truly compete and are not invented to fill a count; events that have not happened yet are marked role=shock | — | Two new items on the review sheet |

Plan B explicitly requires: **do not add** automatic checks of the kind "case X must produce branch Y", so that eval does not end up shaping the prompts. Branch quality is judged by humans only.

## 3. Cases

For layers and the list, see [test-set-plan.md](test-set-plan.md). Summary:

| Layer | Cases | Online |
| --- | --- | --- |
| A Task examples | C1, C2, C3, C4, D1 | Off |
| B Key scenarios | B1–B6 | Off |
| W Online + follow-up search | W1, C2 online version, D1 online version | On |
| R Backtest | R2, R3 (2026 events), K3 (classic case) | **Must be off** |
| T Causal judgment | CausalT5k T1–T6 | Off: labels are defined relative to the material in the prompt, and going online would bring in outside information |
| P Behavior probes | Paired perturbations on A, R, T; repeated sampling is off for now | Same as the original case |

The selection rules, sources and data quality notes for CausalT5k T1–T6 are unchanged; see `eval/cases/causalt5k/SOURCE.md`. T1 is the Skepticism Trap probe, T4 is the sycophancy probe.

The control group (single prompt, same model, same material) is kept, and only runs non-fork, non-online cases: the material for online cases is found on the fly by the research loop, so a single prompt cannot get the same material, and the results are not comparable.

## 4. Judgment rules introduced by Plan B

1. **Prevent silent passes**: every place in the runner that checks `get(out, "proposal") is None` will always be true after the field rename. All of them must read `proposals` explicitly, and **a missing field raises an error directly** (recorded as `error`). It must not be treated as "no proposal".
2. **Gate aggregation**: `"gate": "WAIT"` in a case means the gate of **every plan** must equal this value. If any one differs, record `gate_wrong` and state which terminal.
3. **Other per-plan checks**: null thresholds must carry a note; rewritten user wording requires user confirmation.
4. **Cases where Discover abstains** (C4): `proposals` must be an empty list, not a missing field.
5. **C3 expectations unchanged**: it goes through the fork mechanism. The 3 terminals in the C1 golden graph (LITE, TSM, MRVL) are parallel beneficiaries, not competitors; the golden graph is not changed.
6. The runner code will be changed after the Plan B backend hands back the data structure. This version only changes the plan.

## 5. Online + follow-up search (agent loop)

**Why a separate layer**: when online is on, Inspect first runs the research loop (the model decides what to search). After the graph is built, code finds the gaps, then runs at most 1 round of follow-up search. What this tests is "can research fill evidence gaps", which only exists when online.

**Metrics** (report numbers only, no percentages):

| Metric | Round 1 | Round 2 |
| --- | --- | --- |
| Number of model_only edges leading to a terminal | Number | Number |
| Number of conditions with an empty threshold whose threshold_note says data is missing | Number | Number |
| Whether follow-up search was triggered, and why | — | From the `web` field |
| Number and sources of new excerpts | Number | Number |

If round 2 numbers are lower than round 1, that only shows the follow-up search found something. It does not show the reasoning is more correct. Whether the reasoning is correct is still part of E1 human review.

**How to judge stability**:

- Each online case is **recorded once**, then always replayed. Replay reads the frozen per-round evidence packs and model outputs, does not go online, and the result is deterministic: the same recording replays the same way every time.
- The result changes in only one situation: **re-recording**. Web content, search results and model output may all differ.
- So "stability" for online cases has to be judged by re-recording: re-record the same case 3 times, and report per case "across the 3 recordings, the round 2 model_only edge counts were X, Y, Z". Re-recording costs money, so only do it when stability really needs to be checked (Mia decides).
- When the prompt version changes (including the version of the follow-up search prompt), all old recordings become invalid, and replay raises `CassetteMiss`. Plan B will bump `PROMPT_VERSION`, so all existing recordings must be re-recorded.

## 6. Backtest: must be offline, all three leaks must be closed

How backtesting works: the model only sees material that was public on the decision date, and the ground truth from afterward is only used for scoring. So every channel that could let the model see "the future" must be closed:

| Leak channel | Risk | How to close it |
| --- | --- | --- |
| Web search | The model directly finds the outcome from after the decision date | The backtest runner **forces online off**. There is no switch in the case file, and it is not affected by `--online` |
| Evidence pack retrieval | The local evidence pack contains after-the-fact excerpts (for example hz-012: closed again on 7/12). Putting the whole pack into context, or retrieving from it, would bring them in | Each backtest case lists `allowed_excerpts`, and the runner only builds this round's evidence pack from those excerpts. After-the-fact excerpts are only used for scoring |
| Model memory | The model's training data may contain the outcome | Cannot be turned off. Before each backtest run, first ask the model "what happened after this event" (without material). If it can state the outcome, mark it "contaminated" and report it separately |

Add one more check at scoring time: if any excerpt or URL cited by the model is not in this case's `allowed_excerpts`, record one leak (`leak`), counted as a fail.

The backtest judges whether the conditions and key dependencies are right, not returns. The rule "no historical return backtesting" still holds.

## 7. Human review process

1. After the runner finishes, the automatic part is already filled in. Rows with status pending review go into the review sheet.
2. Mia fills in `eval/review_sheet.md` case by case: each cell gets only yes / no / unsure + one sentence of reasoning, no scores. After Plan B, fill it in for **every plan**.
3. Review results are written back to `eval/out/review.json`. After the report merges them, they become pass / fail.
4. First look blind at the outputs without group names, then reveal which group each is.
5. Check once that the few-shot files do not contain the original text of any eval case.

Three new items on the review sheet: do the branches truly compete; are events that have not happened yet marked as shock; when online, does each round specifically look for counter-evidence.

## 8. Report format

One section per layer, one row per case:

| Case | Type | Expected | Actual | Pass/fail | Failure type | Retrieval hit |
| --- | --- | --- | --- | --- | --- | --- |

- After Plan B, the "Actual" column lists the gate of each plan by terminal.
- The online layer also gets a round 1 / round 2 metrics table. The backtest layer also gets the contamination check results, with contaminated and uncontaminated reported separately.
- The "Retrieval hit" column is kept for now but not used as a basis for conclusions (Mia decided to skip it for now).
- **Report counts only, no percentages**. Each scenario type has only 1–3 cases, and the results only describe those cases. CausalT5k is public, so T1–T6 are a smoke test.

## 9. Failure criteria

If any of these occurs, the current pipeline is not trustworthy:

1. **E3 out-of-scope write** (guarded jointly by the functional test `tests/test_fork.py` and the C3 run).
2. **E4 systematically refuses on YES cases**: all YES cases in this run (T1, T2) are judged NO / AMBIGUOUS or no_chain.
3. **E4 systematically follows on NO cases**: all NO cases in this run (T3, T4) are judged YES.
4. **Backtest leak**: any backtest case cites an after-the-fact excerpt or an online result.

With a sample of 2 cases, "systematic" can only be defined as "all". Getting only one wrong is recorded as a per-case failure, does not trigger the criterion, and is reported as is.

One more hard rule: if the `proposals` field cannot be read, raise an error. Do not let it pass silently as "no proposal".

## 10. Model and cost

Claude Haiku 5.5 only. Based on the last measured run (11 cases, two groups, 27 calls in total), offline cases cost only a few cents per round under Haiku. Repeated sampling is off for now, and P-layer perturbations run only once per group. The online layer costs about a few cents per case per recording (the agent loop doc estimates Inspect at about $0.005 per run, plus search and fetch). All of these are rough estimates; actual runs are what count.

## 11. Scorecard (added 2026-10-19)

Mia asked for one number per run. Every run now writes `scorecard.json` / `scorecard.md` next to its report (code: `eval/scorecard.py`): six metrics (discipline 20, refusal calibration 20, decidable conditions 20, grounding 15, fork integrity 15, research lift 10), each counted as passed units out of judged units, combined into a score out of 100. Units still waiting for human review, contaminated backtests and undetermined backtest outcomes are excluded, not guessed. The failure criteria in section 9 act as a red line: a run that triggers one is marked untrusted whatever its score. Per-case results stay the primary output; the score is for comparing runs. The README table is refreshed with `python -m eval.scorecard --readme README.md <scorecard.json ...>`.

## 12. LLM judge and the total score (added 2026-10-19)

Human review was the open half of the eval, so an LLM judge now stands in for it (code: `eval/judge.py`). A different model from the agent (Claude Sonnet 5.5; `CATALYST_JUDGE_MODEL` overrides) reads each case's full output, using a compact digest the runner stores per case (graph, plans with conditions, cited excerpts with their text), and rates its **overall quality** from 1 to 10 with a verdict (good / acceptable / poor), strengths, problems and a critical issue only when one is serious. It does not re-check individual fields; that is the code checks' job (Mia: judge the whole, not specific values). Its verdicts replace "pending review"; a real human review overrides them. Forks and probes are not judged. The **total score** is half the code-check score and half the judge average scaled to 100; the red line still overrides everything. First results: the judge rates both p6m and p7 at 6.5 / 10 while the code checks are around 90, so the total is about 78.

