# Catalyst core: schema, validators and harness

2026-10-18 · main line (core-schema branch)

This document records implementation-level decisions only. Product and architecture follow `docs/prd.md` and `docs/engineering-design.md`. For the eval's interface proposal, see `eval/INTERFACE.md` on the eval branch.

## Modules

| Module | Responsibility | Written by |
| --- | --- | --- |
| `catalyst/schema.py` | The single data contract: persisted objects (Graph, Condition, Scenario, TradeProposal…) and model output objects (`*Output`) | — |
| `catalyst/validator.py` | Structural validation: the graph (ids, no cycles, a terminal is reachable, evidence or model_only), Condition (threshold note, date, window), references (the excerpt exists in the current evidence pack, model_only does not pose as evidenced, supported has evidence behind it, contradicting excerpts are answered) | code |
| `catalyst/conditions.py` | Condition evaluation: met / not_met / unknown | code |
| `catalyst/gate.py` | Entry AND truth table, exit ANY / ALL | code |
| `catalyst/fork.py` | Write-scope computation, patch application (rejected if out of scope), Scenario defaults | code |
| `catalyst/branches.py` | Branch derivation: own part, divergence points, kind (hypothetical / evidenced / model_only), trunk | code |
| `catalyst/diff.py` | Structural diff of two versions (including `changed_claim_ids`, for the front end to show directly) | code |
| `catalyst/store.py` | Immutable snapshots + operation log + trace + recording, one directory per run | code |
| `catalyst/reasoner.py` | The Reasoner boundary: live / record / replay | model |
| `catalyst/evidence.py` | The Evidence Provider boundary: load material by pack | — |
| `catalyst/harness.py` | Controlled generation: call the model → parse → schema → domain validation → rewrite with errors, at most 2 retries | code |
| `catalyst/entrypoints.py` | The three entry points discover / inspect / fork, plus approval (sign) | — |
| `catalyst/__main__.py` | Harness CLI: run a case, record, replay, promote a fixture | — |

## Why fixtures are not hand-written

Graph-level fixtures are recorded by the harness running real cases. They are then promoted to `fixtures/` with `promote`, and the UI and the tests share that one copy.

- **Record**: `RecordingReasoner` writes the hash and the raw output of every request into `cassette.jsonl`. At the same time `RunStore` writes the snapshots, proposals, scenarios, trace and operation log.
- **Replay**: `ReplayReasoner` returns the recording by request hash. The process is deterministic and costs nothing. If the prompt, the evidence pack, the schema or the input changes, replay raises `CassetteMiss`. It will not pass an old answer off as the new one.
- **Only two things still need a person to write them**: the expectations (what the gate should be, which claims in C3 should be challenged), because an expectation must not come from the model's own output, or the reasoning is circular; and the minimal inputs of pure code tests (a few Conditions in the truth table).

## Decisions on eval/INTERFACE.md

| # | Decision |
| --- | --- |
| D1 | Adopted: edges and conditions have an `id`, the graph carries `conditions`, and nodes carry a `role`. |
| D2 | **Changed to met.** evaluation_status answers "does this condition hold": for `not_observed_by`, when the window has ended, the source covers the whole window and there is no record in the window, the condition "the deadline passed with nothing happening" holds. If a record is seen in the window, give not_met. Everything else is unknown. The original text of the design document says not_met and needs updating to match. |
| D3 | Adopted: not_met takes priority over unknown, and the result is BLOCKED. |
| D4 | Adopted: write scope = the target and its descendants + the out-edges of those nodes + the conditions hanging on those nodes; an in-edge whose source is outside the scope is not in the scope. |
| D5 | The model proposes the assessment in the patch. The code accepts only claims inside the scope, and for everything outside the scope the code writes unaffected. |
| D6–D9 | Adopted the eval line's defaults. |

## Other implementation decisions

