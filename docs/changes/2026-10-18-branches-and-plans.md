# Change note: one graph with several branches + approve a plan (plan B)

2026-10-18 · Version 2 (review comments adopted) · Status: **waiting for Mia to set the scope** (section 9)

This note is the only basis for this change. Changes to the PRD, the engineering design, the core, the front end and the eval all follow this note. Anything it does not mention stays as it is.

## 1. In one sentence

One graph holds competing branches. Each branch leads to a conclusion, and each conclusion has a plan that the system fills in beforehand (entry conditions, exit conditions, key dependency). The user reviews the plans, edits them as needed, and approves one of them. The user may also approve none.

## 2. Why change it

From the user's side, the decision depends on "which premise you believe".

- **The divergence point is the key dependency.** Wherever the branches part is the premise most worth checking. There is no need to look for it separately.
- **The conditions tell you which path reality is taking.** The same observable signal is an entry condition on one branch and often an exit condition on another. For example, "integrated lasers start volume shipments".
- **Not an investing coach.** The system supplies the plan. The user is only a copilot and human-in-the-loop: review, edit, approve. Approval is required because execution needs a human to say yes. The user is not asked to write a vow-style free-text statement.

## 3. Decisions

| # | Decision | What it replaces |
| --- | --- | --- |
| D-B1 | Inside the chosen direction, Inspect gives 2–3 competing branches where there is a real disagreement, each leading to one terminal. When there is no real disagreement, 1 branch is also valid. No branches are made up to reach a number. Discover's candidate directions do not change. Branches expand only inside the direction the user chose | A single path |
| D-B2 | Every terminal must have a plan, and exactly one. Every plan has a direction and an instrument. "No trade" = approving none of the plans. There is no separate plan without a direction | One proposal per version |
| D-B3 | B2 changes from "sign" to "approve a plan". The plan is pre-filled. Pick a branch. A threshold with no basis is highlighted "needs your confirmation". Click approve. The note is optional. The three required free-text boxes are removed | The sign-off form |
| D-B4 | At most one plan per version is in the approved state. Approving one revokes the approval of the other plans in the same version. When several branches benefit side by side, they cannot be approved together either (to be considered in the next phase) | — |
| D-B5 | Changing an assumption = updating this graph: recompute only the downstream, produce a new version, undoable. **Only the affected plans become invalid** and need to be approved again. The approvals of the other plans are kept (the rule for deciding is in 4.3) | "Baseline / scenario" side-by-side comparison as the main flow |
| D-B6 | Premise confirmation keeps the claim-by-claim ticking. For a premise that is not ticked, the conclusions that depend on it fade in the UI. No model call | Deleting nodes and edges (not doing it) |
| D-B7 | The model's rewording of the user's own words still needs the user's confirmation. It is done with one line at the top of the plan: "We understood your idea as … ✓" | The "testable judgment" in the sign-off form |
| D-B8 | Stacked scenarios (implemented) and the multi-scenario comparison page (implemented) stay, but leave the main flow. The back end works as before. The front end's #scenarios page is labelled "Experimental" | A multi-scenario list in the main flow (not doing it) |
| D-B9 | **Hypothetical branches and evidenced branches must look clearly different in the UI, so the user can tell them apart at a glance.** The branch kind is derived by code and is not labelled by the model (see 4.2) | — |

**Explicitly not doing**: deleting nodes and edges; leaving AddShock to the model and letting the user add branches (that is plan C); switching between update and scenario modes; plans with no direction.

## 4. Core (back end) changes

### 4.1 Data structures (`catalyst/schema.py`)

- Add `terminal_id` to `ProposalDraft` and `TradeProposal`. `Direction` **stays required**.
- The output of Inspect's second step (`InspectPlanOutput`) changes from `proposal` to `proposals: list[ProposalDraft]`. The review simulated this new schema in memory: the union has 13 members (limit 16), so it is within the limit.
- Each version stores a set of proposals. The API version bundle **switches over in one step** to `proposals: list`, with no transitional `proposal` field. Otherwise "which one is shown by default" would be decided by the order of the model's output. When `store.get_proposal` reads an old file (a single dict), it wraps it into a list with one item.
- `ProposalMeta.proposal_version` changes to `f"{g.version}.{terminal_id}"`, so that several plans in the same version do not share a name.

