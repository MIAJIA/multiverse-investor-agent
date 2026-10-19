# Frontend MVP execution steps

Total budget about 55 minutes. Check off each step when done; **step 5 is the fallback decision point**: if step 5 still isn't checked at minute 140 of the whole project, switch to Streamlit (see "Fallback" in implementation-plan.md).

- [x] **1. Scaffolding (4 minutes)**
  Under `web/`, handwrite `package.json`, `vite.config.ts` (/api proxy), `tsconfig.json` (strict), `index.html`, (MOCK on by default, written in `api.ts`: the repo root `.gitignore` ignores `.env`); `npm install react react-dom @xyflow/react` and `-D vite @vitejs/plugin-react typescript @types/react @types/react-dom vitest`. Add `web/node_modules`, `web/dist` to `.gitignore`.
  Done when: `npm run dev` shows a blank page.

- [x] **2. Types and fixture (8 minutes)**
  `src/types.ts` copied from `catalyst/schema.py` (including enum value arrays); `scripts/make_fixtures.py` (derive_proposal + fork + DemoReasoner) generates `fixtures/c1.json`; `scripts/check_fixtures.py`.
  Done when: both scripts run, check exits 0; after rerunning make, `git diff` is empty.

- [x] **3. status / toFlow / lookup + unit tests (6 minutes)**
  `status.ts`, `toFlow.ts` (longest-path depth → y, index within layer → x), `lookup.ts`; three test files.
  Done when: `npm test` is all green.

- [x] **4. api.ts and App state (4 minutes)**
  Four functions + MOCK branch; the single `useState` in App, empty shells for the three tabs, the Header's Analyze calls `createRun` → `getVersion`.
  Done when: after clicking Analyze, `versions['c1-v1']` has a value (print the version number with `<pre>` first).

- [x] **5. B1 canvas and panel (12 minutes) — fallback decision point**
  `ClaimNode`, `GraphCanvas`, `NodePanel`, `Workspace`; color variables in `styles.css`.
  Done when: manual script steps 1–6 pass.

- [x] **6. B2 sign-off (9 minutes)**
  `Signoff` (assumption table + Confirm + condition threshold / deadline inputs), `ProposalCard`, `SignDialog`; signing calls `sign` → `getVersion`.
  Done when: manual script steps 7–12 pass.

- [x] **7. B3 scenario comparison (8 minutes)**
  `Scenario`: ForkForm → `fork` → `getVersion`; baseline / scenario toggle; `toFlow` gets assessment; three right-hand blocks.
  Done when: manual script steps 13–17 pass.

- [x] **8. Wrap-up (4 minutes)**
  `npm run typecheck && npm test && npm run build`; `check_fixtures.py`; walk through B1 → B2 → B3 from the start; commit to the frontend branch (no push).
  Done when: all automation in test-plan.md passes, and one complete flow is demoed.

Cut order when over time: Discover candidate list → edge labels → B2 deadline editing → B3 proposal comparison keeps only three rows.

## Execution log (2026-10-18)

- Implementation started 20:48, the B1 canvas was up at 20:55 (fallback decision point: 30 minutes after start); did not switch to Streamlit.
- Automation: `npm run typecheck` passes; `npm test` 3 files, all 23 tests pass; `npm run build` passes (the fixture is a separate dynamic chunk, not loaded in real mode); `check_fixtures.py` OK (1 fixture, 13 enums); rerunning `make_fixtures.py` gives unchanged output.
- Manual demo (MOCK, built-in browser 1440×900): steps 1–17 all work, screenshots in `screenshots/` (b1-workspace, b2-signoff, b3-scenario).
  - Exception: the "change a deadline" part of step 10 couldn't be verified, because the built-in browser couldn't type into the date input; changing the threshold was verified.
- One fix made during the demo: after signing, the assumption table's checkboxes went back to Not started. Now, after signing, the proposal's `confirmed_claim_ids` is the source of truth.
- `types.ts`'s OpKind has `sign` added ahead of time (decided by the main session, not yet merged into the schema); registered in `check_fixtures.py`'s PENDING, to be removed once the schema adds it.