- **Canonical form**: snapshots, the API, diffs and hashes always use `dump()`, which has all fields (including defaults). The E3 hash comparison must first put both sides through schema normalisation. It must not hash a hand-written raw dict directly.
- **Proposal status is split into two fields**: `status` (lifecycle) and `gate` (the entry decision: WAIT / BLOCKED / READY_FOR_REVIEW). Both are written by code only. When the gate is READY_FOR_REVIEW, status is needs_review. Otherwise it is draft.
- **Proposal fields written by code only**: `support_status` is derived from the evidence status and the scenario assessment of the claims holding the key dependency and the entry conditions, and of the claims this branch owns. In `user_judgment`, confirmed, confirmed_claim_ids and probability can be written only by the user (the model output schema simply has no such fields). When the model has rewritten the user's own words, `requires_user_confirmation` is always true.
- **Conditions are re-evaluated with each version**: for every new version that inspect and fork produce, all conditions are evaluated again against the observations and the date. `conditions.evaluate` never raises. If the date is invalid it gives unknown.
- **A citation's stance cannot be flipped**: when an excerpt is cited, the stance must match the stance of that excerpt in the evidence pack. There are three stances: supports, contradicts, neutral. Neutral is background information (such as "the data is updated only weekly"). It can be cited, but it does not make a claim supported, it needs no rebuttal, and `unanswered_contradictions` ignores it. None of the three stances can be flipped into another.
- **Evidence hangs on edges only**: a node with no in-edge cannot be marked supported (a check in the inspect stage). Node-level evidence is left for later.
- **Reference validation in fork**: a patch cannot change evidence references, so fork validates only the edges added in Stage 1. The references already in the baseline graph were validated when it was generated. A new edge in Stage 1 must run from a new node to a declared impacts target.
- **Scenarios do not advance evidence**: a patch cannot change `evidence_status`, and a node may change only statement / time_bucket / instruments.
- **Stacked scenarios**: when a scenario version is forked again, the new scenario is computed on top of the previous layer.
  - `ops` = the parent scenario's ops plus this op. `base_version` is the direct parent version, and `root_version` is the original non-scenario baseline (old snapshots do not have this field, and a None is read as `base_version`).
  - The assessment inherits from the parent scenario first: for a claim inside the write scope, use the value the model gives this time; outside the scope, keep the parent scenario's value, and do not reset it to unaffected.
  - The proposal's `scenario_ref.challenged_claim_ids` and `support_status` are computed from the stacked assessment.
  - A "challenged" from the previous layer is not wiped out just because this layer does not touch it. To undo one scenario layer, you can only go back to an earlier version. If the model overwrites the previous layer's challenged inside the write scope, the model's value is used, and a non-blocking hint is given.
  - `fork(scenario=...)` takes the baseline version's scenario. If none is passed, it is read from the store. Signing does not change the scenario: after a scenario version is signed, the new version carries the same scenario, and forking again from the signed version still stacks.
- **Relative time**: it is legal for an anchor or observation_window to be written as `scenario:<event>`. But until the user confirms the starting point, the evaluation result is always unknown.
- **Structured output**: the pydantic schema is converted into a strict JSON Schema (every object has `additionalProperties: false`, and all fields are listed in required). When the API rejects that schema, we fall back to constraining the JSON in the prompt, with the validator as the backstop. The reason for falling back (the original API error) is recorded in `schema_fallback_reason` in meta, and is visible in both the recording and the trace.
- **Inspect is split into two steps**: a single whole `InspectOutput` was rejected by the API (`The compiled grammar is too large`). In practice the grammar budget covers only about 70 flat string fields, and nullable fields and arrays of objects take extra room. InspectOutput has 64 fields and 18 nullable fields, and many nested arrays. Even with all unions, enums and descriptions removed it was still over the limit, so cutting fields could not solve it. It is now split into two steps: `inspect` (`InspectGraphOutput`: no_chain, nodes, edges) → `inspect.plan` (`InspectPlanOutput`: conditions, proposal). Both schemas were verified to be accepted, and each one's union count is within the API limit of 16. Step 2 runs only after the graph passes validation, and the final graph is put into its prompt. Errors go back only to the step that produced them, for rewriting. The return shape of `inspect()` is unchanged, and `attempts` is the sum of the two steps.
- **Short node titles**: Claim has an optional field `label` (at most 10 Chinese characters or 4 English words). Old snapshots without this field still parse. Inspect must write it (a missing one is a blocking error). Too long gives only a non-blocking hint, and the code does not truncate. A fork patch may change the label.
- **anchor**: the anchor of an absolute time window is today, or the date the event happened. Write `scenario:` only when it is relative to an event that has not happened and whose starting point the user must confirm. When all conditions are scenario anchors, inspect gives a non-blocking hint (such a proposal will only stay at WAIT until the user confirms).
- **Assessment in a fork**: the prompt lists "the claim ids that need an assessment" (= the nodes of the write scope). If the model writes edges, conditions or claims outside the scope, all the errors are listed at once ("c1.e4 is an edge, not a claim; write assessment only for these claims: [...]") and the model rewrites. The code does not silently drop illegal entries. The changed assumption itself and a newly added shock node are scenario inputs, and get unresolved. challenged is used only for the claims that depend on them.
- **Where Discover abstains**: abstain only when no reasonable mechanism can be found (a connection that can be forced only through a generic channel such as "sentiment" or "policy uncertainty" also counts as no mechanism). In these three cases it does not abstain: there is no supporting excerpt (label it hypothesis); there is a contradicting excerpt that has not been rebutted (this is a validation in the Inspect stage); a date or definition needs the user's confirmation.
- **Model default**: `claude-opus-5-5`, effort set to high, server-side fallback on. Override with `CATALYST_MODEL` / `CATALYST_EFFORT`.
- **Retry**: each retry is a fresh single-turn request. Its content is the original question, the last output and the list of errors. History messages are not rewritten.

