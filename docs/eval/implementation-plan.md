# Eval scaffold · implementation plan

2026-10-18 · eval line (branch `eval-scaffold`)

Based on: `docs/engineering-design.md` "Core data model", "Agent loop and harness", "Verifiable: Eval design", "Three-hour mapping", "Acceptance checklist"; the main text of `docs/prd.md`. Field names always follow the design docs. Where the design docs do not decide something, it is written as a proposal in [`eval/INTERFACE.md`](../../eval/INTERFACE.md), for the main session to confirm or change.

## Boundaries

- This line owns only `eval/`, `tests/`, `docs/eval/`, and `requirements-dev.txt` at the repo root. It does not create or modify `catalyst/`, and does not change the two design docs.
- No real model calls, no reading of any API key. The Reasoner is always injected; tests use a fake.
- How "the model proposes, code decides" maps onto eval: what code can decide (E3 Non-interference, entry truth table, condition time semantics, reference existence) is written as deterministic tests; what code cannot decide (whether E1 causality holds, whether E2 conditions are meaningful, whether the E4 rationale hits the trap) goes into the human review sheet, and is not handed to an LLM judge.

## Directory structure

```
eval/
  INTERFACE.md          Interface proposal for the core package (function signatures, fields, error types)
  __init__.py
  loader.py             Reads cases and fixtures (plain JSON, does not import catalyst)
  scoring.py            Automatic judgment: label comparison, E3 Expected Impact set comparison, retrieval hit, failure types, failure criteria
  runner.py             Two groups: pipeline / baseline; Reasoner, Evidence and entry functions are all injectable
  report.py             Per-case markdown report (no percentages)
  fakes.py              fake reasoner / evidence / core entry points (for tests and sample_results)
  review_sheet.md       Template for the E1 / E2 / E4 human review sheet
  sample_results.json   Fake results, only for validating the report generator
  cases/
    causalt5k/T1.json … T6.json   Verbatim CausalT5k D3 excerpts + this project's expected behavior
    causalt5k/SOURCE.md           Source URL, commit hash, selection rules, data quality notes
    C1.json C2.json C3.json C4.json D1.json   Specs for self-built cases
  fixtures/
    c1_graph_v1.json              C1 baseline graph (golden)
    c1_evidence_pack.json         Semiconductor excerpts cited by the C1 graph (hand-written placeholders, for structural tests)
    c3_change_assumption.json     ChangeAssumption: op, expected write scope, in-scope / out-of-scope patches, set that should be challenged
    c3_add_shock.json             Predefined AddShock: Stage 1 lookup result, expected write scope, patches, set that should be challenged
    d1_hormuz.json                D1: placeholder excerpts for the small Hormuz pack + proposal entry conditions (threshold null + note) + expected WAIT
    gate_truth_table.json         Entry AND truth table
    condition_cases.json          Cases for condition time semantics and Condition validation
    reference_cases.json          Reference Validator cases
  cases/causalt5k/extract.py      Extracts T1–T6 verbatim from the CausalT5k download at a fixed commit
tests/
  conftest.py           Adds the repo root to sys.path
  _graph.py             Test-side graph tools: normalized hashing, reference implementation of the write scope (does not import catalyst)
  _adapter.py           The only place that imports catalyst; importorskip when catalyst does not exist
  test_gate.py          Entry truth table, verifiable ≠ met (depends on the core)
  test_conditions.py    not_observed_by time semantics, null threshold, deadline ≥ anchor (depends on the core)
  test_fork.py          E3 Non-interference: write scope, out-of-scope rejection, hashes unchanged, baseline still there (depends on the core)
  test_validator.py     Reference Validator (depends on the core)
  test_fixtures.py      golden fixture self-consistency (does not depend on the core)
  test_cases.py         Case files and CausalT5k selection rules (does not depend on the core)
  test_scoring.py       Automatic judgment and failure criteria (does not depend on the core)
  test_runner_report.py fake reasoner runs the runner, fake results run the report (does not depend on the core)
  test_runner_core.py   ScriptedReasoner + real core entry points run T1–T6, C3, C4: contract between runner and core (depends on the core)
docs/eval/
  implementation-plan.md  test-plan.md  eval-plan.md  step-by-step.md
requirements-dev.txt      pytest
```

## Module responsibilities

