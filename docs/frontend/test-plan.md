# Frontend MVP test plan

2026-10-18 · frontend branch

## Automated

All run under `web/` (the Python part from the repo root):

```bash
npm run typecheck && npm test && npm run build
~/Downloads/multiverse-investor-agent/.venv/bin/python web/scripts/check_fixtures.py
```

### 1. `toFlow` pure function (`src/__tests__/toFlow.test.ts`)

Inputs use real versions from `fixtures/c1.json`; no separately made-up graphs.

| Case | Expected |
| --- | --- |
| Node count / edge count for c1-v1 | 10 / 9, ids correspond one-to-one with the graph |
| Depth coordinates | `c1.event`, `c1.assume.capex`, `c1.assume.external_laser` depth 0; `c1.cpo_ramp` 1; `c1.laser_demand`, `c1.siph_foundry`, `c1.pluggable_dsp` 2 (laser_demand takes the longest path, not 1); the three terminals 3. Same depth has the same y, x values don't overlap |
| Edge `from` alias | The React Flow edge's `source` = `from` in the schema |
| model_only | data.modelOnly = true (dashed) for `c1.e6`, `c1.e9`; false for the rest |
| key dependency | When the v1 proposal is passed in, only `c1.assume.external_laser` has data.isKey = true; the `key_dependency.condition_id` form also resolves to the condition's claim_id (hand-make a proposal that contains only condition_id) |
| assessment | When c1-v2's scenario is passed in, `c1.laser_demand`, `c1.term.laser_vendor` are challenged and the rest unaffected; when not passed, data.assessment is undefined |
| Changed assumption | When v2 is passed in, `c1.assume.external_laser` has data.isChangedTarget = true |
| Immutability | `JSON.stringify(graph)` is the same before and after the call (input not mutated) |
| Cycles / dangling edges | Hand-make an edge pointing to a nonexistent node: no crash, the edge is ignored and counted in the return value's `warnings` |

### 2. status mapping (`src/__tests__/status.test.ts`)

- Every value of every enum (Role, EvidenceStatus, AssessmentStatus, Gate, ProposalStatus, SupportStatus, VerificationStatus, EvaluationStatus, ExitLogic) has a label and a color: assert one by one using the value arrays in `types.ts`; missing one fails. Check the enum value arrays against schema.py's Literals once (see the script in section 3).
- The set of `gate` labels contains no "execute" / "执行" wording.
- `status` and `gate` map to two different badge component keys (to prevent them being merged into one).
- `exit_logic` ANY → "或" ("or"), ALL → "且" ("and").

### 3. Fixture conforms to the schema (`web/scripts/check_fixtures.py`)

For each version in `fixtures/c1.json`:

- `parse_graph(graph)` succeeds, and `validator.blocking(validate_graph(g))` is empty;
- `TradeProposal.model_validate(proposal)` succeeds, `proposal.graph_version == graph.version`;
- When there's a `scenario`, `Scenario.model_validate` succeeds, `scenario.version == graph.version`, and `base_version` is in `versions`;
- When there's a `diff`, recompute it with `catalyst.diff.diff(base, graph)` and the result matches the file (to catch hand edits to the fixture);
- Every entry in `excerpts` passes `Excerpt.model_validate`, and every excerpt_id referenced in the graph can be found in that version's excerpts;
- Canonical form: for every object `X.model_validate(d).dump() == d` (all fields present, including defaults);
- Additionally print the enum values `types.ts` needs (read from the schema's Literals) and compare with the arrays in `src/types.ts`; exit code non-zero on mismatch.

Run `make_fixtures.py` again; `git diff --exit-code web/fixtures/c1.json` should be empty (generation is deterministic).

### 4. TypeScript and build

- `npm run typecheck` (`tsc --noEmit`, strict) has no errors;
- `npm run build` succeeds; the output should not contain the fixture unless `VITE_MOCK=1` (just check whether `dist/assets` has a chunk named `c1.json`; not enforced).

### Automation not done

Component render tests, end-to-end browser tests: not done within the 55-minute budget; covered by the manual script below.

## Manual demo script (B1 → B2 → B3)

Setup: `cd web && npm run dev`, open http://localhost:5173 . The top right should have the "MOCK · fixture c1" badge (absent with the real backend).

### B1 Research Workspace

| # | Action | Expected to see |
| --- | --- | --- |
| 1 | The input box contains "光子芯片采用快于预期" ("photonic chip adoption faster than expected"), click Analyze | The canvas shows 10 nodes and 9 edges in four rows top to bottom: event + two assumptions / CPO shipments / three intermediate nodes / three terminals (LITE, TSM, MRVL). Small text at the top `c1-v1` |
| 2 | Look at the canvas | Event blue, assumptions and intermediate nodes green, terminals purple; `c1.e6`, `c1.e9` are dashed (model inference only); "主流 CPO 方案采用外置 CW 激光光源" ("mainstream CPO designs use an external CW laser source") has an outer glow and Check first |
| 3 | Click "外置 CW 激光光源需求随 CPO 端口数上升" ("demand for external CW laser sources rises with CPO port count") | Right-hand panel: details (statement, evidence_status = supported, mechanisms of the two incoming edges); evidence Supporting 2 (sc-003, sc-004, with source, date, original text) / Contradicting 1 (sc-005, rebuttal shown below); one condition `cond.c1.els_design_wins`: verifiable and unknown as two separate badges |
| 4 | Click "CPO 交换机……提前到 2027 年下半年" ("CPO switches ... pulled forward to 2H 2027") | Condition `cond.c1.cpo_shipments` threshold shows "你来定" ("you decide") and threshold_note; unverified, unknown |
| 5 | Click "可插拔 DSP 供应商相关业务增速承压" ("growth of pluggable DSP vendors' related business under pressure") | Evidence area shows "仅模型推断" ("model inference only"), no empty cards |
| 6 | Click "光子芯片……采用快于预期" ("photonic chip ... adoption faster than expected") (the event) | Evidence area shows "这个节点没有入边" ("this node has no incoming edges"); evidence_status is still the backend's supported (known issue 1) |

### B2 Sign-off

| # | Action | Expected to see |
| --- | --- | --- |
| 7 | Switch to Sign-off | Several rows in the assumption table, each row: statement, invalidation condition (rule + deadline), evidence status, Confirm; at the top "0 / n confirmed" |
| 8 | Check Confirm on two rows | The count becomes 2 / n; the evidence status column doesn't change |
| 9 | Look at the proposal card | LITE long; the two entry conditions joined by "且" ("and"); one exit condition, marked "ANY · 或" ("ANY · or"); two separate badges: status = draft, gate = WAIT (先别动 "hold off"); support_status; key dependency points to the external light source assumption with its why. No execute button of any kind |
| 10 | Fill a threshold on `cond.c1.cpo_shipments` (e.g. 100000), change one deadline | "已修改，签字后由后端重算" ("modified, will be recomputed by the backend after signing") appears next to the condition; gate is still WAIT |
| 11 | Click Sign | Three fields pop up: testable judgment (prefilled clarified_statement, original wording shown beside it), criteria (prefilled criteria, may be empty), deadline (prefilled deadline); small text under the button "签的是研究判断，不是下单" ("you are signing a research judgment, not placing an order") |
| 12 | Submit | The proposal card shows "已签" ("signed"), confirmed_claim_ids = the two checked in step 8; under MOCK there's an extra line "MOCK：gate 未重算" ("MOCK: gate not recomputed") |

### B3 Scenario Diff

| # | Action | Expected to see |
| --- | --- | --- |
| 13 | Switch to Scenario, pick "主流 CPO 方案采用外置 CW 激光光源" ("mainstream CPO designs use an external CW laser source") in the dropdown, enter the new value "主流 CPO 方案改用集成激光，不再需要外置光源" ("mainstream CPO designs switch to integrated lasers and no longer need an external light source"), click Fork | Scenario version `c1-v2` appears; the toggle shows "基线 c1-v1 / 情景 c1-v2" ("baseline c1-v1 / scenario c1-v2") and "假设，未观测" ("hypothetical, not observed") |
| 14 | Look at the scenario canvas | "外置 CW 激光光源需求" ("external CW laser source demand") and "激光器供应商……营收超预期" ("laser vendor ... revenue beats expectations") have an orange border and orange dot (challenged); the other 8 have gray background with check; the changed assumption has the "改动的假设" ("changed assumption") corner tag; evidence_status still shown on nodes |
| 15 | Look at the three right-hand blocks | ① Challenged premises: two items + their reasons; ② What to check next: "主要厂商 2027 年量产 CPO 是否确实采用集成激光（正式披露）……" ("whether major vendors' 2027 volume-production CPO actually uses integrated lasers (official disclosure) ..."); ③ Proposal v1 → v2: gate WAIT → WAIT, status draft → draft, support_status supported → challenged, traced to `c1.assume.external_laser` (changed_claim_ids three items) |
| 16 | Switch back to "基线" ("baseline") | The canvas returns to the uncolored v1; the three right-hand blocks are hidden or grayed out |
| 17 | Pick another node (e.g. the capex assumption) and Fork again | Under MOCK shows a backend-style rejection: "MOCK：fixture 只录了 c1.assume.external_laser 的 change_assumption" ("MOCK: the fixture only recorded change_assumption for c1.assume.external_laser"); the original scenario is unaffected |

### Real backend (rerun after the backend lands)

`VITE_MOCK=0 npm run dev`, rerun 1–17. Differences should appear only in: no MOCK badge; in step 12 gate is recomputed by the backend (with the threshold changed and observations empty it should still be WAIT); step 17 goes through a real fork.

### Additional cases (data selector in the MOCK header)

| # | Action | Expected to see |
| --- | --- | --- |
| 18 | Select "C1 到期复查（BLOCKED）" ("C1 due-date recheck (BLOCKED)"), Analyze, switch to Sign-off | Proposal card gate = red "BLOCKED · 受阻" ("BLOCKED · blocked"), status still draft; `cond.c1.els_design_wins` is red "未满足" ("not met"), `cond.c1.cpo_shipments` is still "未知" ("unknown") |
| 19 | Select "C4 弃权（没有因果链）" ("C4 abstain (no causal chain)"), Analyze | No canvas; shows "没有找到有依据的因果链" ("no grounded causal chain found") and the reason the backend gave; none of the three tabs are clickable |

Data sources: `make_fixtures.py` generates `c1_blocked.json` (today=2027-04-15, plus a fabricated observation that "covers the whole window but has no records"; not_met and BLOCKED are determined by code) and `c4_abstain.json` (real `ep.discover` entrypoint + ScriptedReasoner abstaining). Not covered: D1 Hormuz (no golden graph, and ScriptedReasoner has no inspect, so it has to wait for a real recording), READY_FOR_REVIEW (C1's shipment threshold is null, so the code won't judge it met), AddShock (UI was cut).