## Critic (not enabled in this phase)

**What it is meant to solve.** Inspect's validators decide structure only: whether a citation exists, whether a stance was flipped, whether a threshold has an explanation. They do not judge the reasoning itself. Two kinds of error get past the structural checks:
- A wrongly chosen key dependency. The key_dependency points at a condition that is easy to verify but matters little to the conclusion, while the premise that would actually overturn the argument is not listed.
- Sycophancy or excess skepticism. When the user sounds sure, the model fills in the chain to go along with the user. Or the reverse: only because the material contains counter-evidence, the model rates a sound chain as weak.

The Critic is a separate prompt that checks only the one chain the user chose. Its output is "which claim was challenged, and with what", that is, `CriticReport.items = [{claim_id, challenge}]`. It only raises challenges. It does not change the graph or the gate.

**Why it is not built in this phase.** The design document lists the Critic as optional, and the second thing to give up when time runs short (ranking refinement → Critic → market reference → UI animation). This phase puts state consistency, evidence labelling, the refusal mechanism and the end-to-end flow first. Also, the Critic needs its own eval before anyone can tell whether it helps or gets in the way, and the eval has no Critic case yet.

**The placeholder for now.** The interface is fixed first:
- `TradeProposal.critic` is always `{status: "disabled", reason: "Not enabled: out of scope for this phase", items: []}`, and an old snapshot without this field is parsed to this value too.
- `entrypoints.critic()` returns disabled directly and does not call the model. `derive_proposal` calls it every time it generates a proposal, and the front end can show "disabled" from this field.
- When it is built later, it must go through `run_stage` (parse → schema → domain validation → rewrite with errors), with its own prompt; claim_id may only be a node on the chosen chain. If the model fails, give `status: "failed"`, and do not block the proposal.

## Known limitations (POC)

- Retrieval (BM25) is not implemented: the whole evidence pack goes into the context. The evidence line will add retrieval.
- Stage 1 of AddShock has the caller supply `impacts`, `new_nodes` and `new_edges` in the op. Using the model to identify an arbitrary shock is left for later.
- The observation data that condition evaluation needs (`Config.observations`) is usually empty in the POC, so most conditions are unknown and most entry decisions are WAIT. This is the default state by design (WAIT).
- The market reference is not connected: `market_reference` is always null, that is, no_market.

## HTTP interface (`catalyst/api.py`)

A thin HTTP layer for the front end, with no business logic. It only translates requests into entry-point calls, and reads versions back from the RunStore. Run `.venv/bin/python -m catalyst.api`; the address is http://localhost:8000. When `CATALYST_REPLAY=<recording directory>` is set, it replays the recording and does not call the model.

- Every write operation returns `{ok, errors, version}`, and the front end then GETs that version with the version number.
- `GET /api/runs/{id}/versions/{v}` returns `{graph, proposal, scenario, diff, excerpts}`. `diff` is computed against the parent version, and the fixture that `promote` writes has this shape too.
- **sign = approve one plan.** No model call; produces a new version (`op.kind = "sign"`, `op.value.terminal_id` is the approved plan, or null).
  - Request body: `{version, terminal_id, clarified_statement?, criteria?, deadline?, note?, confirmed_claim_ids?, condition_overrides?}`.
    - `terminal_id` must be present. A missing key returns `{ok: false, errors}` instead of a KeyError turned into a 404.
    - `terminal_id: null` approves no plan (no trade); the judgment fields must then be empty.
    - The text fields and `note` keep the plan's values when omitted, so sign cannot clear them.
  - User-edited thresholds and deadlines are written into the conditions; an earlier deadline shrinks the observation window. Code re-evaluates the conditions and re-derives every plan.
  - The approved plan gets `user_judgment.confirmed = true`. The other plans in the version get confirmed=false (D-B4) and keep their confirmed_claim_ids.
  - Only threshold / threshold_note / comparator / deadline can be overridden at approval.
