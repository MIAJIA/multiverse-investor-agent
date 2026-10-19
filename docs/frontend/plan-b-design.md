# Frontend design: Plan B-minimal (branches + plan approval)

2026-10-18 · frontend branch (core-schema@da2d097 merged) · Status: **reviewed (section 10 holds the post-review decisions and takes precedence over the body), start once the backend implementation is committed**

Basis: sections 3, 5, and 9 of `docs/changes/2026-10-18-branches-and-plans.md` (hereafter "the change notes"). This document covers only the frontend; the data contract is whatever schema Plan B's backend finally delivers. This document is designed for now against the contract relayed by the main session, and section 7 lists what the backend needs to add.

The principle is unchanged: **the model proposes, the code decides; the frontend only displays, edits, confirms, and compares.** Branches, branch kinds, gate, and invalidation are all provided by the backend; the frontend only does lookups by id and set operations.

## 1. Scope

| Page | Do | Don't do (next phase) |
| --- | --- | --- |
| B1 | Clearly distinct visuals for the three branch kinds (D-B9); clicking a conclusion highlights the whole branch; the shared trunk is displayed according to `trunk` | Divergence point markers; premises fading after being checked (D-B6) |
| B2 | "签字" ("Sign") becomes "批准计划" ("Approve plan"): conclusion list + prefilled plan + understanding confirmation + approve / revoke approval + optional note (D-B3, D-B4, D-B7) | Portfolio approval; export to the execution layer |
| B3 | Keep as is; affected approved plans are marked "前提已改动，请重新批准" ("premise changed, please re-approve"); a one-line hint when a rival branch changed; add a "在这个版本上重新批准" ("re-approve on this version") entry point (see 4.3) | Undo stack, the full "set as current version" flow |
| #scenarios | Keep, mark "实验" ("experimental"), move from the top bar to a secondary entry inside the playground, catch up with the new schema so it compiles | Joining the main flow |
| Top bar (optional) | Online toggle + a one-line status "联网：开，拿到 N 段" ("online: on, got N excerpts"), taken from `web.message` | — |

## 2. Data contract (frontend-side types)

```ts
type BranchKind = 'evidenced' | 'model_only' | 'hypothetical';

interface Branch {
  terminal_id: string;
  divergence_node_ids: string[];
  own_node_ids: string[];
  own_edge_ids: string[];
  kind: BranchKind;
  trunk: 'evidenced' | 'model_only';
}

interface TradeProposal { /* existing fields */ terminal_id: string; }

interface VersionBundle {
  graph: Graph;
  proposals: TradeProposal[];   // replaces proposal; the old field is not kept
  branches: Branch[];
  scenario: Scenario | null;
  diff: GraphDiff | null;
  excerpts: Excerpt[];
}

interface SignBody {            // semantics are "approve"; the interface name is unchanged
  version: string;
  terminal_id: string;          // required
  clarified_statement?: string; // optional: only sent if the user edited it in "we understand your idea as ..."
  criteria?: string | null;
  deadline?: string | null;
  confirmed_claim_ids: string[];
  condition_overrides: Record<string, ConditionOverride>;
}
```