### 4.2 Branch derivation (new file `catalyst/branches.py`, pure functions, decided by code)

`store.bundle`, `promote` and `web/scripts/make_fixtures.py` all call the same function. The version bundle gains:

```
branches: [{terminal_id, divergence_node_ids, own_node_ids, own_edge_ids, kind, trunk}]
```

- **Own part**: `own_node_ids = (ancestors(t) ∪ {t}) − ⋃ ancestors(other terminals)`. `own_edge_ids` are the edges whose end falls in `own_node_ids`. This way a side-path root node is not missed.
- **Divergence point**: if a node's outgoing edges each reach a different set of terminals, that node is a divergence point.
- **kind**, one of three, taken in this order of priority:
  1. `hypothetical`: among **all ancestors** of this branch (including the shared upstream), any one of these is present:
     - a node with role=shock;
     - a node added by a scenario shock;
     - an assumption the user has changed (the target of `scenario.ops` in this version and in ancestor versions).

     Note: an assumption the user has changed makes every branch that depends on it hypothetical.
  2. `evidenced`: **none of the edges** in the own part is model_only, and all carry supports evidence; there is no contradicted node among the own nodes; the evidence pack used is not synthetic.
  3. `model_only`: everything else. A branch backed by a synthetic evidence pack is also downgraded to this kind, and labelled "evidence is a placeholder".
- **trunk**: the strength of the shared upstream, with value evidenced / model_only, computed the same way. This avoids a branch showing as a solid line when the whole trunk is inference.
- **Residual risk** (open question): "event that has not happened yet" relies on the model marking it role=shock, and the model may miss it. The prompt states this requirement firmly. One item is added to the human review sheet.

### 4.3 After an assumption changes, which plans become invalid (D-B5)

A plan counts as affected if any one of these holds. Its `confirmed` is reset to false, and `confirmed_claim_ids` drops the claims inside the write scope:

1. Its terminal is inside this fork's write scope. The write scope is all the descendants of the change target, so anything hanging off the shared upstream or the divergence point is caught by this rule.
2. Its entry conditions or exit conditions hang on a claim inside the write scope. This rule covers the case of "a mirror condition hanging on the rival branch".
3. Its key_dependency points at a claim or a condition inside the write scope.

A plan that meets none of these keeps its approval as it was. The decision looks only at the write scope the code computed, not at the model's assessment.

**Known blind spot** (open question): the rivalry is not in the graph structure. If the change is to a premise that only the rival branch owns, and this plan has no condition that references it, this plan does not become invalid. B3 gives one line on this: "The rival branch changed. Your plan is not directly affected, but it is worth another look."

This reverses existing behaviour: line 56 of `tests/core/test_api.py` asserts "a sign-off is not lost on fork". It must be changed to match.

### 4.4 Validation

- The set of the plans' terminals must be **exactly equal** to all the terminals on the graph (blocking): one plan per terminal, no more and no fewer.
- `direction.instrument` must belong to that terminal's instruments.
- For a condition a plan references, the claim it sits on should be an ancestor of that terminal. Otherwise give a non-blocking hint. A condition may be shared by several plans.
- `_support_status` must include the claims owned by this branch, in addition to the claims holding the entry conditions and the key_dependency. It is still computed by code.

### 4.5 Flow

- The meaning of `sign` changes to "approve". The interface name is not changed yet:
  - `clarified_statement`, `criteria` and `deadline` become optional, and default to the values in the plan. `api.sign_run` currently reads `body["clarified_statement"]` directly, and a missing key raises KeyError. Fix that as well.
  - Add the required parameter `terminal_id`.
  - In the new version it produces, only the approved plan is confirmed (D-B4).
  - `condition_overrides` stays: changing a threshold or a date makes no model call, and the code evaluates again.
- fork: the `proposal` parameter becomes `proposals`. Each plan is recomputed when derived. Per 4.3, only the affected plans are reset.

