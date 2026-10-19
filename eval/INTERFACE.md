# Eval interface proposal for the core package

> 2026-10-18 update: the core has landed on the `core-schema` branch (commit 64024cc), with decisions recorded in `docs/core-design.md`. D1 and D3–D9 are adopted as the defaults in this document; D2 was changed to met (already synced). For the E3 hash comparison, both sides are first normalized through `parse_graph(d).dump()`. The original proposal text is kept below; where it differs from the implementation, the core wins.

2026-10-18 · eval line → main session

This is a **proposal**, not a spec. The main session can implement it as written, or edit this file directly. After an edit, the eval line only needs to change `tests/_adapter.py` (the only place on the test side that imports catalyst) and `load_core_entrypoints()` in `eval/runner.py` (the only place on the runner side that imports catalyst). Field names always follow `docs/engineering-design.md` "Core data model"; fields this line needs that the design doc does not cover are marked "new" below.

## 1. Data representation

- Core functions **accept plain dicts** (the result of JSON deserialization). They may return dicts or objects with `to_dict()` / `model_dump()`; the adapter normalizes them. If the core uses pydantic / dataclass, please provide `catalyst.schema.parse_graph(dict)` and `parse_condition(dict)`; the adapter will use them automatically.
- Dates in the data are ISO strings `YYYY-MM-DD`; the `now` parameter is a `datetime.date`.
- Enum values are lowercase strings (`met`, `not_met`, `unknown`, `supported` …); gate results are uppercase strings (`WAIT`, `BLOCKED`, `READY_FOR_REVIEW`). Returning an `Enum` is also fine; the adapter takes `.value`.

## 2. Functions

| Function | Signature | Behavior requirements (checked by tests) |
| --- | --- | --- |
| Entry evaluation | `catalyst.gate.evaluate_entry(conditions: list[Condition]) -> "WAIT" \| "BLOCKED" \| "READY_FOR_REVIEW"` | AND; any not_met → BLOCKED; otherwise any unknown → WAIT; empty set → WAIT; all met → READY_FOR_REVIEW; only looks at evaluation_status, verification_status = verifiable does not count as satisfied |
| Condition evaluation | `catalyst.conditions.evaluate(condition, observations: list[Observation], now: date) -> "met" \| "not_met" \| "unknown"` | not_observed_by: `now > observation_window.end` and the coverage of some same-source observation covers the whole window, no record inside the window → met; a record inside the window → not_met; everything else unknown (decision D2); when threshold is null, a numeric condition is always unknown |
| Condition validation | `catalyst.validator.validate_condition(condition) -> list[Error]` | When numeric and threshold is null, threshold_note must be non-empty; when anchor and deadline are both dates, deadline ≥ anchor; when anchor starts with `scenario:`, skip the date comparison; predicate and kind are within the enums |
| Reference validation | `catalyst.validator.validate_references(graph, evidence_pack) -> list[Error]` | excerpt_id must exist in the **current** pack; an edge with `model_only: true` must not carry evidence with stance = supports; a Claim with evidence_status = supported must have at least one non-model_only incoming edge with supports evidence |
| Write scope | `catalyst.fork.compute_write_scope(graph, op) -> (node_ids: set[str], edge_ids: set[str])` | See decision D4 |
| Apply patch | `catalyst.fork.apply_patch(graph, patch, scope) -> Graph` | Returns a new version: a new `version` value, `parent_version` = baseline version; **does not modify** the input graph in place; out of scope raises `catalyst.fork.ScopeViolation`, and leaves no partial write |
| diff | `catalyst.diff.diff(g1, g2) -> dict` | Contains at least `nodes_changed`, `edges_changed`, `conditions_changed`, `nodes_added`, `edges_added`, `nodes_removed`, `edges_removed` (lists or sets of ids) |
| Case entry points | See section 4 | |

`Error` can be a string or an object, but `str(error)` must contain the id of the failing node / edge / condition / excerpt: tests use this to locate it.

## 3. Fields (new ones marked)

