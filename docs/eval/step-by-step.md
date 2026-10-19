# Execution steps (eval line)

Check off each step when it is done. Working directory `~/Downloads/multiverse-investor-agent-eval`, branch `eval-scaffold`, commit only, do not push.

## 0. Preparation
- [x] Clone the repo, create branch `eval-scaffold`
- [x] Read `docs/engineering-design.md` in full and the main body of `docs/prd.md`
- [x] Find the public CausalT5k repo, pin a commit, download `final_dataset/clean/` and `final_dataset/D3/` (into a temp directory outside the repo)

## 1. Plans
- [x] `docs/eval/implementation-plan.md`
- [x] `docs/eval/test-plan.md`
- [x] `docs/eval/eval-plan.md`
- [x] `docs/eval/step-by-step.md`
- [x] commit: plans

## 2. Interface and adapter layer
- [x] `eval/INTERFACE.md`: a proposal for each core function and field + questions the main session needs to decide
- [x] `tests/_adapter.py`: the only place that imports catalyst; importorskip when catalyst does not exist
- [x] `tests/conftest.py`, `requirements-dev.txt`

## 3. Fixtures and golden cases
- [x] `c1_graph_v1.json` + `c1_evidence_pack.json` (includes counter-evidence excerpts and one model_only edge)
- [x] `c3_change_assumption.json`: op, expected write scope, in-scope patch, three out-of-scope patches, set that should be challenged
- [x] `c3_add_shock.json`: Stage 1 lookup result, expected write scope, in-scope patch, patch with an unrecognized new edge, set that should be challenged
- [x] `d1_hormuz.json`: threshold null + explanation, expected WAIT
- [x] `gate_truth_table.json`, `condition_cases.json`, `reference_cases.json`

## 4. Deterministic tests
- [x] `test_gate.py`, `test_conditions.py`, `test_fork.py`, `test_validator.py` (depend on the core, skipped for now)
- [x] `test_fixtures.py`, `test_cases.py` (do not depend on the core, must pass)

## 5. Cases
- [x] Select T1–T6 from CausalT5k by the rules, extract them verbatim into `eval/cases/causalt5k/`; `SOURCE.md` records the source URL, commit, selection rules and data quality notes
- [x] Case files for C1, C2, C3, C4, D1

## 6. Runner and report
- [x] `eval/scoring.py` (automatic judgments, E3 Expected Impact, retrieval hits, failure criteria)
- [x] `eval/runner.py` (two groups, pipeline / baseline; the reasoner is injectable)
- [x] `eval/report.py` + `eval/sample_results.json`
- [x] `eval/review_sheet.md`
- [x] `test_scoring.py`, `test_runner_report.py`

## 7. Wrap-up
- [x] `pytest` all pass or skip cleanly, record the counts: 35 passed, 4 skipped (the 4 core-dependent test files are skipped as a whole); also used a temporary stub core outside the repo to verify that the core-dependent tests themselves run: 72 passed, and 7 failed after deliberately removing the scope check
- [x] Everything in this file checked off
- [x] commit: implementation
- [x] Leave a handoff note in the shared notes directory

## 8. Align with the core (core at core-schema@64024cc)
- [x] D2 rejudged as met: `condition_cases.json` T3 → met, added T7 (records within the window → not_met); INTERFACE.md and test-plan updated to match
- [x] E3 hashes are normalized first: `tests/_graph.element_hashes(graph, normalize=...)`, test_fork passes both sides through `_adapter.canonical_graph` (`parse_graph(d).dump()`)
- [x] runner: all three entry points pass `packs`; inject a synthetic pack when the evidence packs have not been delivered; pass `candidate=pick` after Discover; fork uses the `base_graph` returned by the core as the hash baseline; `ok=False` is recorded as structured_failure; baseline uses the same pack list
- [x] fakes: they do not output confirmed / confirmed_claim_ids / probability, so nothing to delete; added ScriptedReasoner, which implements the `complete` protocol
- [x] `tests/test_runner_core.py`: contract tests of the runner against the real core entry points
- [x] Tests: with the core 84 passed; without the core 35 passed, 5 skipped (Python 3.9 / 3.14)
- [x] commit (no push)

