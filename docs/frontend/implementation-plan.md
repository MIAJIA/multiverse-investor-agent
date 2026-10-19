# Frontend MVP implementation plan (B1 / B2 / B3)

2026-10-18 · frontend branch (based on core-schema@129dd12)

This document follows the corrections made after review and takes precedence over the original text of `docs/frontend-design.md`. The principle is unchanged: **the model proposes, the code decides; the frontend only displays, edits, confirms, and compares, and does not compute anything itself.** gate, status, support_status, version numbers, condition evaluation, write scope, assessment, and diff all come from backend return values.

## Scope

| Tab | Do | Don't do |
| --- | --- | --- |
| B1 Research Workspace | One-line event input + Analyze; read-only React Flow canvas (coordinates by depth); click a node → right-hand panel: details, evidence (evidence on incoming edges, with the excerpt's original text looked up by excerpt_id), conditions | Auto layout, collapsible groups, minimap, edge hover, drag bar, What-if toolbar, candidate card selection |
| B2 Sign-off | Per-assumption table (Confirm checkbox); proposal card (status and gate shown separately, entry marked "且" ("and"), exit marked with exit_logic); thresholds and deadlines of entry / exit conditions are editable; Sign → three-field form (testable judgment, criteria, deadline) | Execute button, export, history |
| B3 Scenario Diff | Pick a node + enter a new assumption value → fork; baseline / scenario toggle; canvas colored by the three assessment states; three blocks on the right: challenged premises and reasons, what to check next, proposal v1 → v2 | Multiple scenarios, scenario naming, AddShock UI, free-text what-if |

The three tabs are three tabs on the same page, sharing one state.

## Tech stack

Vite 8 + React 19 + TypeScript + `@xyflow/react` 12 + `useState`; tests use Vitest. No Next.js template, shadcn, Zustand, or ELK. Styling is one handwritten `styles.css` (CSS variables + a few classes); no Tailwind.

Verified on this machine: Node v26.10.0, npm 11.19.1; installed `react@19.3.1 react-dom @xyflow/react@12.12.0 vite@8.3.4 @vitejs/plugin-react@6.1.2 typescript@7.0.2 vitest@5.0.5 @types/react@19.3.0` in a temp directory with no errors, and `tsc --version` works. typescript 7 is the native compiler; if some tool is incompatible with it, fall back to `typescript@~5.9`.

## File list and responsibilities

```text
web/
  package.json            scripts: dev / build (tsc --noEmit && vite build) / test (vitest run) / typecheck
  vite.config.ts          React plugin; /api proxied to CATALYST_API (default http://localhost:8000)
  tsconfig.json
  index.html
  fixtures/c1.json        generated fixture, not handwritten (see below)
  scripts/
    make_fixtures.py      runs the catalyst entrypoints offline, generates fixtures/c1.json
    check_fixtures.py     validates the fixture against the schema (parse_graph / TradeProposal / Scenario / diff recompute)
  src/
    main.tsx              mounts <App/>
    App.tsx               the only state (useState), three tabs, all backend calls are made from here
    types.ts              TS mirror of schema.py (field names unchanged) + VersionBundle
    api.ts                createRun / getVersion / fork / sign; the MOCK switch lives here
    toFlow.ts             pure function: (graph, opts) → { nodes, edges }, coordinates computed by depth
    status.ts             the single mapping table from every enum → label and color
    lookup.ts             read-only lookups: a node's incoming-edge evidence, conditions on a node, the claim key_dependency points to
    components/
      ClaimNode.tsx       generic node card (role sets color, evidence_status in small text, assessment as outline, key dependency as outer glow)
      GraphCanvas.tsx     ReactFlow wrapper: nodesDraggable=false, click callback
      NodePanel.tsx       details / evidence / conditions sections (not three sub-tabs, stacked vertically)
      ProposalCard.tsx    shared by B2 and B3
      Workspace.tsx       B1
      Signoff.tsx         B2: assumption table + condition editing + proposal card
      SignDialog.tsx      B2: three-field form
      Scenario.tsx        B3: fork form + toggle + canvas + three right-hand blocks
    styles.css
    __tests__/
      toFlow.test.ts
      status.test.ts
      lookup.test.ts
```

## Component tree

```text
<App>                                  all state lives here
  <Header>                             event input + Analyze; MOCK badge; current run / version (small text)
  <Tabs>                               Workspace | Sign-off | Scenario
  ├─ <Workspace bundle selected onSelect>
  │    <GraphCanvas flow onNodeClick/> ← toFlow(bundle.graph, {keyClaimId})
  │    <NodePanel bundle nodeId/>        details · evidence (Supporting n / Contradicting n) · conditions
  ├─ <Signoff bundle signoff onChange onSign>
  │    <AssumptionTable/>                one row per claim: statement, invalidation condition (rule + deadline), evidence_status, Confirm
  │    <ProposalCard proposal editable overrides onEdit/>
  │    <SignDialog open defaults onSubmit/>
  └─ <Scenario base scenarioBundle viewing onFork onToggle>
       <ForkForm nodes onSubmit/>         dropdown to pick a node + one-line new value → POST fork
       <VersionToggle/>                   baseline {base_version} / scenario {version} + "假设，未观测" ("hypothetical, not observed")
       <GraphCanvas flow/>                ← toFlow(graph, {assessment, changedTarget})
       <DiffSidebar>
         challenged premises               claims with scenario.assessment == challenged + assessment_reason
         what to check next                proposal.scenario_ref.next_checks
         proposal v1 → v2                  fields of the two ProposalCards side by side + diff.changed_claim_ids + scenario.ops
```

## State structure (A1: only one copy)

```ts
type VersionBundle = {                // = the return value of GET /api/runs/{id}/versions/{v}
  graph: Graph;
  proposal: TradeProposal | null;
  scenario?: Scenario | null;         // only forked versions have this
  diff?: GraphDiff | null;            // relative to scenario.base_version, computed by the backend
  excerpts: Excerpt[];                // excerpts that entered the context when this version was reasoned (store's observations/<v>.json)
};

type AppState = {
  runId: string | null;
  versions: Record<string, VersionBundle>;  // the only data cache: bundles stored by version number exactly as the backend returned them
  baseVersion: string | null;               // the version B1 / B2 look at, also the base_version for fork
  scenarioVersion: string | null;           // the version produced by the most recent fork
  viewing: 'base' | 'scenario';             // B3's toggle
  tab: 'workspace' | 'signoff' | 'scenario';
  selectedNodeId: string | null;
  signoff: {                                // only user input not yet submitted; sent to the backend as one package on sign
    confirmedClaimIds: string[];
    conditionOverrides: Record<string, { threshold?: number | null; deadline?: string }>;
  };
  busy: boolean;
  errors: string[] | null;                  // rejection reasons from the backend / validator, shown verbatim
};
```

- There is no second copy of nodes, edges, conditions, or evidence: every render computes them fresh from `versions[v]` with `toFlow` / `lookup`.
- Canvas nodes are not draggable (`nodesDraggable={false}`), so `useNodesState` isn't needed and positions aren't stored.
- `signoff` only holds input the user hasn't submitted yet; after a threshold is changed, the proposal card shows "已修改，签字后由后端重算" ("modified, will be recomputed by the backend after signing"), and gate still shows the value the backend gave; the frontend does not predict it.

## API and MOCK switch

`src/api.ts` exports four functions with the same signatures in both modes:

```ts
createRun(body: { event: string; target?: string; packs?: string[] }): Promise<RunCreated>
getVersion(runId: string, version: string): Promise<VersionBundle>
fork(runId: string, body: { base_version: string; op: Op }): Promise<WriteResult>
sign(runId: string, body: SignBody): Promise<WriteResult>

type WriteResult = { ok: boolean; errors: string[]; version: string | null };
```

- Switch: `const MOCK = import.meta.env.VITE_MOCK !== '0'`. On by default (the repo root `.gitignore` ignores `.env`, so no `.env` file is used); once the backend is up, `VITE_MOCK=0 npm run dev`. The top-right of the page shows a "MOCK · fixture c1" badge, so the fixture isn't demoed as if it were real output.
- Real mode: `fetch('/api/...')`, proxied to the backend by the Vite dev server. On non-2xx, the `errors` (or `detail`) in the response body is thrown to the UI verbatim.
- After every write operation, App calls `getVersion` once with the returned `version`, stores it in `versions`, and redraws everything — this is the design doc's "operation → new version number → redraw".
- MOCK mode: `await import('../fixtures/c1.json')` (dynamic import, not bundled in real mode).
  - `createRun` → `{ run_id: 'mock', version: <the version whose parent_version is null>, discover: null }`;
  - `getVersion` → `fixture.versions[v]`;
  - `fork` → returns that version number when the op's kind and target match `scenario.ops[0]` of the scenario version in the fixture; otherwise returns `ok:false`, errors = "MOCK：fixture 只录了 <target> 的 change_assumption" ("MOCK: the fixture only recorded change_assumption for <target>"). The value text is not compared.
  - `sign` → does not recompute gate (that's the backend's job): writes the user input into that version's proposal `user_judgment` (`confirmed: true`), returns the same version number, and adds, separately from errors, a notice "MOCK：gate 未重算" ("MOCK: gate not recomputed"). This is the only place in MOCK that changes data; clearly commented in the code.

### Backend endpoint shapes and suggested changes

| Endpoint | Original shape | Suggestion |
| --- | --- | --- |
| `POST /api/runs {event, target?, packs?}` | `{run_id, discover?, inspect}` | Add `version` (the graph version produced by inspect). Without target, the backend picks the first grounded candidate into inspect as `cmd_run` does; `discover` is returned as is, and the UI lists the candidates read-only (not shown if time runs short). When `inspect.ok=false` or `no_chain=true`, the UI shows errors / `no_chain_reason`. |
| `GET /api/runs/{id}/versions/{v}` | `{graph, proposal, scenario?, diff?}` | **Add `excerpts`** (store's `observations/<v>.json`). Without the excerpts' original text, B1's evidence panel can only show excerpt_id. Define `diff` as relative to `scenario.base_version`. |
| `POST /api/runs/{id}/fork {base_version, op}` | fork entrypoint return value | Keep the entrypoint return value, but add a top-level `version` (= `graph.version`, null on failure). When the backend calls `ep.fork` it must pass `proposal=` (preferring that version's signed proposal), otherwise v2 has no proposal and no `scenario_ref`, and B3's second and third blocks are empty; `pack` uses the baseline version's observations. |
| `POST /api/runs/{id}/sign {...}` | the signed proposal | Return `WriteResult` (`{ok, errors, version}`), then the frontend does a GET. Two points need a backend decision; see items 4 and 5 of the next section. |

## Fixture generation

`web/scripts/make_fixtures.py`, run from the repo root:

```bash
~/Downloads/multiverse-investor-agent/.venv/bin/python web/scripts/make_fixtures.py
```

(The worktree has no `.venv`, so it borrows the main repo's; the first line of the script inserts the worktree root at `sys.path[0]`, ensuring this branch's `catalyst/` is what gets imported.)

Steps:

1. Read the golden graph `eval/fixtures/c1_graph_v1.json` and the evidence pack `c1_evidence_pack.json`, `EvidenceProvider.register(pack)`.
2. **Baseline proposal**: `ep.derive_proposal(ProposalDraft, parse_graph(golden), model="scripted")`. ProposalDraft is a short piece written in the script (instrument LITE long, entry `cond.c1.cpo_shipments` + `cond.c1.els_design_wins`, exit `cond.c1.dsp_guidance`, exit_logic ANY, key_dependency → `c1.assume.external_laser`, user_judgment rewrites one sentence). gate / status / support_status / meta are still derived by code.
   - Why not go through `ep.inspect`: tried in a temp directory; the golden graph doesn't pass inspect's `_root_issues` (`c1.event`, `c1.assume.capex`, `c1.assume.external_laser` have no incoming edges yet are marked supported); see item 1 of the next section.
   - This draft is the only handwritten "model output" in the fixture, stated in the file's `_source.notes`; replace it wholesale once there's a real recording.
3. **Fork**: `ep.fork(golden, c3_change_assumption.op, reasoner=DemoReasoner(), pack=pack, proposal=<baseline proposal>, config=Config(today="2026-10-18", run_prefix="c1"))`. `DemoReasoner` inherits from `eval.fakes.ScriptedReasoner` and only replaces assessment's `reason: "scripted"` with human-readable demo sentences (the dictionary is in the script); everything else is inherited from the parent class. Trial run done: ok, produces `c1-v2`, `changed_claim_ids = [external_laser, laser_demand, term.laser_vendor]`, challenged = `[c1.laser_demand, c1.term.laser_vendor]`, v2 proposal gate=WAIT, support_status=challenged.
4. Write `web/fixtures/c1.json`, in the same format as `python -m catalyst promote`, with two extra fields per version:

```json
{
  "_source": {"script": "web/scripts/make_fixtures.py", "case": "C1+C3a", "notes": ["…"]},
  "versions": {
    "c1-v1": {"graph": {...}, "proposal": {...}, "scenario": null, "diff": null, "excerpts": [...]},
    "c1-v2": {"graph": {...}, "proposal": {...}, "scenario": {...}, "diff": {...}, "excerpts": [...]}
  },
  "latest": "c1-v2"
}
```

The shape of `versions[v]` is exactly the return value of `GET /versions/{v}`, so MOCK's `getVersion` does no transformation. Suggest the main session have `promote` also write out `diff` (relative to parent) and `excerpts` (observations), so that later recorded fixtures can directly replace this file with no frontend changes.

## Field mapping to the schema

| What the UI shows | Comes from (schema.py field) | Notes |
| --- | --- | --- |
| Node color | `Claim.role`: event blue / assumption, intermediate green / terminal purple / shock orange | intermediate shares assumption's color; a corner tag on the card distinguishes them |
| Node main text / original wording | `Claim.statement` / `Claim.original_statement` | When the two differ, details show "原话" ("original wording") |
| Node small text | `Claim.evidence_status` + count of incoming-edge evidence | |
| Instrument | `Claim.instruments` (terminal) | |
| Key dependency highlight | `proposal.key_dependency.claim_id`, or `key_dependency.condition_id` → that condition's `claim_id` | A reference on the proposal, not a node field; the canvas only does a lookup. `why` is shown in details |
| Edge solid / dashed | `Mechanism.model_only` | In TS the field name is `from` (the schema's alias) |
| Edge label | `Mechanism.channel` + `sign` | The one-sentence mechanism is only shown in details |
| Node evidence | `evidence[]` of edges pointing to the node (`edge.to == id`), split by `stance` into Supporting / Contradicting; `excerpt_id` → `bundle.excerpts[].text / source / date` | `rebuttal` shown under the contra card; when all incoming edges are model_only show "仅模型推断" ("model inference only"); with no incoming edges show "证据只挂在边上，这个节点没有入边" ("evidence only hangs on edges; this node has no incoming edges") |
| Condition row | `Condition.rule` (large text); `series ?? source`, `anchor`, `deadline`, `threshold` (null → "你来定" ("you decide") + `threshold_note`), `comparator` | |
| Two condition badges | `verification_status` (可核实 verifiable / 未核实 unverified), `evaluation_status` (已满足 met / 未满足 not met / 未知 unknown) | Not merged |
| Proposal status | `TradeProposal.status` (draft / needs_review) and `gate` (WAIT 先别动 "hold off" / BLOCKED 受阻 "blocked" / READY_FOR_REVIEW 待复核 "awaiting review") **as two separate badges** | There is no Ready to execute |
| Proposal support | `support_status` | |
| Entry / exit | `entry_conditions` (marked "且"), `exit_conditions` + `exit_logic` (ANY "或" ("or") / ALL "且", shown explicitly) | |
| Direction | `direction.instrument / side / horizon_days / note` | |
| Sign form defaults | `user_judgment.clarified_statement`, `criteria`, `deadline`; when `requires_user_confirmation` is true, show `original_statement` side by side | Submitted fields: `clarified_statement / criteria / deadline / confirmed_claim_ids / condition_overrides` |
| Signed | `user_judgment.confirmed`, `confirmed_claim_ids` | |
| Three-state coloring | `Scenario.assessment[claim_id]`: challenged orange border / unaffected gray background with check / unresolved gray background with dashed line | Two layers with evidence_status, both shown on the card |
| Changed assumption | `Scenario.ops[0].target` | Annotation only; see item 3 of the next section |
| Challenge reason | `Scenario.assessment_reason[claim_id]` | |
| What to check next | `proposal.scenario_ref.next_checks[]` | |
| Change tracing | `diff.changed_claim_ids`, `nodes_changed / edges_changed / conditions_changed` | Provided by the backend; the frontend doesn't compare |
| Version number | `Graph.version`, `parent_version`, `Scenario.base_version` | Only appears in small text; B3's toggle takes the baseline by `scenario.base_version`, not hard-coded v1 / v2 |

## Inconsistencies with the schema or open questions found

1. **The golden C1 graph doesn't pass inspect's own checks.** `c1.event`, `c1.assume.capex`, `c1.assume.external_laser` have no incoming edges yet are `supported`, and `entrypoints._root_issues` rejects them. The fixture script therefore bypasses inspect and calls `derive_proposal` directly. The UI will also show "supported but the evidence panel is empty". Needs a decision: change the golden (set root nodes to unknown), or relax the rule for event / assumption.
2. **ScriptedReasoner has no inspect stage**, so there's no ready-made baseline proposal; the script hand-writes the ProposalDraft (see above), and code derives the remaining fields.
3. **The changed assumption itself is `unaffected`.** It's in the write scope, but ScriptedReasoner only marks two downstream nodes as challenged, so `c1.assume.external_laser` will be painted gray "unchanged" in B3, which reads wrong. The frontend will use `scenario.ops[0].target` to add an extra "改动的假设" ("changed assumption") corner tag (display only). Whether the code should give the target a fixed assessment (none of the existing three states fits) is for the main session to decide.
4. **sign conflicts with immutable snapshots.** `RunStore._put` doesn't allow overwriting `proposals/<v>.json`, so signing can't modify the proposal in place. Suggest writing the sign result to a separate location (e.g. `signoffs/<v>.json`), and the GET bundle returns the signed proposal.
5. **condition_overrides are lost on fork.** `derive_proposal` takes conditions by id from the new graph's `conditions`; if the thresholds / deadlines the user changed while signing exist only in the proposal, the v2 proposal reverts to the original values. Two options: (a) when overrides are non-empty, the backend first produces a new graph version (OpKind needs a `confirm_condition` added; no model call; re-evaluate conditions, re-derive the proposal), then signs on that version, and sign returns the new version number; (b) on fork, the backend re-applies the overrides. Suggest (a); it's the design doc's confirm_condition. The frontend can handle either, because fork's base_version always uses the version number sign returned. Also: when changing deadline, `observation_window.end` must be ≤ deadline (validator line 61), and the backend has to change it too; when filling threshold on a numeric condition, there must be a comparator.
6. **OpKind has no confirm_condition / sign**; what a signature is recorded as in the oplog hasn't been decided.
7. **`scenario_ref.next_checks` is `list[str]`.** The design doc wants an event-type Condition (large-text time limit + two branches: observed / not observed); the MVP only shows strings.
8. **There's no proposal-level diff.** B3's "proposal v1 → v2" can only show the two proposals' gate / status / support_status / scenario_ref side by side, plus the graph diff's `changed_claim_ids` and `scenario.ops`; the frontend doesn't judge "what changed". If highlighting is wanted, suggest the backend add `proposal_changes` to the fork return value.
9. **promote doesn't output `diff` and `excerpts`** (see the fixture section above), so recorded fixtures can't directly replace it yet.
10. `UserJudgment.probability` exists, but per review the sign form has only three fields and doesn't collect it.
11. B2's "Needs review" user status: the frontend doesn't derive it; there's only Not started / Confirmed; `evidence_status` and the condition's `verification_status` are shown side by side, and the judgment is left to the user.

## Fallback

Decision point: **minute 140 of the whole project**: check whether step 5 of `step-by-step.md` (B1 canvas shows the fixture's 10 nodes and 9 edges) is checked off. If not, stop React and build `web/streamlit_app.py` instead: read the same `fixtures/c1.json`, draw the graph with Graphviz (scenario version colored by assessment), below it the condition list, the proposal card (status / gate separate), and a fork dropdown (only supports the one scenario in the fixture). Estimated 20 minutes. The main session keeps the project clock; please give a reminder when the time comes.

## Cut order (when over time)

1. The read-only Discover candidate list at the top of B1
2. Edge labels (channel + sign)
3. B2 deadline editing (keep threshold only)
4. B3 proposal comparison keeps only the three rows gate / status / support_status
