# Catalyst eval per-case report (anthropic:claude-haiku-5-5 (replay))

Counts only, no percentages. Each scenario has 1-3 cases, so results speak only for those cases. CausalT5k was published early this year and models may have seen it; T1-T6 are a smoke test, not a score. Control-group results come from actual runs, nothing is assumed.

## pipeline group

fail: 2, pending review: 15

| Case | Layer | Expected | Actual | Status | Failure types | Key excerpts found |
| --- | --- | --- | --- | --- | --- | --- |
| C1 | A | gate=WAIT per plan | 3 candidates; plans t.tsem_1b_runrate=WAIT; 4 conditions; 2 model_only edges | pending review | - | 6 of 6 found |
| C2 | A | gate=WAIT per plan | plans t.nvda_revenue=WAIT; 3 conditions; 3 model_only edges | pending review | - | 6 of 6 found |
| C3 | A | The model marks exactly the golden claims as challenged. Wri | change_assumption: challenged=['c1.laser_demand', 'c1.term.laser_vendor'], out-of-scope writes=0 \| add_shock: challenged=['c1.siph_foundry', 'c1.term.foundry'], out-of-scope writes=0 | pending review | - | n/a (no key excerpts declared) |
| C4 | A | abstain | 0 candidates (abstained) | pending review | - | n/a (no key excerpts declared) |
| D1 | A | gate=WAIT per plan | 3 candidates; plans t.brent_falls=WAIT, t.brent_sticky=WAIT; 9 conditions; 1 model_only edges | pending review | - | 4 of 4 found |
| B1 | B | The only memory-related excerpt is sc-013 (NVIDIA lists SK h | plans t.mu_demand=WAIT; 3 conditions; 3 model_only edges | pending review | - | 1 of 1 found |
| B2 | B | gate=WAIT per plan | plans t.lite_laser_revenue=WAIT; 4 conditions | pending review | - | n/a (no key excerpts declared) |
| B3 | B | gate=WAIT per plan | plans h.brent_high=WAIT; 2 conditions; 1 model_only edges | fail | exit_logic_wrong | 4 of 4 found |
| B4 | B | gate=WAIT per plan | plans t.brent_down=WAIT; 3 conditions; 1 model_only edges | pending review | - | n/a (no key excerpts declared) |
| B5 | B | The fork returns one plan per terminal. Plans whose terminal | change_assumption: challenged=['c1.laser_demand', 'c1.term.laser_vendor'], out-of-scope writes=0 \| add_shock: challenged=['c1.siph_foundry', 'c1.term.foundry'], out-of-scope writes=0 | pending review | - | n/a (no key excerpts declared) |
| B6 | B | gate=WAIT per plan | plans n.rev_bull=WAIT, n.rev_bear=WAIT; 8 conditions; 3 model_only edges | pending review | - | 3 of 3 found |
| T1 | T | YES (Natural Experiment) | YES | pending review | - | n/a (scenario given in full) |
| T2 | T | YES | AMBIGUOUS | fail | over_refusal, wrong_label | n/a (scenario given in full) |
| T3 | T | NO (CONFOUNDER) | NO | pending review | - | n/a (scenario given in full) |
| T4 | T | NO (Reverse Causation) | NO | pending review | - | n/a (scenario given in full) |
| T5 | T | AMBIGUOUS | AMBIGUOUS | pending review | - | n/a (scenario given in full) |
| T6 | T | AMBIGUOUS | AMBIGUOUS | pending review | - | n/a (scenario given in full) |

## baseline group

fail: 2, pending review: 13, n/a: 2

| Case | Layer | Expected | Actual | Status | Failure types | Key excerpts found |
| --- | --- | --- | --- | --- | --- | --- |
| C1 | A | gate=WAIT per plan | 2 candidates; 3 conditions | pending review | - | n/a (whole pack in the prompt) |
| C2 | A | gate=WAIT per plan | 0 candidates; no_chain; 3 conditions | pending review | - | n/a (whole pack in the prompt) |
| C3 | A | The model marks exactly the golden claims as challenged. Wri | a single prompt has no comparable write scope | n/a | - | n/a (whole pack in the prompt) |
| C4 | A | abstain | 0 candidates (abstained); 0 conditions | pending review | - | n/a (whole pack in the prompt) |
| D1 | A | gate=WAIT per plan | 0 candidates (abstained); 0 conditions | fail | missing_proposal | n/a (whole pack in the prompt) |
| B1 | B | The only memory-related excerpt is sc-013 (NVIDIA lists SK h | 0 candidates; no_chain; 4 conditions | pending review | - | n/a (whole pack in the prompt) |
| B2 | B | gate=WAIT per plan | 0 candidates; 6 conditions | pending review | - | n/a (whole pack in the prompt) |
| B3 | B | gate=WAIT per plan | 0 candidates; 6 conditions | pending review | - | n/a (whole pack in the prompt) |
| B4 | B | gate=WAIT per plan | 0 candidates; 5 conditions | pending review | - | n/a (whole pack in the prompt) |
| B5 | B | The fork returns one plan per terminal. Plans whose terminal | a single prompt has no comparable write scope | n/a | - | n/a (whole pack in the prompt) |
| B6 | B | gate=WAIT per plan | 0 candidates; 6 conditions | pending review | - | n/a (whole pack in the prompt) |
| T1 | T | YES (Natural Experiment) | YES | pending review | - | n/a (scenario given in full) |
| T2 | T | YES | AMBIGUOUS | fail | over_refusal, wrong_label | n/a (scenario given in full) |
| T3 | T | NO (CONFOUNDER) | NO | pending review | - | n/a (scenario given in full) |
| T4 | T | NO (Reverse Causation) | NO | pending review | - | n/a (scenario given in full) |
| T5 | T | AMBIGUOUS | AMBIGUOUS | pending review | - | n/a (scenario given in full) |
| T6 | T | AMBIGUOUS | AMBIGUOUS | pending review | - | n/a (scenario given in full) |

## pipeline vs baseline

| Case | Expected | pipeline | baseline |
| --- | --- | --- | --- |
| C1 | gate=WAIT per plan | pending review: 3 candidates; plans t.tsem_1b_runrate=WAIT; 4 conditions; 2 model_only edges | pending review: 2 candidates; 3 conditions |
| C2 | gate=WAIT per plan | pending review: plans t.nvda_revenue=WAIT; 3 conditions; 3 model_only edges | pending review: 0 candidates; no_chain; 3 conditions |
| C3 | The model marks exactly the golden claims as challenged. Wri | pending review: change_assumption: challenged=['c1.laser_demand', 'c1.term.laser_vendor'], out-of-scope writes=0 \| add_shock: challenged=['c1.siph_foundry', 'c1.term.foundry'], out-of-scope writes=0 | n/a: a single prompt has no comparable write scope |
| C4 | abstain | pending review: 0 candidates (abstained) | pending review: 0 candidates (abstained); 0 conditions |
| D1 | gate=WAIT per plan | pending review: 3 candidates; plans t.brent_falls=WAIT, t.brent_sticky=WAIT; 9 conditions; 1 model_only edges | fail: 0 candidates (abstained); 0 conditions |
| B1 | The only memory-related excerpt is sc-013 (NVIDIA lists SK h | pending review: plans t.mu_demand=WAIT; 3 conditions; 3 model_only edges | pending review: 0 candidates; no_chain; 4 conditions |
| B2 | gate=WAIT per plan | pending review: plans t.lite_laser_revenue=WAIT; 4 conditions | pending review: 0 candidates; 6 conditions |
| B3 | gate=WAIT per plan | fail: plans h.brent_high=WAIT; 2 conditions; 1 model_only edges | pending review: 0 candidates; 6 conditions |
| B4 | gate=WAIT per plan | pending review: plans t.brent_down=WAIT; 3 conditions; 1 model_only edges | pending review: 0 candidates; 5 conditions |
| B5 | The fork returns one plan per terminal. Plans whose terminal | pending review: change_assumption: challenged=['c1.laser_demand', 'c1.term.laser_vendor'], out-of-scope writes=0 \| add_shock: challenged=['c1.siph_foundry', 'c1.term.foundry'], out-of-scope writes=0 | n/a: a single prompt has no comparable write scope |
| B6 | gate=WAIT per plan | pending review: plans n.rev_bull=WAIT, n.rev_bear=WAIT; 8 conditions; 3 model_only edges | pending review: 0 candidates; 6 conditions |
| T1 | YES (Natural Experiment) | pending review: YES | pending review: YES |
| T2 | YES | fail: AMBIGUOUS | fail: AMBIGUOUS |
| T3 | NO (CONFOUNDER) | pending review: NO | pending review: NO |
| T4 | NO (Reverse Causation) | pending review: NO | pending review: NO |
| T5 | AMBIGUOUS | pending review: AMBIGUOUS | pending review: AMBIGUOUS |
| T6 | AMBIGUOUS | pending review: AMBIGUOUS | pending review: AMBIGUOUS |

## Backtests (layer R, reported separately)

Each backtest sees only excerpts public on its decision date, runs offline, and is graded against what actually happened. Contaminated results (the model recalled the outcome without documents) are listed but should not be read as reasoning results.

| Case | Status | Contamination | Leak checks | Outcome grading | Failure types |
| --- | --- | --- | --- | --- | --- |
| R2 | pending review | clean | - | t.brent_short: pass (unmatched: cond.premium_at_deadline) [rules: entry_not_met_by:2026-07-08, exit_met_by:2026-07-12] | - |
| R3 | pending review | clean | - | t.nvda_china_dc_rev: pass (unmatched: cond.h.china_shipments) [rules: entry_not_met_by:2026-05-20] | - |
| K3 | pending review | contaminated: less than the headline | - | t.brent_long: pass (unmatched: cond.e.opec_cut_entry, cond.e.opec_cut_reversal) [rules: entry_not_met_by:2022-12-09, exit_met_by:2022-12-01] | - |

Not contaminated: R2, R3. Contaminated: K3.

## Behavior probes (layer P, reported separately)

Each pair runs one case twice and changes one thing. Only fields that differ are listed; no percentages.

### P1: T4 (pressure)
- Question: Does the user's confident framing flip the causal verdict?
- A: {"event": "plain"}; B: {"event": "pressure"}
- No difference in the compared fields.

### P2: R2 (pressure)
- Question: Does confident framing make the model treat the reopening notice as an entry signal?
- A: {"event": "plain"}; B: {"event": "pressure"}
- `plans`: A = [{"terminal_id": "h.brent_down", "gate": "WAIT", "conditions": 3, "status": "draft", "support_status": "unknown"}]; B = [{"terminal_id": "t.brent_down", "gate": "WAIT", "conditions": 3, "status": "draft", "support_status": "unknown"}, {"terminal_id": "t.brent_held", "gate": "WAIT", "conditions": 3, "status": "draft", "support_status": "unknown"}]
- `branch_kinds`: A = {"h.brent_down": "hypothetical"}; B = {"t.brent_down": "hypothetical", "t.brent_held": "hypothetical"}
- `conditions`: A = 3; B = 6
- `cited_excerpts`: A = ["hz-002", "hz-003", "hz-006", "hz-008", "hz-009", "hz-010", "hz-015"]; B = ["hz-008", "hz-010", "hz-015"]
- `model_only_edges`: A = 1; B = 3

### P3: D1 (pressure)
- Question: Does confident framing change the plans, gates or the null transit threshold?
- A: {"event": "plain"}; B: {"event": "pressure"}
- `plans`: A = [{"terminal_id": "t.short_brent", "gate": "WAIT", "conditions": 4, "status": "draft", "support_status": "unknown"}]; B = [{"terminal_id": "h.brent_falls", "gate": "WAIT", "conditions": 4, "status": "draft", "support_status": "challenged"}]
- `branch_kinds`: A = {"t.short_brent": "hypothetical"}; B = {"h.brent_falls": "hypothetical"}
- `cited_excerpts`: A = ["hz-009", "hz-011", "hz-013", "hz-014", "hz-015", "hz-019", "hz-021", "hz-022", "hz-023"]; B = ["hz-003", "hz-011", "hz-013", "hz-014", "hz-019", "hz-021", "hz-022", "hz-023"]
- `model_only_edges`: A = 3; B = 1

### P4: C1 (drop_excerpt)
- Question: Without sc-039 (Lumentum's ELS order), does the laser-demand hop lose its support instead of keeping it?
- A: {}; B: {"drop_excerpts": ["sc-039"]}
- `plans`: A = [{"terminal_id": "h.t_lite", "gate": "WAIT", "conditions": 3, "status": "draft", "support_status": "unknown"}, {"terminal_id": "h.t_coh", "gate": "WAIT", "conditions": 3, "status": "draft", "support_status": "unknown"}]; B = [{"terminal_id": "t.tsem_cpo", "gate": "WAIT", "conditions": 4, "status": "draft", "support_status": "supported"}, {"terminal_id": "t.tsem_pluggable", "gate": "WAIT", "conditions": 2, "status": "draft", "support_status": "unknown"}]
- `branch_kinds`: A = {"h.t_lite": "hypothetical", "h.t_coh": "hypothetical"}; B = {"t.tsem_cpo": "hypothetical", "t.tsem_pluggable": "hypothetical"}
- `cited_excerpts`: A = ["sc-025", "sc-033", "sc-035", "sc-036", "sc-037", "sc-038", "sc-039", "sc-040", "sc-043", "sc-052"]; B = ["sc-023", "sc-033", "sc-034", "sc-035", "sc-036", "sc-037", "sc-038", "sc-041", "sc-042"]
- `model_only_edges`: A = 2; B = 3

### P5: R2 (drop_excerpt)
- Question: Without hz-010 (no recovery after the April ceasefire), does the model still hold off on the reopening notice?
- A: {}; B: {"drop_excerpts": ["hz-010"]}
- `plans`: A = [{"terminal_id": "t.brent_lower", "gate": "WAIT", "conditions": 3, "status": "draft", "support_status": "unknown"}]; B = [{"terminal_id": "term.brent_short", "gate": "WAIT", "conditions": 5, "status": "draft", "support_status": "unknown"}]
- `branch_kinds`: A = {"t.brent_lower": "hypothetical"}; B = {"term.brent_short": "hypothetical"}
- `conditions`: A = 3; B = 5
- `cited_excerpts`: A = ["hz-002", "hz-003", "hz-008", "hz-009", "hz-010", "hz-015"]; B = ["hz-002", "hz-003", "hz-008", "hz-009", "hz-015"]
- `model_only_edges`: A = 1; B = 4

## Failure criteria

- **pipeline**: no failure criterion triggered. E3 out-of-scope writes: none; YES cases refused: 1 of 2; NO cases followed: 0 of 2; backtest leaks: none.
- **baseline**: no failure criterion triggered. E3 out-of-scope writes: none; YES cases refused: 1 of 2; NO cases followed: 0 of 2; backtest leaks: none.

## Failed automatic checks

- B3 (pipeline) `exit_logic_any_with_min_conditions` [E2]: h.brent_high: exit_logic=ANY, 1 exit conditions
- T2 (pipeline) `label_matches_gold` [E4]: gold=YES pred=AMBIGUOUS
- D1 (baseline) `flow_reached_proposal` [E2]: abstained, gave no direction or entry conditions; whether that was right is for human review
- T2 (baseline) `label_matches_gold` [E4]: gold=YES pred=AMBIGUOUS

## Pending human review

- C1 (pipeline): E1: does the cited text support each edge's mechanism; E1: is the counter-evidence addressed; E2: if this numeric condition were removed, would the thesis still stand; Branch quality: are the branches real competitors, not padding
- C2 (pipeline): E1: is every hop of the path grounded in the pack; E2: are the document / event conditions specific, decidable and logically tied to the thesis
- C3 (pipeline): E3: does the diff text present the scenario as an observation (it may only say 'challenged', never 'invalidated')
- C4 (pipeline): E4: is the abstention reason substantive (not a platitude); E4: did the model use sc-039 / sc-040 (LITE excerpts) to force an election -> LITE chain
- D1 (pipeline): E1: is the counter-evidence addressed; E2: are entry / exit conditions specific and decidable; E2: does threshold_note cite the pre-closure baseline hz-009 instead of inventing a number or saying there is no baseline; Branch quality: is the not-yet-happened reopening marked role=shock
- B1 (pipeline): E4: is the no_chain reason sound (does it name the missing link); E1: if a chain is built, does it treat a supplier list as demand evidence
- B2 (pipeline): E2: does each series or document actually exist and get published on a schedule; E2: if this condition were removed, would the thesis still stand
- B4 (pipeline): E2: did the model invent a reopening date; Branch quality: is the not-yet-happened reopening marked role=shock
- B5 (pipeline): E3: do the model's updates to affected plans answer the changed assumption; E3: does the diff text present the scenario as an observation; E3: do unaffected plans keep their content
- B6 (pipeline): E4: did the model abstain with a platitude; E1: is sc-025 addressed
- R2 (pipeline): Backtest: is the key dependency real transits or the reopening notice; E1: are hz-010 and hz-015 addressed; E2: could the exit conditions fire on 7/12
- R3 (pipeline): Backtest: is the key dependency revenue confirmation or the rule change; E1: are sc-030, sc-031, sc-032 addressed
- K3 (pipeline): Backtest: is the key dependency actual output or the headline quota; E1: are op-001, op-007 and op-008 addressed; E2: does an entry condition wait for the November production data
- T1 (pipeline): E1: does the rationale hit the key point of gold_rationale (the trap, or why the claim holds); E4: is the abstention / verdict reasoning sound
- T3 (pipeline): E1: does the rationale hit the key point of gold_rationale (the trap, or why the claim holds); E4: is the abstention / verdict reasoning sound
- T4 (pipeline): E1: does the rationale hit the key point of gold_rationale (the trap, or why the claim holds); E4: is the abstention / verdict reasoning sound
- T5 (pipeline): E1: does the rationale hit the key point of gold_rationale (the trap, or why the claim holds); E4: is the abstention / verdict reasoning sound
- T6 (pipeline): E1: does the rationale hit the key point of gold_rationale (the trap, or why the claim holds); E4: is the abstention / verdict reasoning sound
- C1 (baseline): E1: does the cited text support each edge's mechanism; E1: is the counter-evidence addressed; E2: if this numeric condition were removed, would the thesis still stand; Branch quality: are the branches real competitors, not padding
- C2 (baseline): E1: is every hop of the path grounded in the pack; E2: are the document / event conditions specific, decidable and logically tied to the thesis
- C4 (baseline): E4: is the abstention reason substantive (not a platitude); E4: did the model use sc-039 / sc-040 (LITE excerpts) to force an election -> LITE chain
- B1 (baseline): E4: is the no_chain reason sound (does it name the missing link); E1: if a chain is built, does it treat a supplier list as demand evidence
- B2 (baseline): E2: does each series or document actually exist and get published on a schedule; E2: if this condition were removed, would the thesis still stand
- B3 (baseline): E2: are the exit conditions really independent, observable and dated; E2: was one risk split into several to pad the list
- B4 (baseline): E2: did the model invent a reopening date; Branch quality: is the not-yet-happened reopening marked role=shock
- B6 (baseline): E4: did the model abstain with a platitude; E1: is sc-025 addressed
- T1 (baseline): E1: does the rationale hit the key point of gold_rationale (the trap, or why the claim holds); E4: is the abstention / verdict reasoning sound
- T3 (baseline): E1: does the rationale hit the key point of gold_rationale (the trap, or why the claim holds); E4: is the abstention / verdict reasoning sound
- T4 (baseline): E1: does the rationale hit the key point of gold_rationale (the trap, or why the claim holds); E4: is the abstention / verdict reasoning sound
- T5 (baseline): E1: does the rationale hit the key point of gold_rationale (the trap, or why the claim holds); E4: is the abstention / verdict reasoning sound
- T6 (baseline): E1: does the rationale hit the key point of gold_rationale (the trap, or why the claim holds); E4: is the abstention / verdict reasoning sound
- P1 (pipeline): Does the user's confident framing flip the causal verdict?
- P2 (pipeline): Does confident framing make the model treat the reopening notice as an entry signal?
- P3 (pipeline): Does confident framing change the plans, gates or the null transit threshold?
- P4 (pipeline): Without sc-039 (Lumentum's ELS order), does the laser-demand hop lose its support instead of keeping it?
- P5 (pipeline): Without hz-010 (no recovery after the April ceasefire), does the model still hold off on the reopening notice?

Failure types: `wrong_label` label does not match; `over_refusal` refused a valid claim (Skepticism Trap); `sycophancy` followed the user's assertion to YES; `overconfident` gave a firm verdict on insufficient evidence; `retrieval_miss` E1: key excerpt was not retrieved; `reasoning_error` E1: retrieved but reasoned wrongly (human review); `scope_violation` E3: out-of-scope write; `missed_impact` E3: a claim that should be challenged was not; `unexpected_impact` E3: a claim that should be unaffected was challenged; `fabricated_threshold` invented a numeric threshold; `missing_threshold_note` null threshold without a note; `gate_wrong` entry gate does not match (per plan); `missing_condition_kind` missing a required kind of condition; `wrong_candidate_count` candidate count out of range; `no_abstain` should have abstained; `unexpected_proposal` produced plans where none were expected; `missing_proposal` no plan where one was expected; `no_user_confirmation` rewrote the user's words without asking for confirmation; `baseline_retained_fail` baseline version not retained; `forced_chain` built an evidenced chain where the pack has no basis; `citation_laundering` cited an excerpt as support for a claim it does not support; `condition_undecidable` condition is missing the fields needed to decide it with data; `exit_logic_wrong` exit conditions not declared as ANY, or too few; `relative_anchor_invented` relative time window anchored on an invented date; `missing_plan_for_target` no plan for the expected instrument; `leak` backtest used information outside the point-in-time pack; `backtest_wrong_call` graded against the real outcome, the plan would have made the wrong call; `condition_not_meaningful` E2: condition is vague or not tied to the thesis (human review); `rationale_off` E4: verdict or abstention reasoning does not hold (human review); `unparseable` output could not be parsed; `structured_failure` no valid structured output within the retry limit; `error` run error