- **node** (Claim): `id`, `statement`, `original_statement`, `evidence_status`, `time_bucket`, `instruments`; new `role`: event / assumption / intermediate / terminal / shock (used to locate the ChangeAssumption target and AddShock new nodes).
- **edge** (Mechanism): new `id` (the write scope records edges by id); `from`, `to`, `channel`, `sign` (`+` / `-`), `lag_days`, `mechanism`, `evidence: [{tier, source_id, excerpt_id, stance, supports}]` or `model_only: true`; evidence with stance = contradicts gets a new optional `rebuttal` (explains why it is not a refutation; only contradicts evidence without a rebuttal moves a Claim to contradicted, see decision D8).
- **channel enum** (proposed): adoption, capex, demand, supply, price, substitution, technology, policy, revenue, sentiment.
- **condition**: new `id`; the rest as in the design doc: `claim_id`, `kind`, `predicate`, `series`, `source`, `comparator`, `threshold`, `threshold_note`, `anchor`, `deadline`, `observation_window: {start, end}`, `rule`, `verification_status`, `evaluation_status`.
- **graph**: `version`, `parent_version`, `op`, `nodes`, `edges`, `model_output_ref`, `observations_ref`; new `conditions` (attached to the graph, so that Fork's "any change to related Conditions is rejected" can be checked against the graph snapshot).
- **op**: `{kind, target, value}`; AddShock also carries the Stage 1 results `impacts: [node_id]`, `new_nodes: [node]`, `new_edges: [edge]` (for the three-hour version, filled in by code from a predefined table).
- **patch** (new): `{base_version, node_updates: [{id, fields}], edge_updates: [{id, fields}], condition_updates: [{id, fields}], node_adds: [node], edge_adds: [edge], assessment: {claim_id: unaffected|challenged|unresolved}}`.
- **observation** (new): `{source, coverage: {start, end}, records: [{date, value, excerpt_id}]}`; `source` matches the condition's `series` or `source`; `coverage` is the range the source actually covers.
- **evidence pack**: `{pack_id, excerpts: [{source_id, excerpt_id, source, date, text, stance}]}`.

## 4. Case entry points (used by the runner)

All placed in `catalyst.entrypoints` (or a module the main session specifies), with Reasoner and Evidence Provider injected:

```python
discover(event: str, target: str | None = None, *, reasoner, evidence, config=None) -> {
    "candidates": [{"id", "direction", "label": "grounded" | "hypothesis" | "not_recommended", "rationale"}],  # 0–3 items
    "abstained": bool, "abstain_reason": str | None,
    "observations": [excerpt_id],          # ids of all excerpts retrieved this round (go into the snapshot's observations_ref)
}
inspect(event: str, target: str | None = None, *, candidate_id=None, material: str | None = None,
        judgment_only: bool = False, reasoner, evidence, config=None) -> {
    "graph": Graph | None, "no_chain": bool, "no_chain_reason": str | None,
    "proposal": TradeProposal | None,      # must be None when judgment_only=True
    "judgment": {"label": "YES" | "NO" | "AMBIGUOUS", "rationale": str} | None,   # required when judgment_only=True
    "observations": [excerpt_id],
}
fork(graph, op, *, reasoner, evidence, config=None) -> {
    "graph": Graph,                        # new version
    "base_graph": Graph,                   # original version (must still be retrievable)
    "scope": {"nodes": [...], "edges": [...]},
    "diff": {...},                         # result of catalyst.diff.diff
    "scenario": {"version", "base_version", "ops", "assessment": {claim_id: status}},
    "proposal": TradeProposal | None,
}
```

TradeProposal must have at least `entry_conditions`, `support_status`, `meta.approval_required`, `user_judgment`, plus the `gate` the adapter uses to read the gate result (the result of `evaluate_entry(entry_conditions)`, proposed as a derived field placed directly in the proposal). After Plan B the return body changes to a `proposals` list, see 4c.

The runner CLI also needs `catalyst.reasoner.default_reasoner()` (the returned object must also have `single_prompt(prompt: str) -> str`, so the baseline group can do a single prompt with the same model) and `catalyst.evidence.default_provider()` (must have `load_pack(pack_id) -> list[excerpt]`, so the baseline group can put the full text of the same material into the prompt).

`judgment_only=True` is for CausalT5k: the scenario is given directly as `material`, and only a causal judgment is output, no proposal.

## 4b. How the runner actually calls the core (after alignment)

- All three entry points get `packs=<packs available for this case>`, computed by `eval.runner.prepare_packs(case, evidence, source)`. **One run uses only one source** (`run_all(..., pack_source=)`, CLI `--packs real|synthetic`): the real packs reuse ids like `sc-001…` and `hz-001…`, but their meaning and stance differ from the placeholder excerpts in `eval/fixtures`.
  - `real` (default): only use the real packs under `packs/`. If one is missing, leave it out and write it into `notes`; do not fill in with a synthetic pack. If a synthetic pack (`synthetic: true`) is already registered in the provider, do not use it either.
  - `synthetic`: always inject the placeholder pack with the same pack_id via `EvidenceProvider.register`, only to validate the pipeline. Retrieval hit is not judged (the report says "n/a (synthetic pack, ids collide with real pack)").
  - The baseline group's prompt uses the same list, to guarantee "the same material".
- The inspect after Discover gets `candidate=<the whole candidate dict>` (and also `candidate_id`).
- C3's fork uses the golden graph (`c1_graph_v1.json`) with `pack=<c1_evidence_pack>` and `packs=[]`, whether or not this run uses real packs: the golden graph cites placeholder excerpt ids. The baseline for the E3 hash is the `base_graph` returned by the core (already in normalized form); the hand-written fixture is not hashed directly.
- When an entry point returns `ok=False`, record `structured_failure`, with the errors the core gives attached.
- The baseline group calls `reasoner.single_prompt(prompt)` first. If the reasoner does not have this method, fall back to `complete(stage="baseline", system="", user=prompt, schema={"type": "object"})`.

## 4c. Fields eval reads after Plan B (plan-b@d105c45)

- Return body of inspect / discover / fork / sign: `proposals: list[TradeProposal]`, `[]` when there are none. **The singular `proposal` is no longer read.**
  - Eval reads it explicitly with `eval.runner.read_proposals(out, stage)`: if the field is missing, or the return body still has the old `proposal`, or it is not a list, always raise `MissingField`, and run_case records ERROR. It must not pass silently as "no proposal".
  - Must be `[]` for judgment_only (CausalT5k), Discover, and no_chain.
- For each plan (`TradeProposal`), eval reads: `terminal_id`, `gate`, `status`, `support_status`, `entry_conditions`, `exit_conditions`, `user_judgment.requires_user_confirmation`. `approval_reset` and `rival_changed` are currently only shown in the report, not scored.
- `branches: [{terminal_id, divergence_node_ids, own_node_ids, own_edge_ids, kind, trunk, synthetic_evidence}]` in the inspect return body: eval only lists `kind` in the report. Whether the branches truly compete is part of human review; there is no automatic check (Plan B section 6).
- Per-plan checks: the `gate` expectation in a case applies to every plan; the null threshold note and invented thresholds are checked plan by plan; `requires_user_confirmation` is checked plan by plan. Condition types (for example "at least one numeric") are checked across all plans of the graph combined, because parallel-beneficiary plans can use different types of conditions.
- `original_statement` and `clarified_statement` are the same across the plans of one version, so eval does not check them repeatedly.
- The cases in the contract test `tests/test_runner_core.py` that read `proposals` are skipped while the core does not yet have `TradeProposal.terminal_id`; there is also one that asserts the runner raises an error under the old contract.

## 5. Questions for the main session to decide

| # | Question | This line's default (tests are written to it) | What to change if it changes |
| --- | --- | --- | --- |
| D1 | Whether edge / condition `id`, `conditions` on the graph, and node `role` go into the schema | Add them | All fixtures |
| D2 | What not_observed_by gives when "window ended + source fully covers + no record inside the window" | **Decided (main session, docs/core-design.md): met.** evaluation_status answers "does the condition hold", and "did not happen by the deadline" holds in this case; a record seen inside the window gives not_met; everything else is unknown. The original design doc text says not_met and is pending sync | `expected` of T3 in `eval/fixtures/condition_cases.json` |
| D3 | When unknown and not_met appear together in the entry conditions | BLOCKED (confirmed not-met takes precedence) | G6 in `gate_truth_table.json` |
| D4 | How write scope edges are computed: ChangeAssumption = target + all descendant nodes + **the outgoing edges of these nodes**; incoming edges that point to a descendant node but start outside the scope (such as `c1.e3` in C1) are **not** in scope. AddShock = Stage 1 new nodes and new edges + `impacts` and their descendants + the outgoing edges of these nodes | As stated at left | expected_scope in `c3_*.json`; the reference implementation in `tests/test_fixtures.py` |
| D5 | Patch format; whether `assessment` goes in the patch as a model proposal, or is derived by code from the diff | Put it in the patch; code only accepts in-scope claims | `c3_*.json` |
| D6 | How CausalT5k's Skepticism Trap and sycophancy trap map onto cases: in the dataset they are diagnosed failure modes (P1, P2), not a per-case `trap` field | T1 = a YES case that looks like a trap but actually holds (Natural Experiment); T4 = NO case + a pressure sentence in a confident user tone | `eval/cases/causalt5k/` |
| D7 | Whether a non-numeric condition with a null threshold must also have threshold_note | Only enforced for numeric; non-numeric conditions in the fixtures also have a note | `condition_cases.json` |
| D8 | Which field expresses that contradicts evidence has been "rebutted" | Optional `rebuttal` text | `c1.e4` in `c1_graph_v1.json` |
| D9 | In which case the online search pack is turned on for the demo | C2 | `eval/cases/C2.json` |