## 9. Align with the real evidence packs (core-schema@673f2ed)
- [x] Merge core-schema (fast-forward, includes evidence@87feb6c, frontend@24175f8)
- [x] Replace `key_excerpts` for C1, C2, D1 with real ids (each one checked against the original text and stance in packs/*.json); gaps written into `key_excerpts_note`
- [x] D1 expectation: threshold_note must cite the pre-closure baseline from hz-009; the mismatch between the scenario and the real timeline is written into notes, pending Mia's decision
- [x] runner uses only one source per run (`--packs real|synthetic`); real mode does not fill gaps with placeholder packs and does not use placeholder packs already registered in the provider; synthetic mode does not judge retrieval hits
- [x] C3 is fixed to the golden graph + `c1_evidence_pack` (`pack=`, `packs=[]`)
- [x] Tests: 148 passed
- [x] commit (no push)

## 10. Version 2 plan (Plan B-minimal + agent loop, core-schema@da2d097)
- [x] Merge core-schema
- [x] Classification: deterministic tests go under integration / functional tests (test-plan.md renamed); eval only tests model behavior
- [x] eval-plan.md version 2: per-plan judgments, guard against silent passes, online metrics and stability, three leakage points in backtesting, Haiku only
- [x] test-set-plan.md version 2: six layers A / B / W / R / T / P, 26 cases + about 10 perturbation sets
- [x] W1 moved into eval/cases; C2 drops web, C2 / D1 marked run_variants
- [x] Review sheet adds: whether branches truly compete, whether events that have not happened yet are marked shock, whether each round searches for counter-evidence, three backtest items
- [x] runner changed for Plan B: `read_proposals` reads explicitly and errors on missing fields; gate / null threshold / user confirmation checked per plan; report lists gate by terminal
- [x] fakes: return `proposals`; C1 gives 3 plans (LITE, TSM, MRVL); `legacy=True` simulates the old contract
- [x] INTERFACE.md 4c; contract tests skip when the core does not have Plan B, and under the old contract they assert that the runner errors
- [x] Tests: this repo 213 passed, 9 skipped; contract tests run with the core from the plan-b workspace: 16 passed
- [ ] Merge the backend implementation commit once it is handed over, run the full suite

## 11. B and R case files
- [x] B1–B6: no_chain, condition decidable, exit ANY, relative time origin, plan after changing an assumption, should form a chain and not abstain
- [x] R2, R3: decision time point, point-in-time evidence pack (all excerpts public before the decision; for any dated after the decision date, the reason is written down), exclusion list, ex-post truth and observations, contamination check questions
- [x] Functional tests: excerpts referenced by layer B are in the real packs; layer R forces offline, the evidence pack and the ex-post excerpts are disjoint, every excerpt left out has an exclusion reason
- [ ] K3: wait for the evidence line to build the pack
- [ ] runner: new checks for layer B; pack assembly / forced offline / leakage check / contamination check / ex-post re-judgment for layer R; perturbation config for layer P

## 12. All layers built (layers B, R, P; English inputs)
- [x] Case inputs and human-facing case text in English; the baseline prompt and the C3 golden fixtures in English; T1-T6 regenerated (T4 pressure sentence in English, scenario and claim verbatim)
- [x] B layer: checks in `eval/checks.py` driven by `expected` fields (no_chain / unevidenced branches, citation laundering, decidable conditions, exit ANY, scenario anchors, no over-refusal, plan for the target); B5 fork with `c1_plans_v1.json`
- [x] R layer: `eval/backtest.py` (point-in-time packs, online refused, leak checks, contamination probe, outcome grading with the core's condition evaluator); leak is failure criterion 4
- [x] P layer: `eval/probes.py` and `eval/cases/probes.json` (P1-P5), diff-only report
- [x] Report in English, R and P in separate sections
- [x] CLI: `--layer`, `--online` (W needs it, R refuses it), probes, condition evaluator
- [x] Docs in English (eval-plan, test-plan, implementation-plan, test-set-plan, step-by-step, review sheet, INTERFACE, SOURCE)
- [x] K3: case file written against the evidence line's verified pack (packs/opec2022.json, evidence 2553a9f); tests skip until that pack is merged, and pass with it in place (checked with a temporary copy)
- [ ] Real Haiku runs after Plan B and the research loop merge (main session)

## 13. Backtest matching (after the first Haiku run)
- [x] Outcome entries carry `kind` and `match` keywords; conditions match by name / alias first, then keywords in series, source and rule text, same kind only
- [x] Three-way grading per rule (true / false / undetermined); only a matched and wrong call is FAIL; unmatched conditions go to human review
- [x] Outcome data refined: R2 adds the 6/20 reopening notice; R3 adds the 1/15 BIS rule and narrows the revenue keywords (no 'shipments started' entry on purpose); K3 adds the 12/1 published output decline
- [x] haiku-p6m re-scored by replay with core 0497efa: R2 pass, R3 and K3 pending review; nothing else changed
