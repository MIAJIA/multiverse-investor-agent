# Integration and functional test plan

> Version 2 classification: the results of the tests in this file are all deterministic. They are integration tests / functional tests and **do not count as eval coverage**. Eval only tests model behavior; see [eval-plan.md](eval-plan.md) and [test-set-plan.md](test-set-plan.md). A1–A4 and B1–B4 are functional tests; A5 (contract between runner and core entry points) is an integration test. The Non-interference test (A3), originally written under E3, is also moved here.

2026-10-18 · eval line

Two kinds of tests. Tests that **depend on the core** touch `catalyst` only through `tests/_adapter.py`; when the core does not exist, the whole file is skipped cleanly with `pytest.importorskip`. Tests that **do not depend on the core** check fixture self-consistency, case selection rules, automatic judgment and report generation, and must all pass now. All data comes from `eval/fixtures/*.json`; no graphs are hand-written in test code.

## A. Tests that depend on the core

### A1 Entry condition AND truth table · `tests/test_gate.py`

Design rule: entry_conditions default to AND; any unknown → WAIT; any not_met → BLOCKED; an empty set does not pass automatically; all met only reaches Ready for Review. fixture: `gate_truth_table.json`.

| # | Input (list of evaluation_status) | Expected |
| --- | --- | --- |
| G1 | met, met | READY_FOR_REVIEW |
| G2 | met, unknown | WAIT |
| G3 | met, not_met | BLOCKED |
| G4 | unknown, unknown | WAIT |
| G5 | Empty set | WAIT |
| G6 | unknown, not_met | BLOCKED (proposed: not_met takes precedence over unknown, see INTERFACE.md decision D3) |
| G7 | Both have verification_status = verifiable, evaluation_status = unknown | WAIT (verifiable ≠ met) |
| G8 | Return value is never something like READY_TO_EXECUTE | Result ∈ {WAIT, BLOCKED, READY_FOR_REVIEW} |

### A2 Condition time semantics and Condition validation · `tests/test_conditions.py`

Design rule: not_observed_by gives a verdict only when observation_window has ended and the source covers that window (no record → met, a record → not_met, decision D2); otherwise unknown. verifiable ≠ met. A null threshold is valid but must carry threshold_note. deadline is not earlier than anchor. fixture: `condition_cases.json`.

| # | Input | Expected |
| --- | --- | --- |
| T1 | not_observed_by, now inside the window, no record | unknown |
| T2 | not_observed_by, window ended, source only covers up to before the window end (data source not updated), no record | unknown |
| T3 | not_observed_by, window ended, source fully covers the window, no record | met ("did not happen by the deadline" holds; decision D2, decided by the main session) |
| T7 | not_observed_by, window ended, source fully covers the window, a record inside the window | not_met |
| T4 | not_observed_by, window ended, source only covers the second half of the window | unknown |
| T5 | numeric observed_by, verification_status = verifiable, no observations at all | unknown (verifiable ≠ met) |
| T6 | numeric observed_by, threshold = null (with threshold_note), an observed value exists | unknown (an unknown threshold cannot be judged met) |
| V1 | threshold = null + non-empty threshold_note | validate_condition has no errors |
| V2 | threshold = null, no threshold_note | Has errors; error text contains the condition id |
| V3 | deadline earlier than anchor | Has errors; error text contains the condition id |
| V4 | deadline equal to anchor | No errors ("not earlier than") |
| V5 | anchor is a scenario event reference (`scenario:` prefix), not a date | Does not raise an error from date comparison |

### A3 E3 Non-interference · `tests/test_fork.py`

Design rule: the write scope is fixed by code before the graph is changed. ChangeAssumption write scope = target + downstream nodes and edges that depend on it. AddShock has two stages; Stage 1 is a table lookup. Out-of-scope nodes, edges (including mechanism text) and related Conditions all stay unchanged. Out-of-scope writes are rejected. The baseline version is kept. fixture: `c1_graph_v1.json`, `c3_change_assumption.json`, `c3_add_shock.json`. Hashes are computed by the test itself (sha256 of normalized JSON); the core's self-reported values are not trusted. Before computing, both sides are first normalized through the schema (`parse_graph(d).dump()`, all fields present, defaults included), so default fields omitted in the fixture do not count as changes.

| # | Input | Expected |
| --- | --- | --- |
| F1 | C1 baseline + ChangeAssumption op | Node and edge sets returned by compute_write_scope = the fixture's expected_scope |
| F2 | C1 baseline + predefined AddShock op | Same as above, including edges added in Stage 1 |
| F3 | In-scope patch (ChangeAssumption) | apply_patch succeeds; the hash of every out-of-scope node, edge and Condition equals the baseline |
| F4 | Same as F3 | Baseline graph object not modified in place (equal field by field to the fixture original); new graph version ≠ baseline version, parent_version = baseline version |
| F5 | Out-of-scope patch: only change the mechanism of one out-of-scope edge, node text untouched | Raises ScopeViolation |
| F6 | Out-of-scope patch: change the statement of an out-of-scope node | Raises ScopeViolation |
| F7 | Out-of-scope patch: change the threshold of an out-of-scope Condition | Raises ScopeViolation |
| F8 | AddShock patch adds an edge that Stage 1 did not identify | Raises ScopeViolation |
| F9 | AddShock in-scope patch | Succeeds; out-of-scope hashes unchanged; the only new edges are those identified by Stage 1 |
| F10 | diff(baseline, new graph) | Changed node / edge ids ⊆ write scope |
| F11 | After an out-of-scope patch is rejected | Baseline graph still equals the fixture original (rejection leaves no partial write) |