### 4.6 Prompts (bump `PROMPT_VERSION`)

- **The graph step**: give competing branches at the real points of disagreement. The branches share the upstream. Do not make up branches to reach a number. **Any event that has not happened yet is written as role=shock** (delete the old wording "or explicitly written as an assumption"). Change the wording in the prompt about "one instrument" and "one proposal".
- **The plan step**: one plan per terminal. Mirror conditions are encouraged.
- After the version is bumped, all existing recordings become invalid (`eval/out/haiku-realpacks`, `runs/D1`, and so on). They **need to be re-recorded with live model calls**. The cost and time are counted in section 9.

## 5. Front-end changes

| Page | Change |
| --- | --- |
| B1 | Click a conclusion and the whole branch it sits on is highlighted. **The three kinds of branch look clearly different** (D-B9): evidenced is a solid line in the normal colours; model-only is a dashed line, faded; **a hypothetical branch gets a different visual language as a whole**: diagonal hatching, grey-purple tones, and every node and conclusion card carries a prominent "Hypothetical · not observed" label. The shared trunk is shown according to `trunk`. A special marker for the divergence point goes to the next phase |
| B2 "approve a plan" | At the top is the list of conclusions. Each row gives the premise "you need to believe", the status (WAIT / BLOCKED / READY_FOR_REVIEW), and the branch kind, marked in the same visual language as the canvas. The plan card of a hypothetical branch has a banner at the top: "This branch rests on an assumption that has not happened yet". Select a row and the pre-filled plan shows below. A `threshold` that is null is highlighted "needs your confirmation". One "Approve" button, and one optional note |
| B3 | **Reuse the existing scenario page; no new interaction is written.** After a fork, "set as current version", and "undo" goes back to the parent version. Only an affected approved plan is marked "Premise changed, please approve again". When the rival branch changed, give the line from 4.3 |
| #scenarios | Kept, labelled "Experimental", not in the main navigation, but it must still compile |

Files to change:
- `types.ts`; the state in `App.tsx`, changed to "current version + undo stack";
- `Signoff`, `SignDialog`, `ProposalCard`, `lookup.keyClaimId`, `Workspace`, `NodePanel`, `Scenario`;
- the mock `api.ts`;
- the 4 fixtures and `check_fixtures.py`.

## 6. Eval changes

- **Prevent silent passes**: the runner has places that test with `get(out, "proposal") is None` (`runner.py` lines 192 and 214). After the field is renamed those tests would always be true. They must be changed to read `proposals` explicitly. When the field is missing, raise an error. It must not be treated as "no proposal".
- **Aggregation rule for the gate**: `"gate": "WAIT"` in a case is read as: the gate of **every plan** must equal this value.
- **The other checks** also become per-plan checks: a null threshold must carry an explanation, and a reworded statement needs the user's confirmation.
- **C1's golden graph** has 3 terminals (LITE, TSM, MRVL). They benefit **side by side and do not compete with each other**. The graph itself needs no change, but the hand-written proposal draft in `make_fixtures.py` must become 3 plans. C3 goes through the fork mechanism, and its expectations need no change.
- **The human review sheet** gets two new items: whether the branches are real competitors and not made up to reach a number; whether events that have not happened yet are marked as shock. **No** automatic check such as "D1 must show a certain branch" is added, so that the eval does not shape the prompt in return.
- `INTERFACE.md` and `fakes.py` are updated to match.

## 7. To do (next phase; the structure already leaves room)

| To do | How to add it later |
| --- | --- |
| Finer actions: reduce position, remind me | Add an optional `action` field to conditions; for now use "entry / exit conditions" |
| Structured threshold sources: cite an excerpt or a calculation rule | Add an optional `threshold_basis` field to conditions; for now it is written in `threshold_note` |
| Automatic calculation of thresholds derived by a rule | After live data is connected, support it in condition evaluation |
| Mark each condition "can it be executed automatically" | Add a status field to conditions, and carry it when the plan is exported |
| Export to the execution layer | Export the approved plan as JSON |
| Approve side-by-side branches together | Relax D-B4 |
| Divergence point markers, put rivalry into the graph | So that the blind spot in 4.3 can be detected |
| Plan C: the user adds branches themselves, AddShock goes to the model | Reuse the fork's two-step mechanism |
| Critic | The placeholder already exists (disabled) |
| Market reference | Do a snapshot first, connect a data source later |