The frontend associates `proposals` and `branches` by `terminal_id` and doesn't depend on array order (change notes 4.1: avoid letting "which one is shown by default" be decided by the model's output order). The list is ordered by the left-to-right order of terminals on the canvas (`toFlow`'s coordinates), which is purely presentational.

## 3. B1: visual spec for the three branch kinds

### 3.1 Spec

| | Evidence-backed (evidenced) | Model inference only (model_only) | Hypothetical (hypothetical) |
| --- | --- | --- | --- |
| Node background | Current light type background (event blue / assumption green / terminal purple) | White | Gray-violet `#f1eef7` + 45° diagonal hatching (`repeating-linear-gradient(45deg, #e3ddef 0 2px, transparent 2px 8px)`) |
| Node border | 1px solid, type color | 1px dashed `#b9bfc8` (5 4) | 1.5px dotted `#8e7cc3` (2 3) |
| Text | Normal | Faded overall: title `#6b7280`, no opacity (avoids going gray when layered) | Title `#4b3f72` |
| Edge | Solid `#9aa1ab` 1.2px | Dashed `#c4c9d0` (5 4) | Dotted `#8e7cc3` (2 3) |
| Label | None (no text in the default state) | Small text "仅推断" ("inferred only"), gray | Prominent pill "假设 · 未观测" ("hypothetical · not observed"): `#5b4a9e` text, `#e6e0f5` background, **on every node and conclusion card**, placed before the title |
| Ring | As usual (green / red / gray segments) | As usual; a dashed empty ring when there are no citations | As usual, but the background becomes gray-violet |

- The principle that **color is only for status** is kept: branch kinds are distinguished by hatching + line style + label, so they can be told apart in grayscale printing or with color vision deficiency. Orange is still reserved for "关键依赖" ("key dependency") and, in scenarios, "受挑战" ("challenged").
- Downgrade caused by a synthetic evidence pack (change notes 4.2 item 3): append "· 资料为占位" ("· evidence is placeholder") after the model_only label. This needs the backend to provide the flag; see section 7 item 3.

### 3.2 Which kind each node uses

The backend only gives a branch-level kind; to assign a node to a kind, the rules are as follows (table lookups only, no inference from evidence):

1. The node is a shock, or is a target of this version's `scenario.ops` → **hypothetical**;
2. The node is in some branch's `own_node_ids` → that branch's `kind`;
3. Everything else (the shared trunk) → the `trunk` of the branches that contain it; when the trunks of several branches disagree, take the weaker tier (model_only).

Rule 3 is a trade-off the frontend makes on top of the backend's results. **Suggest the backend directly provide two tables, `node_kinds` / `edge_kinds`** (section 7 item 1), so the frontend doesn't need this rule. An edge's kind follows its end node.

### 3.3 Highlighting a whole branch

Click a conclusion (terminal): this branch = its `own_node_ids` + all its ancestors (the shared trunk). Ancestors are traced upward through the graph structure, which is a lookup along edges, not a judgment. While highlighted, the other nodes recede to 32% opacity (reusing B3's "the rest recede"), the right-hand panel shows this conclusion's plan summary and offers "去批准这份计划 →" ("go approve this plan →"), which jumps to B2 and selects this row. Click empty space to cancel.

### 3.4 Component changes

- `node/DesignNode.tsx`: `DesignData` adds `kind: BranchKind`, `highlighted?: boolean`; styled per 3.1. The existing `look.color` / `look.shape` branches are kept for the playground.
- `components/GraphCanvas.tsx`: reads `bundle.branches`, assigns a kind to every node and edge per 3.2; when `selectedTerminalId` is set, highlights per 3.3.
- `lookup.ts`: `keyClaimId(proposal)` becomes `keyClaimIds(proposals)` (one per plan); adds `branchOf(bundle, terminalId)`, `ancestors(graph, id)`.
- `Workspace.tsx`: when a terminal is clicked, the right side shows the "计划摘要" ("plan summary") instead of the evidence panel (the evidence panel can still be expanded from the summary).
- `NodePanel.tsx`: "为什么先查这一步" ("why check this step first") becomes a list of the plans that use this node as their key dependency.

## 4. B2: "批准计划"

### 4.1 Page structure

```text
┌ 我们把你的想法理解为：「2027-06-30 前 CPO 出货……」   ✓ 对   改一下 ┐   ← appears only once, shared by all plans
├ 结论列表 ────────────────────────────────────────────────────────────┤
│ ▌ 光源营收超预期  LITE 看多     你需要相信：外置光源架构、光源需求上升   WAIT 先别动   ✓ 已批准 │
│ ▒ 硅光代工营收占比升  TSM 看多  你需要相信：硅光代工利用率升           WAIT 先别动          │
│ ┆ DSP 业务承压  MRVL 看空       你需要相信：DSP 需求放缓（仅推断）       WAIT 先别动          │
├ 选中这一行的计划 ─────────────────────────────────────────────────────┤
│ [假设分支才有] ▧ 这条分支建立在尚未发生的假设上：改用集成激光            │
│ 方向 · 进场条件（且）· 离场条件（ANY / ALL）· 关键依赖 · Critic 一行灰字 │
│ 阈值为 null 的条件：黄底 + 「需要你确认」+ 输入框                       │
│ 你需要相信的前提（可选勾选，不勾也能批准）                               │
│ 备注（可选，一行）                                                      │
│ [批准这份计划]      本版本已批准：光源营收超预期 · 撤销批准             │
└───────────────────────────────────────────────────────────────────────┘
```

- The vertical bar at the start of each row is a miniature of the branch kind: ▌ solid (evidence-backed), ┆ dashed (inferred only), ▒ diagonal gray-violet (hypothetical), the same visual system as the canvas. Rows of hypothetical branches also carry the "假设 · 未观测" ("hypothetical · not observed") pill.
- "你需要相信" ("you need to believe") = this branch's `own_node_ids` minus the terminal itself, listed by short title, at most 3, with "等 N 个" ("and N more") beyond that; when empty (the branch only splits at the terminal), write "与其他结论共用全部前提" ("shares all premises with other conclusions").
- The status column uses only gate (先别动 "hold off" / 受阻 "blocked" / 待复核 "awaiting review"), and no longer shows draft / needs_review separately; the latter goes into the small text on the plan card.
- The original per-assumption table and the three-required-field form (`SignDialog`) are removed.

### 4.2 Interaction flow

1. On entering B2, the default selection is: the plan already approved in this version; if none, the first row of the list. No plan is approved automatically.
2. **Understanding confirmation**: when any plan's `user_judgment.requires_user_confirmation` is true, the top row's "✓ 对" ("✓ right") must be clicked before approving; clicking "改一下" ("edit") turns it into an input box in place, then ✓ after editing, and the edited text is sent with the approval request as `clarified_statement`. If unedited, this field isn't sent (the backend keeps the value in the plan).
3. **Changing thresholds / dates**: only in the selected plan, recorded in this plan's draft (`drafts[terminal_id].overrides`), and, as now, marked "已修改，批准后由后端重算" ("modified, will be recomputed by the backend after approval").
4. **Approve**:
   - No plan approved yet in this version → send `sign` directly.
   - Another plan already approved in this version → first pop a one-line confirmation "批准这份会撤销对『光源营收超预期』的批准" ("approving this will revoke the approval of 『光源营收超预期』 (light source revenue beats expectations)"), and send after confirmation.
   - New version number returned → `getVersion` → the current version switches to the new version; this row in the list shows "✓ 已批准" ("✓ approved"), the other rows don't.
5. **Revoke approval**: the approved row has "撤销批准" ("revoke approval") beside it. After revoking, no plan is approved in this version, and the UI says "本版本没有批准任何计划（= 不交易）" ("no plan approved in this version (= no trade)"). **The backend currently has no revoke endpoint**; see section 7 item 2.
6. **Not approving**: no dedicated button is needed; leaving the page means not approving. A permanent line of small text at the top: "一份都不批准也是一个决定" ("approving none is also a decision").
7. Permanent small text next to the approve button "批准的是一份计划，不是下单" ("what you approve is a plan, not an order"); there is no execute button.

### 4.3 B3 changes

- The scenario page's right-hand "提案 v1 → v2" ("proposal v1 → v2") becomes "计划" ("plans"): only lists **the one approved in the baseline** and the plan for the same terminal in the scenario version, showing gate / support / approval state side by side.
- **Invalidation marker**: a plan approved in the baseline whose `user_judgment.confirmed` became false in the scenario → orange "前提已改动，请重新批准". Determined by comparing backend fields across the two versions (table lookup), without judging write scope ourselves; if the backend adds an explicit field, switch to that field (section 7 item 4).
- **Rival branch hint**: the approved plan isn't invalidated, but this fork's `diff.changed_claim_ids` intersects the `own_node_ids` of **other branches** → gray text "对手分支变了，你的计划没有直接受影响，但值得再看一眼" ("the rival branch changed; your plan isn't directly affected, but it's worth another look").
- "在这个版本上重新批准": sets the scenario version as B2's current version and jumps to B2. This is the only new action in B3, used to connect to the invalidation marker; otherwise the user sees "请重新批准" ("please re-approve") with nowhere to approve. No undo stack.

### 4.4 State changes (still one state)

```ts
type AppState = {
  runId: string | null;
  versions: Record<string, VersionBundle>;
  baseVersion: string | null;            // the version B1 / B2 look at, fork's base_version
  scenarioVersion: string | null;
  viewing: 'base' | 'scenario';
  tab: 'workspace' | 'signoff' | 'scenario';
  selectedNodeId: string | null;
  selectedTerminalId: string | null;      // new: shared by B1 highlighting and B2's selected row
  understood: { confirmed: boolean; text: string | null }; // new: understanding confirmation, reset per version
  drafts: Record<string, {                 // new: unsubmitted input stored by terminal_id, replaces signoff
    overrides: Record<string, ConditionOverride>;
    confirmedClaimIds: string[];
    note: string;
  }>;
  online: boolean;                         // new (optional): online toggle
  webMessage: string | null;               // new (optional): web.message returned by the last run creation
  busy: boolean; errors: string[] | null; notices: string[] | null; runNote: string | null;
};
```

`selectedTerminalId` is shared between B1 and B2: click a conclusion in B1, and when switching to B2 the same row is selected by default. `drafts` and `understood` are cleared when `baseVersion` changes.

### 4.5 Component changes

| File | Change |
| --- | --- |
| `types.ts` | The types in section 2; `VersionBundle.proposal` → `proposals`; `Branch`, `BranchKind` |
| `api.ts` | `sign`'s request body; mock `sign`: sets this plan confirmed by terminal and the rest false (gate not recomputed, marked MOCK as before); mock `fork` unchanged; optional: `createRun` takes `online` and returns `web` |
| `App.tsx` | The state in 4.4; `signNow(terminalId)`; `revoke()` (waiting for the backend endpoint) |
| `components/Signoff.tsx` | Rewrite: understanding confirmation row + conclusion list + plan area + approve / revoke |
| `components/SignDialog.tsx` | Delete, replaced by the small "批准会撤销另一份" ("approving will revoke the other one") confirmation box `ApproveConfirm.tsx` |
| `components/ConclusionList.tsx` | New: conclusion list, one row per terminal |
| `components/ProposalCard.tsx` | Add a branch-kind banner; null thresholds highlighted with "需要你确认" ("needs your confirmation"); remove the "研究判断" ("research judgment") section (moved to the top understanding confirmation row) |
| `components/BranchSwatch.tsx` | New: the kind miniature at row start + the "假设 · 未观测" pill, shared by B1 / B2 / B3 |
| `components/Scenario.tsx` | 4.3's plan comparison, invalidation marker, rival hint, "在这个版本上重新批准" |
| `components/GraphCanvas.tsx`, `node/DesignNode.tsx`, `node/node.css`, `lookup.ts`, `Workspace.tsx`, `NodePanel.tsx` | Section 3 |
| `scenarios/*` | Catch up with `proposals` (`scenario_ref` taken from the corresponding terminal's plan); add an "实验" label to the page header; remove the entry from the App top bar, entered only from the `#playground` page header |
| `status.ts` | Add the `BRANCH_KIND` mapping (label, color, line style, hatching); all components take it from here |

## 4.6 Top-bar online toggle (optional)

- Position: to the right of the Analyze button, a small toggle "联网" ("online"), off by default. When on, `createRun`'s request body includes `online: true`.
- Status line: a line of small text below the toggle, showing verbatim the `web.message` returned by the last `POST /api/runs` (e.g. "联网：开，拿到 6 段" ("online: on, got 6 excerpts") or the failure reason); not shown when there's no `web` field.
- Excerpts fetched online go into the evidence panel just like evidence-pack excerpts; the frontend doesn't style sources differently (the source name itself says where it's from). Under MOCK the toggle is clickable, but the status line says "MOCK：不联网" ("MOCK: not online").

## 5. How to change the fixtures

Wait until the backend delivers the schema commit, then:

1. `make_fixtures.py`: `DRAFT` becomes 3 drafts, one per terminal (LITE bullish, TSM bullish, MRVL bearish), each taking its entry / exit conditions from the conditions on that branch, with `terminal_id` filled in; call the backend's derivation function to get `proposals`, and call the function in `catalyst/branches.py` to get `branches`, **not computed by hand in the script**.
2. All four fixtures are generated in the new format:
   - `c1`: 3 baseline plans; after forking to "改用集成激光" ("switch to integrated lasers"), the LITE branch should become hypothetical;
   - `c1_blocked`: same as above, `cond.c1.els_design_wins` judged not_met, LITE plan BLOCKED;
   - `c1_multi`: c1-v3 with the added shock makes the TSM branch hypothetical, and in the stacked c1-v4 both are;
   - `c4_abstain`: unchanged (no graph).
3. Add one more, `c1_approved`: on c1, approve the LITE plan via the backend's sign entrypoint, then fork. This is the only way to demo "前提已改动，请重新批准" and "对手分支变了"; it must go through the backend, not be simulated in the frontend.
4. `check_fixtures.py`: for every version, the terminal set of `proposals` = the terminal set on the graph; each plan passes `TradeProposal.model_validate` and the canonical-form check; `branches` matches a recompute by the backend function; at most one `confirmed` per version.
5. **Known limitation**: the fixtures use a synthetic evidence pack, so per change notes 4.2 all branches are downgraded to model_only, and **the "有资料支持" ("evidence-backed") style can't be seen** in the fixtures. For a remedy see section 7 item 5; until then, the evidenced style is only previewed in the playground and labeled as a demo.

## 6. Test plan

### Automated

| Test | Content |
| --- | --- |
| `branchStyle.test.ts` (new) | 3.2's assignment rules: shock / changed assumption → hypothetical; own nodes → branch kind; shared trunk → trunk, take model_only on disagreement; edges follow their end node |
| `lookup.test.ts` | `ancestors`, `branchOf`, `keyClaimIds`; "你需要相信" = own minus the terminal |
| `approval.test.ts` (new) | mock `sign`: after approving one, only it is confirmed in that version; B3 invalidation check (parent confirmed and child false); rival hint (changed ∩ other branches' own) |
| `status.test.ts` | `BRANCH_KIND` covers the three kinds, and the labels include "假设 · 未观测" |
| `toFlow` / `strength` / `scenarios` | Catch up with `proposals` |
| `check_fixtures.py` | Section 5 item 4 |
| typecheck, build | As before; `#scenarios` must compile |

### Manual demo (MOCK, rerun after connecting the real backend)

| # | Action | Expected |
| --- | --- | --- |
| P1 | c1, B1 | 3 conclusions; in the fixture all are the "仅推断" style (synthetic evidence pack), marked "资料为占位" ("evidence is placeholder") |
| P2 | In B1 click the LITE terminal | The whole LITE branch is highlighted (including the shared trunk), the rest recede; on the right, the LITE plan summary and "去批准这份计划 →" |
| P3 | Go to B2 | The LITE row is selected; at the top "我们把你的想法理解为……" ("we understand your idea as ..."); the approve button is disabled until ✓ |
| P4 | ✓, fill the CPO shipment threshold, approve | LITE "✓ 已批准"; the threshold condition is marked "已修改，批准后由后端重算" |
| P5 | Select TSM, approve | First pops "会撤销对 LITE 的批准" ("will revoke approval of LITE"); after confirming only TSM is approved |
| P6 | Revoke approval | "本版本没有批准任何计划（= 不交易）" (needs the backend endpoint; simulated under MOCK for now) |
| P7 | c1_approved, fork "改用集成激光" in B3 | On the canvas the LITE branch becomes gray-violet hatching + "假设 · 未观测"; the LITE plan is marked "前提已改动，请重新批准" |
| P8 | In c1_approved, with TSM being the approved one, fork the same spot again | The TSM plan keeps its approval, and "对手分支变了……值得再看一眼" ("the rival branch changed ... worth another look") appears |
| P9 | "在这个版本上重新批准" | Jumps to B2, the current version is the scenario version, LITE not approved |
| P10 | From the #playground page header into #scenarios | The page header has "实验", displays correctly |

## 7. What the backend needs to confirm or add

1. **Node / edge kind tables**: the contract only has branch-level kind, so for nodes on the shared trunk the frontend has to make the 3.2 rule 3 trade-off. Suggest the version bundle add `node_kinds: {id: kind}`, `edge_kinds: {id: kind}`, computed together by `branches.py`; with that, all of 3.2 becomes a table lookup.
2. **Revoke approval**: the main session asked for "撤销批准" to be designed, but the existing endpoint can only approve. Suggest `sign` accept `terminal_id: null`, meaning no plan is approved in this version, producing a new version; or open a new `POST /runs/{id}/revoke {version}`. The frontend can handle either.
3. **The "资料为占位" flag**: the frontend can't get the reason a branch was downgraded. Suggest `Branch` add `synthetic: bool` (or `note`).
4. **Explicit invalidation field**: 4.3's invalidation marker is currently inferred from "parent version confirmed, child version not". Suggest fork write `user_judgment.reset_by: <fork version number>` (or `invalidated: true`) on the affected plan, so the frontend reads it directly and can also distinguish "never approved" from "revoked by a fork".
5. **Demo data where "有资料支持" is visible**: the synthetic evidence pack downgrades all branches to model_only. To demo the evidenced style, a C1 recorded with a real evidence pack is needed (already in the re-recording plan in section 9 of the change notes). Until then, B1's evidenced style is only previewed in the playground.
6. **Where the note goes**: the "可选备注" ("optional note") has no corresponding field. Suggest `UserJudgment` and the sign request body add `note: str | None`; not recommended to stuff it into `criteria` (different semantics).
7. **Is there one understanding confirmation per plan**: currently every `TradeProposal` carries a `user_judgment`, but "我们把你的想法理解为……" is a rewrite of the user's original words and should be a single sentence for the whole graph. The frontend displays "the first plan's `clarified_statement`"; if the plans differ, it shows each one in its plan card. Suggest the backend guarantee this sentence is identical across plans in the same version, or lift it to the version level.

## 8. Optional: playgrounds for Mia to choose from

During implementation, two A/B groups can be built first, rendered with real fixtures, and put into the existing `#playground`:

1. **Visuals for hypothetical branches**: A diagonal hatching + gray-violet (this document's default) / B wrap the whole branch in a gray-violet dashed outer frame (a "bubble"), with the nodes themselves unchanged in color.
2. **B2 layout**: A list on top, plan below (this document's default) / B list on the left, plan on the right, two columns.

About 20 minutes each. If the main session thinks it's unnecessary, implement the defaults directly.

## 9. Step checklist and estimates

Data structures follow the backend commit; step 1 has to wait for it.

- [x] **1. Merge the backend schema, change `types.ts`, mock `api.ts`, regenerate 5 fixtures, change `check_fixtures.py`** (30 minutes)
- [x] **2. Existing components catch up with `proposals`; first make sure typecheck and existing tests pass** (20 minutes)
- [x] **3. B1: three kind styles + whole-branch highlighting + `BRANCH_KIND` mapping + unit tests** (35 minutes)
- [x] **4. B2: understanding confirmation, conclusion list, plan area, approve / revoke, confirmation box + unit tests** (50 minutes)
- [x] **5. B3: plan comparison, invalidation marker, rival hint, "在这个版本上重新批准"** (25 minutes)
- [x] **6. Mark #scenarios experimental, move the entry** (10 minutes)
- [x] **7. Optional: online toggle and status line** (15 minutes)
- [ ] **8. Optional: the two playground groups from section 8** (40 minutes)
- [x] **9. typecheck / test / build / check_fixtures, manual demo P1–P10, screenshots, update `docs/frontend/`, commit** (30 minutes)

Required (1–6, 9) about **3 hours 20 minutes**; with the two optional items about 4 hours 15 minutes. After step 2, each step can be accepted independently.

## 10. Post-review decisions (take precedence over the above)

| # | Decision | What it changes above |
| --- | --- | --- |
| 1 | The backend provides two tables, `node_kinds` and `edge_kinds`, in the version bundle | All of 3.2 becomes a table lookup; rule 3's trade-off is removed |
| 2 | Revoke approval = `sign` sends `terminal_id: null`, producing a new version | 4.2 step 5 calls this |
| 3 | "资料为占位" reads `Branch.synthetic_evidence` | 3.1 |
| 4 | Invalidation uses backend fields: `TradeProposal.approval_reset` → "前提已改动，请重新批准"; `TradeProposal.rival_changed` → "同一版本里另一份计划受了影响，值得再看一眼" ("another plan in the same version was affected; worth another look"). rival_changed doesn't judge whether it's a competing relationship, and the copy doesn't say "对手" ("rival") | 4.3's two inference rules are removed, replaced by reading the fields |
| 5 | Demo data for the evidenced style waits for re-recording with a real evidence pack; until then it's only previewed in the playground and labeled as a demo | Section 5 item 5 |
| 6 | Note: `UserJudgment.note`, sign request body adds optional `note` | 4.2, `SignBody` |
| 7 | The backend guarantees `original_statement` and `clarified_statement` are identical across plans in the same version; only one sentence shown at the top | 4.1 |
| 8 | The two playground groups in section 8 are not built; implement the defaults | Section 8, step 9 |
| 9 | The online toggle and status line are built | 4.6, step 7 |

Backend fields (d105c45 plus the points above): `ProposalDraft` / `TradeProposal.terminal_id` (required); `TradeProposal.approval_reset`, `rival_changed` (default false); `UserJudgment.note`; `Branch = {terminal_id, divergence_node_ids, own_node_ids, own_edge_ids, kind, trunk, synthetic_evidence}`; `VersionBundle = {graph, proposals, branches, node_kinds, edge_kinds, scenario, diff, excerpts}`; in the inspect / fork / sign return bodies `proposal` → `proposals`; `proposal_version = "{graph_version}.{terminal_id}"`.

Estimates change accordingly to: required 1–7, 9 about 3 hours 15 minutes (drop 8, steps 3 and 5 each 5 minutes shorter because of table lookups, plus 15 minutes for online).

### Done before starting (not dependent on backend data)

- `types.ts` gained Plan B's types (`Branch`, `BranchKind`, `PlanBBundle`, `ApproveBody`, new fields on `TradeProposal` / `UserJudgment`). `VersionBundle` isn't switched yet; it will be switched together with the fixtures in step 1, so every commit compiles.
- `status.ts`'s `BRANCH_KIND` (label, color, line style, hatching) and `components/BranchSwatch.tsx` (row-start miniature + "假设 · 未观测" pill).

### Visual preview (/#plan-b, built before starting)

- Uses c1-v3 of `c1_multi` (with the "代工停产" ("foundry shutdown") shock added) as demo data (`src/preview/demoPlanB.ts`): the LITE branch is manually set to evidence-backed, the TSM branch is hypothetical (contains the shock node), MRVL is inferred only · evidence is placeholder; the TSM and MRVL plans are handwritten. The page header permanently shows a "演示数据" ("demo data") note. After the backend delivers, delete this demo data and replace it with real fixtures.
- Everything used in the preview is to be reused by the real implementation: `GraphCanvas` gained an optional `branchView` (`node_kinds` / `edge_kinds` / highlighting) and `labelOf`; `DesignNode` gained `kind` / `synthetic` / `dimmed`; `ConditionRow` / `ProposalCard` gained "需要你确认" and `planB`; new component `ApprovePlans` (the whole B2 page); `lookup.ancestors`.
- Walked through in the browser: in B1 clicking LITE, TSM highlights the whole branch; in B2 approval isn't possible before understanding confirmation; approve TSM; switching approval to LITE pops "会撤销对硅光代工的批准" ("will revoke approval of silicon photonics foundry"); after revoking, shows "本版本没有批准任何计划（= 不交易）"; after checking "演示：改了假设之后回到这里" ("demo: come back here after changing the assumption"), the approved plan shows "前提已改动，请重新批准" and the rest show "另一份计划受了影响，值得再看一眼" ("another plan was affected; worth another look") (in real data these two are determined by backend fields). Screenshots `screenshots/pb-*`.

### UI text (decided by the main session)

- All UI text is centralized in `web/src/strings.ts` (`T`); no strings are written in components; `status.ts` only handles colors and line styles, and its labels also come from `T`. It's Chinese now; before submission it's all switched to English, changing only this one file.
- `src/__tests__/strings.test.ts` scans the source under `src` (with comments stripped) and fails if Chinese appears. Exceptions: `strings.ts` and demo data (`playground/demoLabels.ts`, `preview/demoPlanB.ts`, `scenarios/demoNames.ts`).
- Backend-generated content (node statements, conditions, reasons) will be English later; Chinese UI with English content is expected. The Chinese content of the MOCK fixtures is left alone until replaced by re-recording. `T.app.defaultEvent` must match the fixture's event and be switched together when changing to English.

### B2 streamlined version (Mia: the original is too full; reference Dynamic Island / Robinhood / OpenEvidence)

The preview page's B2 can switch between A / B / original in the top right; all three use the same set of props (`components/approve/model.ts`), and the approval logic is exactly the same.

- Shared pieces (`components/approve/Pieces.tsx`):
  - "你的想法" ("your idea") is collapsed into a pill at the top; click "对，就是这个意思" ("yes, that's what I mean") to confirm; "改一下" expands in place into an input box (Dynamic Island).
  - Approval is collapsed into a black pill at the bottom: "批准「X」" ("approve 「X」") / "改批这份 · 会撤销「Y」" ("approve this one instead · will revoke 「Y」") / "✓ 已批准「X」 撤销" ("✓ approved 「X」 revoke"); clicking it expands in place to show the threshold reminder, optional note, and confirmation, replacing the original dialog. When the idea hasn't been confirmed, the pill turns gray with a hint.
  - Plan details look like an OpenEvidence answer card: "你需要相信" are small tags with citation counts (superscript numbers; inferred-only ones say "仅推断"), clicking lists the numbered original text and sources below; "盯这些信号" ("watch these signals") is one per line (status dot · entry / exit · rule · deadline), the one missing a threshold has a yellow "需要你确认 · 设一个阈值" ("needs your confirmation · set a threshold"), clicking it shows an input box in place; the full plan card and per-premise checkboxes are tucked into "更多细节" ("more details").
- A expanding list (Robinhood): one big heading ("3 个结论，还没批准" ("3 conclusions, none approved yet") / "已批准：X" ("approved: X")) + one row per conclusion (name, instrument · direction, one status), clicking a row expands it in place; hypothetical-branch rows carry diagonal hatching across the whole row.
- B answer card (OpenEvidence): a row of pills at the top switches conclusions, below it only one card: large text "看多 TSM" ("bullish TSM"), a one-sentence thesis in a serif font, premises and signals.
- Screenshots: `screenshots/pb-b2-lite-*`. The original (`ApprovePlans`) is kept for comparison for now; once decided, delete the ones not chosen.

## Implementation log (after core-schema@ffbd2a3)

- Merged core-schema (including plan-b@ffbd2a3). `types.ts`'s `VersionBundle` switched in one go to `proposals` / `branches` / `node_kinds` / `edge_kinds`; `TradeProposal.terminal_id`, `approval_reset`, `rival_changed`, `UserJudgment.note` made required; the old `SignBody`, `Signoff`, `SignDialog` deleted.
- Fixtures: `make_fixtures.py` writes versions into a temporary `RunStore` and reads them out with `store.bundle(v)` (the same code as `GET /versions/{v}`); approval goes through `ep.sign`, forking through `ep.fork`. Five: `c1`, `c1_blocked`, `c1_multi`, `c1_approved` (v2 approves LITE → v3 changes the assumption; v4 approves TSM → v5 changes the same spot), `c4_abstain`. The content became English along with the golden graph. `check_fixtures.py`: no old `proposal` field; the plans' terminal set = the terminals on the graph; at most one approved per version; understanding confirmation identical across plans; `branches` / `node_kinds` / `edge_kinds` match a recompute with `catalyst.branches.dump_views`; diff matches a recompute relative to the parent version.
- B1: `Workspace` uses the backend's kind tables (`GraphCanvas`'s `branchView`); clicking a conclusion highlights its own part + ancestors, `PlanSummary` on the right; the key dependencies of all three plans are marked (`toFlow`'s `keyClaimIds`).
- B2: uses streamlined A (`components/approve/ApproveList`) — Mia said the original was too full; A's structure is exactly design 4.1's "list on top, plan below", just with the plan expanding in place within the selected row. Approve = `sign` (with this plan's draft, the edited understanding, the note), revoke = `sign` sending `terminal_id: null`; when switching approval to another plan, the bottom pill states which one will be revoked. The preview page can still switch A / B / original.
- B3: "计划 vN → vM" ("plans vN → vM") lists every plan in the scenario version (gate, support, whether approved), `approval_reset` → "前提已改动，请重新批准", `rival_changed` → "同一版本里另一份计划受了影响，值得再看一眼"; adds "在这个版本上重新批准 →".
- #scenarios: removed from the main navigation, entered only from the node-visuals playground's page header, with "（实验）" ("(experimental)") in the title.
- Online: a toggle in the top bar, `createRun` takes `online`, the status line shows `web.message` verbatim (under MOCK it's "MOCK：不联网").
- Short titles for English content: without a label, English is truncated to the first 4 words (Chinese still truncated to 10 characters).
- MOCK: approval prefers the approval versions recorded in the fixture (so the backend-computed approval_reset etc. are real), and only when none was recorded does it change data in memory with the notice "gate 未重算" ("gate not recomputed"); forking finds the recorded version by "which version it starts from + this layer's operation".

### P1–P10 under MOCK (2026-10-19, built-in browser)

| # | Result |
| --- | --- |
| P1 | 3 conclusions; the fixtures use a placeholder evidence pack, so branches are all "仅推断", and the "资料为占位" ones are shown |
| P2 | Click LITE: its own part + the shared trunk highlighted, the rest recede; on the right the plan summary + "去批准这份计划 →" |
| P3 | In B2 the LITE row expands in place; before confirming "你的想法" the approve pill is gray, with the hint "先确认上面「你的想法」" ("confirm 「你的想法」 above first") |
| P4 | Confirm, set threshold, approve: LITE "✓ 已批准", the big heading becomes "已批准：…" (c1 has no recorded approval version, so the notice gate not recomputed appears) |
| P5 | Select TSM: the pill says "改批这份 · 会撤销「…」", after confirming only TSM is approved |
| P6 | Revoke: none of the three rows approved, the big heading goes back to "3 个结论，还没批准" |
| P7 | c1_approved: approve LITE (recorded c1-v2) → in B3 change the external light source → c1-v3: LITE "前提已改动，请重新批准", the rest "另一份计划受了影响" ("another plan was affected") |
| P8 | Approve TSM (c1-v4) → change the same spot → c1-v5: TSM keeps "✓ 已批准" and has "另一份计划受了影响" |
| P9 | "在这个版本上重新批准" → B2, current version c1-v3, LITE shows "前提已改动，请重新批准"; on B1 the LITE branch is in the hypothetical style |
| P10 | Node-visuals playground page header "多情景（实验）" ("multi-scenario (experimental)") → #scenarios, title has "（实验）", displays correctly; the main navigation no longer has it |

Also checked along the way: c1_blocked's LITE is BLOCKED; c4_abstain shows the abstention; with the online toggle on, the status line appears; the preview page (#plan-b) B1 / B2 work; no console errors. Screenshots: `screenshots/planb-b1-highlight.jpg`, `planb-b3-reset.jpg`.

**Not done yet**: connecting the local real backend with `VITE_MOCK=0` and walking B1 → B2 → B3, waiting for the main session to provide the recording directory.

### B2 final: answer card (chosen by Mia, 2026-10-19)

- The official B2 uses the answer card (`components/approve/ApproveCard.tsx`): the "你的想法" pill at the top, a row of pills switching conclusions (approved ones carry ✓, ones revoked by a fork carry an orange dot), below that one card: large text "看多 LITE" ("bullish LITE"), a one-sentence thesis, kind label, premises (with citation counts, click to see original text), signals (fill missing thresholds in place), the full plan card tucked into "更多细节"; at the bottom the black pill for approve / switch approval / revoke.
- The hypothetical branch's banner states clearly which assumption: the shock node on the branch, or the assumption changed in the scenario that is among this branch's ancestors (look up `scenario.ops`'s target).
- The list version (ApproveList) and the original (ApprovePlans) have been deleted; the draft and understanding confirmation types moved to `components/approve/model.ts`. The preview page (#plan-b)'s B2 also has only the answer card now. Screenshots: `screenshots/planb-b2-card.jpg`, `pb-b2-lite-b-card.jpg`.
- Walked through in the browser: the pill is gray before confirming the idea; approve LITE (recorded c1-v2); switching to TSM the pill says "改批这份 · 会撤销…" ("approve this one instead · will revoke ..."); in B3 change the assumption → "在这个版本上重新批准" → the card shows "前提已改动，请重新批准" and the banner with the assumption's name; after approving and then revoking there's no ✓.

## Round after core-schema@248abcf (user_event, real-backend walkthrough)

- Merged core-schema (fast-forward to 248abcf). `Graph.user_event` added to `types.ts`. Typecheck, tests and `check_fixtures.py` passed right after the merge.
- Analyze wait hint (`components/BusyHint.tsx`): the API exposes no stage or progress, so the hint shows only real elapsed time (m:ss, ticking every second) and a sentence saying the analysis usually takes two to three minutes and that the backend does not report which step it is on. There is no progress bar and no percentage. With the online toggle on, it adds one sentence about web search. Fork and approve get the same hint with their own notes. A unit test checks that the elapsed time is real and that no percentage appears.
- Default event in `strings.ts` is now English ("Photonic chips are being adopted faster than expected"); all other UI strings stay Chinese.
- B3 baseline canvas now uses the same branch-kind styling as B1 (the scenario canvas still uses assessment coloring).
- Hypothetical banner on the answer card: it names the assumption changed in the scenario first, then a shock node, and skips the node that restates the user's own event (same rule as the backend's `user_event_nodes`: `original_statement` equals `user_event`, ignoring case, whitespace and trailing punctuation). Before this fix, the live D1 run showed the user's own event as the reason.
- Terminal cards show only the first instrument, cut to 14 characters, with the full list in a tooltip (the real model wrote "Brent crude futures, oil ETFs such as USO").
- Docs in `docs/frontend/*.md` translated to English; literal Chinese UI strings are kept with English glosses.

### Real-backend walkthrough (2026-10-19, Haiku 5.5, medium effort, port 8020, runs/e2e)

- C1 ("Photonic chips are being adopted faster than expected"): Analyze returned in about 70 seconds. The graph carried `user_event`, and its restating node was not hypothetical. The model produced a single branch (TSEM, model_only), so branch kinds could not differ in this run.
- D1 ("I think the Strait of Hormuz is going to open up next week"): Analyze returned in about 85 seconds, again with a single branch (Brent, model_only). The canvas and the answer card both showed "仅推断". B2 approval created r-v2. A B3 fork on `h.transit` created r-v3 in about 50 seconds; the backend set `approval_reset` on the approved plan, B3 showed "前提已改动，请重新批准", "在这个版本上重新批准" opened B2 on r-v3 with the same notice, and B1 on r-v3 showed the branch in the hypothetical style. The B3 baseline canvas showed branch-kind tags.
- Not verified live: two branches with different kinds in one graph. Both live runs produced a single branch. The differing-kind rendering is covered by the plan B preview (demo data) and by unit tests on the fixtures, not by a live run.
- Backend observation: after a fork, every own node of a hypothetical branch is marked hypothetical in `node_kinds`, including the node that restates the user's event, because own nodes take the branch's kind.
- Screenshots: `screenshots/live-analyze-wait.jpg`, `live-b2-card.jpg`, `live-b3-fork.jpg`, `live-b1-after-fork.jpg`.

## B1 canvas cut off under the side panel (fixed after core-schema@724c975)

- Symptom (main session, run 20261019-101248 "Google just launched a new AI model…"): the right part of a wide graph sat under the right-hand panel, and "fit view" did not help.
- Cause, confirmed in headless Chrome (which renders frames): React Flow fits the graph only once, when it mounts. When the canvas later gets narrower (window or pane resized), the graph keeps its old fit. With the fix disabled, the canvas ended at 500px while the nodes ended at 1030px. In a normally rendered page the fit-view button does fix it. In the hidden Claude browser pane it does nothing, because a hidden pane is a background page with no rendering frames, so ResizeObserver, requestAnimationFrame and React Flow's own measuring and fitView do not run. That is why the button seemed broken in both our tests.
- Fix (`components/GraphCanvas.tsx`): `FitOnResize` refits whenever React Flow's stored canvas size changes. As a fallback for pages that are not being rendered, it compares the real container size with the stored size once per second and dispatches a `resize` event when they differ, so React Flow re-measures. Node measurements are also kept between renders (`onNodesChange` for dimension changes), and the fit-view button uses the same padding.
- Verified in headless Chrome for both runs (12-node Google run and 6-node TSMC control): after narrowing from 1600 to 900px wide, the graph refits inside the canvas; after zooming in, the fit-view button brings it back. B3 and the plan B preview use the same component.
- Dev aid: in real mode, `?run=<run_id>&v=<version>` opens a stored run without calling the model.
- The B2 plan-switcher fix from 724c975 (`.ap-page > * { flex-shrink: 0; }`) is unchanged.

## Research workspaces (frontend only, localStorage)

- Problem (Mia): starting a new question kept the previous graph on screen while the new one was being analyzed, and approvals from different questions were mixed in one version history.
- Model: one workspace per question. Analyze always creates a new workspace and switches to it at once, so the canvas shows the waiting state, never the previous graph. Fork and approve versions are recorded only in the workspace that started them; if the user has switched away when a write returns, the version is still recorded there but the visible view is not touched.
- Storage (`web/src/workspaces.ts`, key `catalyst.workspaces.v1`): metadata only — event, online flag, created time, run_id, versions in order, current base version, status (analyzing / ready / failed + error), abstain note, approvals (version, terminal_id or null for "approved none", plan title, time), MOCK fixture name. Graphs and plans stay in the backend and are fetched with `GET /api/runs/{id}/versions/{v}` on open. Every read and write is wrapped in try/catch; empty, blocked or corrupted storage gives an empty list and the page keeps working (a banner says history is not being saved when a write fails). A workspace still "analyzing" when the page was closed comes back as failed ("interrupted") with a retry button.
- UI (`components/WorkspaceSidebar.tsx`): left column with "＋ 新建研究", an "已批准的计划" overview across workspaces (the latest approval per workspace; a revoke removes it), and "研究记录" with each question's date, status chip, online flag and approved plan. Clicking a record reopens it from the backend; clicking an approved plan opens that workspace on B2. If the backend no longer has the run, the workspace shows "这次研究在后端找不到了" and its chip turns to "找不到了".
- No backend change and no new endpoint. MOCK works the same way (the fixture name is stored so reopening switches back to it).
- Tests: `__tests__/workspaces.test.ts` (create, switch, version isolation, approve and revoke, overview, save and reload with interrupted, corrupted / throwing / null storage).
- Live walkthrough (Haiku, medium; API 8022 + Vite 5176, headless Chrome): Q1 "OPEC+ unexpectedly cuts oil output by 2 million barrels per day" (run 20261019-111552, 7 nodes) and Q2 "Photonic chips are being adopted faster than expected" (10 nodes). Starting Q2 cleared the canvas to the waiting state immediately (0 nodes) while Q1 stayed in the list as 完成. Approved "Supplier volume gain · LITE" in Q2; it appeared in the overview and on Q2's record, Q1 stayed 未批准. Switching Q2 → Q1 → Q2 restored each graph and question text. A page reload restored the list and reopened Q2. Pointing Q1's stored run at a missing run showed the missing state; corrupting the storage gave an empty list without errors. The same script passed in MOCK.
- Not verified live: starting a second question while the first is still analyzing (the code records the first result into its own workspace without touching the view; covered by reasoning, not by a run).
- Screenshots: `screenshots/ws-2-analyzing.jpg`, `ws-3-approved.jpg`, `ws-4-q1.jpg`, `ws-8-missing.jpg`.

## Node visual grammar A/B (`/#grammar`, playground only)

- Problem (Mia): the canvas used several channels at once (role tint, hatch, orange border, ring, per-card tags), and it was unclear what each colour meant and which nodes can be changed.
- Rule: one visual channel answers one question. All nodes are white. Type = symbol (Lucide-style line icons: zap = event, cloud-lightning = shock, cog = inference step, circle-help = assumption, flag = conclusion). Conclusions get their own shape. Branch kind = border and edge line style only (solid evidenced, dashed model-only, dotted hypothetical). Evidence = one text line at the bottom ("2 条支持 · 1 条反对", only the opposing count is red). Check-first = a single orange "先查" badge, nothing else is orange. Editable = a pencil button on assumption nodes (the playground only shows a toast; the real version would open B3 on that node).
- Option A: a round symbol badge, no type word; conclusions are capsules with a thick dark border. Option B: every card starts with "symbol + type word"; conclusions have a dark header band carrying the ticker.
- Background research (quick): Munzner / Bertin — shape and hue for categories, length or text for amounts; mixing two channels on one boundary slows search; dashing is the preferred line encoding for uncertainty; BPMN and flowchart standards use shape for type with an inner glyph.
- Not changed: the real B1 / B3 canvas. It switches only after Mia picks A or B. Screenshots: `screenshots/grammar-A.jpg`, `grammar-B-focus.jpg`.