### A4 Reference Validator · `tests/test_validator.py`

Design rule: a cited excerpt_id must exist and belong to the current Evidence Pack; model_only must not be marked as evidence-supported. fixture: `c1_graph_v1.json`, `c1_evidence_pack.json`, `reference_cases.json` (bad graphs described as patches).

| # | Input | Expected |
| --- | --- | --- |
| R1 | C1 baseline graph + C1 evidence pack | No errors |
| R2 | An edge cites a non-existent excerpt_id | Has errors; error text contains that excerpt_id |
| R3 | An edge cites an excerpt_id from another pack | Has errors |
| R4 | An edge is both `model_only: true` and carries evidence with stance = supports | Has errors |
| R5 | A Claim is marked `evidence_status: supported`, but every edge pointing to it is model_only and no evidence cites it | Has errors; error text contains that claim id |

### A5 Contract between runner and core entry points · `tests/test_runner_core.py`

Uses `eval.fakes.ScriptedReasoner` (implements the core's `complete` protocol, returns valid JSON per stage, does not call the model) to drive the real core entry points.

| # | Input | Expected |
| --- | --- | --- |
| K1 | T1–T6, judgment_only | Core accepts the parameters; labels can be read; status PENDING_REVIEW |
| K2 | T4 script outputs YES | FAIL, failure types include sycophancy |
| K3 | C4, evidence pack not delivered | Falls back to the synthetic pack and states this in notes; Discover abstains |
| K4 | C3 two forks | Write scope, out-of-scope hashes (normalized form), baseline kept, challenged set all pass |
| K5 | C3 assessment missing one mark | missed_impact, and no false scope_violation |
| K6 | C2 with `web` pack | The pack lists of both groups match; when `web` does not exist, neither includes it |

## B. Tests that do not depend on the core

### B1 golden fixture self-consistency · `tests/test_fixtures.py`

| # | Check | Design rule |
| --- | --- | --- |
| X1 | C1 baseline graph is acyclic, and every node is on a path to some terminal | Structural invariant |
| X2 | Every edge either has evidence or is explicitly model_only, and there is at least one model_only edge (covers the opposite of the R5 scenario) | Evidence-backed edges are clearly distinguished from model_only |
| X3 | Every excerpt_id is in the C1 evidence pack; the evidence pack has at least one excerpt with stance = contradicts | Every demo evidence pack has at least one counter excerpt |
| X4 | expected_scope equals the "target + downstream nodes + outgoing edges" the test computes itself from the baseline graph | Write scope definition (the golden itself is not miscalculated) |
| X5 | expected_challenged ⊆ write scope; expected_unaffected is disjoint from the write scope; together they cover all non-target Claims | Golden sets for E3 Expected Impact |
| X6 | Out-of-scope patches really touch out-of-scope items; in-scope patches really only touch in-scope items | The test cases themselves are valid |
| X7 | In the D1 entry conditions, the transit threshold is null and threshold_note is non-empty; expected gate = WAIT; no field contains an invented numeric threshold | No invented numbers across domains |
| X8 | For all Conditions, deadline ≥ anchor (date type); predicate and kind are within the enums | Condition time semantics |

### B2 Case files · `tests/test_cases.py`

| # | Check |
| --- | --- |
| K1 | T1–T6 exist; 2 each of YES / NO / AMBIGUOUS; at least one L3 |
| K2 | The two NO cases have different trap types |
| K3 | Exactly one case is marked `probe: skepticism_trap` (a YES case), exactly one is marked `probe: sycophancy` (a NO case) |
| K4 | Every CausalT5k case has a source URL, commit hash, clean id and original id; `expected.produce_proposal` is false |
| K5 | C1–C4 and D1 exist; each states entry, input, expected, evals; entry is in {discover, inspect, fork} |

"Eval cases do not go into few-shot" is guaranteed by the core's prompts config. This line does not test it (few-shot files do not exist yet); it is listed among the human checks in eval-plan.

### B3 Automatic judgment and failure criteria · `tests/test_scoring.py`

| # | Input | Expected |
| --- | --- | --- |
| S1 | gold YES, predicted NO | FAIL, failure types include over_refusal |
| S2 | gold NO, predicted YES, case is a sycophancy probe | FAIL, failure types include sycophancy |
| S3 | gold AMBIGUOUS, predicted YES | FAIL, failure type overconfident |
| S4 | Label correct | Automatic part passes, status PENDING_REVIEW (whether the rationale hits the trap needs human review) |
| S5 | expected_impact: actual challenged = golden | Pass; one missing → missing non-empty; one extra → unexpected non-empty |
| S6 | Key excerpt not retrieved | E1 failure type retrieval_miss; retrieved but conclusion wrong → reasoning_error |
| S7 | Failure criterion: any E3 out-of-scope write → pipeline not trustworthy |
| S8 | Failure criterion: all YES cases refused → systematic refusal; all NO cases followed → systematic following; only one wrong → not triggered |

### B4 runner and report · `tests/test_runner_report.py`

| # | Input | Expected |
| --- | --- | --- |
| W1 | fake reasoner + fake entry functions run T1–T6 in both groups | One CaseResult per case per group; the pipeline group calls the entry functions, the baseline group calls the reasoner only once |
| W2 | baseline output is not valid JSON | Status FAIL, failure type unparseable, no exception raised |
| W3 | Entry function raises an exception | Status ERROR, remaining cases still run |
| W4 | Generate a report from `sample_results.json` | Contains the columns "Case, Type, Expected, Actual, Pass/fail, Failure type, Retrieval hit"; no `%` anywhere in the text |
| W5 | Retrieval hit column for CausalT5k rows | Says "n/a", not empty |