## Recheck log (after switching to the new node style)

- Steps 1–17 rerun under the new style, all pass; this time step 10's deadline change was also verified (typed key by key), and after signing the deadline in the proposal is 2027-02-28.
- Added step 18 (BLOCKED) and step 19 (abstain), passed. Screenshots: `screenshots/b2-blocked.jpg`, `screenshots/c4-abstain.jpg`.
- Under MOCK, every Analyze reloads a clean fixture, so data changed by signing doesn't carry over to the next run.
- Short titles: `types.ts`'s Claim gets an optional `label`. The node card shows label if there is one, otherwise it truncates statement to 10 characters plus "…" (`nodeLabel` in `src/node/labels.ts`). The current fixture has no label, so the app shows truncated sentences; the short titles in `screenshots/b1-workspace.jpg`, `b3-scenario.jpg` come from the playground's demo table; update the screenshots after the backend adds label and the fixture is regenerated. The playground still uses the demo table (`src/playground/demoLabels.ts`), preferring label when present.

## Catching up with core-schema@eb92f73 (label / neutral / critic)

- `git merge core-schema` is a fast-forward (core-schema already contains all of frontend's commits).
- `types.ts`: `Claim.label: string | null`; `Stance` adds `neutral`; `TradeProposal.critic` (`CRITIC_STATUSES` = disabled / ok / failed). `check_fixtures.py` removes OpKind's PENDING (the schema now has `sign`) and checks critic's values.
- The evidence panel gets an extra group "背景" ("background") (neutral); on the ring, neutral is a gray segment, counting as neither pro nor contra; the card's small text says "背景 n". The C1 data has no neutral evidence, so it's verified with a unit test (copy the graph, change one reference to neutral).
- The proposal card gets a line "Critic 挑刺：未启用（下一期）" ("Critic nitpicks: not enabled (next phase)"); when failed shows the reason, when ok lists the items.
- Regenerated 3 fixtures, all pass `check_fixtures.py` (14 enums). The golden C1 graph's labels are all null, so node cards still show truncated statements.

## Multi-scenario playground (/#scenarios)

- Data: `make_fixtures.py` adds `c1_multi.json`, all through real `ep.fork`: c1-v2 = change assumption (integrated laser), c1-v3 = predefined shock (foundry shutdown), c1-v4 = the same shock stacked on c1-v2. `DemoReasoner` changed to look only at the "操作：" ("operation:") line to determine the operation type (when stacking, the baseline graph's own op misleads ScriptedReasoner).
- Five design questions, two approaches each: scenario list (segmented pills / version tree), comparison (overlay coloring / side by side), stacked coloring (relative to the previous layer / relative to baseline), scenario summary (big-number cards / dial dot matrix), new scenario (Dynamic Island / side form). Screenshots `screenshots/sc1–sc5`.
- Scenario names come from a demo table; "相对基线" ("relative to baseline") is demoed by the frontend combining each layer's backend results; the real version needs the backend to provide it.
- Backend issue found: the stacked fork (c1-v4)'s proposal `support_status` reverts to supported — `derive_proposal` only looks at this layer's challenged, and the fact that the parent scenario c1-v2 made the laser path challenged isn't carried down.
- Caught up with the stacked-scenario fix (core-schema@bb173e1, fast-forward): the backend's assessment and `scenario_ref.challenged_claim_ids` are now the full stacked results, Scenario gains `root_version`, and ops also inherit from the parent scenario. Frontend changed to: "相对基线" uses `scenario_ref.challenged_claim_ids` directly; "这一层新增" ("new in this layer") = this version's challenged minus the parent version's challenged (set difference), with a test confirming these nodes are all in the backend diff's `changed_claim_ids`; "这一层改动的假设" ("assumption changed in this layer") only looks at the op newly added in this layer. Most views in the multi-scenario playground default to relative to baseline, group 3 A shows new in this layer, and the numbers on the tree are also new in this layer.