| Module | Responsibility | Does not |
| --- | --- | --- |
| `eval/loader.py` | Reads the JSON in `cases/` and `fixtures/`, returns dicts; lists all cases | Does no validation logic (validation lives in tests and the core) |
| `eval/scoring.py` | Pure functions: `judge_label`, `expected_impact`, `retrieval_hit`, `classify_e1_failure`, `failure_criteria` | Does not judge whether causality holds; does not call the model |
| `eval/runner.py` | `run_case(case, group, reasoner, evidence, entrypoints)` → `CaseResult`; the pipeline group goes through `discover / inspect / fork`, the baseline group puts the same material into one prompt for the same reasoner; catches exceptions and records them as ERROR | Does not import catalyst at top level; entry functions are injected by the caller and lazily loaded only in the CLI |
| `eval/report.py` | `render_report(results)` → markdown: one per-case table per group + a table comparing the two groups + failure criteria verdict + pending review list | Does not compute percentages or average scores |
| `tests/_adapter.py` | Normalizes the core's return values into the shapes tests need (string enums, sets, error lists); when core fields change, only this file changes | Implements no core logic |

## Dependencies on the core package (summary; details in `eval/INTERFACE.md`)

| Dependency | Used in |
| --- | --- |
| `catalyst.gate.evaluate_entry(conditions) -> "WAIT" / "BLOCKED" / "READY_FOR_REVIEW"` | test_gate |
| `catalyst.conditions.evaluate(condition, observations, now) -> "met" / "not_met" / "unknown"` | test_conditions |
| `catalyst.validator.validate_condition(condition) -> list[error]` | test_conditions (null threshold note, deadline ≥ anchor) |
| `catalyst.validator.validate_references(graph, evidence_pack) -> list[error]` | test_validator |
| `catalyst.fork.compute_write_scope(graph, op) -> (node_ids, edge_ids)` | test_fork |
| `catalyst.fork.apply_patch(graph, patch, scope) -> Graph`, raises `catalyst.fork.ScopeViolation` when out of scope | test_fork |
| `catalyst.diff.diff(g1, g2)` | test_fork, runner (C3) |
| Entry points: `discover(event, target=None, ...)`, `inspect(...)`, `fork(...)` | runner pipeline group |

## Data file formats

All fixtures and cases are UTF-8 JSON, with field names taken verbatim from the design docs.

**Graph** (`c1_graph_v1.json`): `version`, `parent_version`, `op`, `nodes`, `edges`, `conditions`, `model_output_ref`, `observations_ref`.
- node (Claim): `id`, `statement`, `original_statement`, `evidence_status` (supported / contradicted / unknown), `time_bucket`, `instruments` (terminals only); plus `role` (event / assumption / intermediate / terminal; a proposed field, to make it easy to locate the ChangeAssumption target).
- edge (Mechanism): `id` (proposed field, needed for the write scope), `from`, `to`, `channel`, `sign`, `lag_days`, `mechanism`, `evidence: [{tier, source_id, excerpt_id, stance, supports}]` or `model_only: true`.
- condition: `id` (proposed field), `claim_id`, `kind`, `predicate`, `series` or `source`, `comparator`, `threshold`, `threshold_note`, `anchor`, `deadline`, `observation_window: {start, end}`, `rule`, `verification_status`, `evaluation_status`.

**Evidence Pack**: `{pack_id, synthetic, excerpts: [{source_id, excerpt_id, source, date, text, stance}]}`. Excerpt text in fixtures is hand-written placeholder text (`synthetic: true`), used only for structural tests. The real Semiconductor Pack and the small Hormuz pack are delivered by the evidence line.

**Op**: `{kind: change_assumption | add_shock, target, value}`; AddShock also carries the Stage 1 lookup results `impacts` (existing node ids), `new_edges` and `new_nodes`.

**Patch** (proposed): `{base_version, node_updates: [{id, fields}], edge_updates: [{id, fields}], condition_updates: [{id, fields}], node_adds: [...], edge_adds: [...]}`.

**Observations** (proposed, for condition evaluation): `[{source, coverage: {start, end}, records: [{date, value, excerpt_id}]}]`. `coverage` is the range the source actually covers, used to decide "the window has ended and the source covers the window".

**Case file**: `{id, type, title, entry, input, material, expected, evals, auto_checks, human_review, notes}`; CausalT5k cases also carry `source` (verbatim excerpt + clean id + original id + commit).

**CaseResult** (runner output / report input): `{case_id, group, case_type, expected, actual, status: PASS | FAIL | PENDING_REVIEW | ERROR, failure_types: [...], retrieval: {expected, retrieved, hit} | null, checks: [{name, eval, passed, detail}], human_review: [...]}`.

## How to run

```
python -m eval.runner --group pipeline --group baseline --out eval/out/results.json   # needs the core and a real reasoner; this line does not run it
python -m eval.report eval/sample_results.json > eval/out/sample_report.md            # this line can run it
pytest -q
```