- **fork** takes all the plans and the observations of the baseline version as input, and re-derives them one by one. Only the affected plans become invalid (see "Plan B" below).

## Plan B: competing branches + approved plans (B-minimal, backend)

Source: `docs/changes/2026-10-18-branches-and-plans.md`, section 4, plus four additions from the frontend design review (kind tables, revoking approval, the note, and one statement per version).

- **Data model**:
  - `ProposalDraft` / `TradeProposal` carry `terminal_id`; `Direction` stays required.
  - `InspectPlanOutput.proposals` is a list. The structured output was accepted by the live API (Haiku, 2 calls, no fallback; 12 unions against the limit of 16).
  - The version bundle is `schema.VersionBundle`, switched in one go to `proposals`; there is no `proposal` field.
  - `UserJudgment.note` is user-only. `ModelUserJudgment` has no such field.
- **Plan order**: plans follow the graph's terminal order, so the default plan never depends on the model's output order.
- **Legacy files**:
  - A `proposals/<v>.json` holding a single dict is read by `parse_proposals` as a one-item list. Its `terminal_id` is the one terminal whose instruments contain `direction.instrument`; none or several matches raise `LegacyProposalError` instead of guessing.
  - `observations/<v>.json` gains `synthetic` (this version used a synthetic placeholder pack); a missing field reads as false.
- **Branch derivation** (`branches.derive_views`, shared by store.bundle, promote, and the inspect / fork results):
  - Own part: `(ancestors(t) ∪ {t}) − ⋃ ancestors(other terminals)`; own edges are the edges ending in it.
  - Divergence node: a node whose out-edges reach different terminal sets. Each branch lists the divergence nodes among its ancestors.
  - kind, by priority:
    1. hypothetical: `ancestors(t) ∪ {t}` contains a role=shock node, a scenario-added node, or a changed assumption (a changed terminal counts too).
    2. evidenced: at least one own edge, every own edge non-model_only with supports evidence, no contradicted own node, and no synthetic excerpt cited by an own edge.
    3. model_only: everything else.
  - A branch with no own edges is never evidenced. `synthetic_evidence` flags "an own edge cites a synthetic excerpt" and is independent of kind.
  - trunk: the ancestors outside the own part and the edges into them, scored by the same rule. With no edges (only the starting event shared), it is evidenced.
  - `node_kinds` / `edge_kinds`:
    - hypothetical inputs → hypothetical;
    - own-part nodes → their branch's kind;
    - shared nodes → the weakest trunk among the branches containing them (model_only < evidenced);
    - edges → the kind of their target node.
- **Plan validation** (`validator.validate_plans`):
  - Blocking:
    - the plan terminals equal the graph's terminals exactly (missing, duplicate and non-terminal targets are all reported);
    - each instrument belongs to its plan's terminal;
    - every reference exists;
    - each plan has at least one entry condition;
    - every plan has an identical `original_statement` and `clarified_statement`. There is one reading of the user's words per graph; the model rewrites, code never picks one.
  - Non-blocking: an entry condition on a claim that is not upstream. Exit conditions get no hint, because the prompt encourages mirrored exit conditions on a rival branch.
- **Which plans a changed assumption invalidates** (`entrypoints.plan_affected`, write scope only):
  - A plan is affected when its terminal is in scope, or one of its entry / exit conditions sits on an in-scope claim, or its key_dependency points into the scope.
  - Affected plans get confirmed=false and lose in-scope confirmed_claim_ids. The others keep their approval.
  - `approval_reset`: the plan was approved and is now affected.
  - `rival_changed`: this plan was not affected, but another plan in the version was. It does not judge whether the two compete; C1's side-by-side terminals trigger it too.
  - Both flags are recomputed on every derivation; inspect and sign always write false.
- **Follow-up research hook**: a comment in `inspect` marks the point where the graph and plans are built but not yet persisted. The agent loop plugs in there and finds gaps via `kind == "model_only"`.
- **Prompt p5** (INSPECT and both step prompts are now in English):
  - competing branches only at genuine disputes;
  - every event that has not happened yet is role=shock;
  - one plan per terminal, with mirrored conditions encouraged;
  - the same statements in every plan.

  All old recordings are invalidated and need re-recording.