## 8. Where the documents need updating

- **PRD**:
  - Core experience: two beats → competing branches + approve a plan;
  - "the sign-off gate" becomes "approve a plan";
  - One Essential Experience;
  - One Testable Hypothesis: E2 is checked per plan;
  - The positioning changes from "we provide discipline" to "an executable plan, approved by a human, that says clearly which conditions can be automated". **State this shift explicitly.**
- **Engineering design**:
  - Core data model: proposals are split by terminal, and branch derivation is added;
  - Agent loop: Inspect's second step outputs several plans;
  - Runtime flow: approval, and resetting the affected plans after an assumption changes;
  - Eval; items 5 and 6 of the acceptance checklist; the front-end section.
- **`docs/core-design.md` and `CLAUDE.md`**: add `proposals`, `terminal_id` and `branches` to the data contract.
- **`docs/frontend-design.md` and `docs/frontend/`**: the new form of B2 and B3.

## 9. Scope and time estimate (Mia to choose)

The 3.3 hours estimated in version 1 was too optimistic. The review's estimate, based on what actually has to change, is 9–13 hours. This version has adopted its simplification suggestions (Direction not made optional, no transitional field, branch derivation in one function, B3 reusing the existing scenario page, divergence point markers deferred), which saves about a third.

| Option | Includes | Time estimate (wall-clock after several lines run in parallel) |
| --- | --- | --- |
| **B-full** | All of this note | Effort about 6–9 hours, about 4–5 hours after parallelising |
| **B-minimal** | Core 4.1–4.6 in full; front end only does the B2 conclusion list plus approval, and the three branch styles in B1; B3 stays as is, with only the invalidation marker added; eval only does the silent-pass prevention and the gate aggregation; docs only change the positioning and the data model sections of the PRD | Effort about 4–5 hours, about 2.5–3 hours after parallelising |
| **Do not do B** | Keep the status quo, and write B into the README as the direction for the next version | 0 |

Both B options need: re-recording (about 30 live Haiku calls, plus another round on Opus for the final demo), integration, and a subagent review after each line finishes.

## 10. Order and division of work (executed once the scope is chosen)

| Order | What changes | Who does it |
| --- | --- | --- |
| 1 | Finalise this note | Mia |
| 2 | Core: 4.1–4.6, including `branches.py` and tests | core fix session |
| 3 | Front end: section 5 (develop first against fixtures in the new format) | front-end session |
| 3 | Eval: section 6 | eval session |
| 4 | PRD and engineering design (the online Claude Docs version; re-export to the repository after editing) | main session |
| 5 | Re-record, integrate, and walk through B1 → B2 → B3 on the real back end | main session |

The two items in step 3 can run in parallel, but both depend on the data structures settled in step 2.

## Appendix: review record

- Result of the version 1 review (subagent, read-only): it can land after the changes. All 10 required changes are merged into this version:
  - the derivation rule for kind (three rules);
  - using role=shock to identify hypothetical branches;
  - the definitions of the own part and the divergence point;
  - Direction stays required;
  - C1 has 3 side-by-side terminals;
  - validate that each terminal has exactly one plan;
  - proposal_version does not share names;
  - support_status includes the claims owned by the branch.
- Q2 (approve only one plan per version): kept. Reason: competing branches often land on the same instrument with opposite directions.
- Q3 (keep a transitional field or not): switch in one step, do not keep it.
- Q4 (make Direction optional): not doing it.
- Q1, Q5: Mia decides. The rules are filled in per the review's comments.
- Q6 (conflicts that were missed):
  - The relationship between Discover and the branches is written into D-B1;
  - The cost of re-recording is written into section 9;
  - the critic and the neutral stance do not conflict.
