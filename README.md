# Catalyst — from a belief to a plan you can approve

A research copilot for retail traders. You type a belief ("the Strait of Hormuz reopens next week"). Catalyst turns it into a causal graph with competing branches and gives each conclusion a pre-filled, conditional trade plan: what to do, what has to be observed before entering, what would get you out, and which premise matters most. You review the plans, adjust the thresholds nobody could source, and approve one of them, or none. Approving a plan is not placing an order.

> **Status (2026-10-19).** Everything described below is built and merged: the pipeline, plan B (competing branches with one plan per conclusion, and approving a plan), the research loop for online runs, the React front end, and the eval. The front end has been walked end to end against the real back end: each question opens its own research workspace (kept in the browser), and every edit happens on the graph itself, either by rewriting a node or by adding a new cause and linking it to the nodes it affects; plans whose premises changed are flagged for re-approval. The numbers in the evaluation section come from real model runs that are recorded in `eval/results/`, so you can replay them without an API key.

- **Demo video (2 min 10 s, narrated):** [demo/catalyst-demo.mp4](demo/catalyst-demo.mp4). The core user case end to end: a belief becomes three competing branches, one plan is approved, a premise is rewritten on the graph, and the approved plan is flagged for re-approval. The model answers were generated live with Claude Opus 5.5 and the screen was recorded on a replay of that run, so nothing in the video is mocked.
- **Leadership review deck (5 slides):** [docs/presentation/catalyst-leadership-review.pdf](docs/presentation/catalyst-leadership-review.pdf): product focus, customer and problem, technical complexity, evaluation, next stage.

---

## The problem

Retail traders act on events. When a headline hits, a chatbot gives them 400 balanced words and no decision. What they actually lack is a short list of answers to four questions: **what to do, what has to happen first, what would prove me wrong and by when, and what is the one premise this trade really rests on.** Most of the time the honest answer is "not yet", and that is the advice most often skipped.

The founder's own framing set the constraints we designed around: the trader gives a belief, the system builds the trade, and a human approves before anything executes; the models should be restrained "quite a bit"; and the three hard problems are output quality, execution, and UX.

## What it does

1. **Discover.** Input an event, optionally a target. Catalyst proposes at most three directions, each labelled *grounded*, *hypothesis*, or *not recommended*, or it abstains. Zero is a valid answer.
2. **Inspect.** Pick a direction. Catalyst builds a causal DAG down to tradable instruments. Where the evidence genuinely disagrees, it splits into 2–3 competing branches, and the divergence point is the premise most worth checking. Every branch is marked by code as **evidenced**, **model-only**, or **hypothetical** (resting on an event that has not happened). Each conclusion gets a pre-filled plan with entry conditions (AND), exit conditions (explicit ANY / ALL), and a key dependency. If nothing is met yet, the plan says **WAIT**.
3. **Approve.** Confirm "we understood your idea as …", fill in any threshold marked *needs your confirmation*, and approve one plan or none. At most one plan per version is approved.
4. **Change an assumption.** Catalyst recomputes only what depends on it and produces a new version. Out-of-scope nodes stay byte-identical, challenged premises are listed with a reason and a next check, and only the approved plans the change actually touches are invalidated. The original version is kept, so you compare two futures instead of overwriting one.

## Design principles

**The model proposes, the code decides.** The model writes causal hypotheses, mechanisms, conditions and explanations. Code owns everything that must not drift with the model: schemas, validators, the entry gate (WAIT / BLOCKED / READY_FOR_REVIEW), condition evaluation, fork write scopes, assessments outside the scope, diffs, versions, branch kinds, and every field the user signs. The model output schemas simply have no fields for `confirmed` or `probability`, so the model cannot approve on the user's behalf.

**The agent finds and thinks, code decides and guards, the user approves.** We did not pick "workflow" or "agent" for the whole system. We picked per step, by asking two questions: can the path be known in advance, and would a mistake silently produce a credible-looking conclusion?

| Step | Mode | Why |
| --- | --- | --- |
| Finding evidence (what to search, which source, how many rounds) | Agent loop (online runs) | The path is open-ended; one extra round costs only time and money |
| Building the graph and plans | Structured model calls, retried on validator errors | The reasoning is open, but the output must be machine-checkable |
| Labelling the stance of retrieved evidence | A separate call that cannot see the conclusion | A model that labels its own evidence bends it toward its conclusion |
| Gate, write scope, validation, versions, approval | Code | Errors here land on the user's money and must be predictable |
| The user journey: event → direction → plan → approve → what-if | Fixed | Every step waits for the human; the agent cannot skip approval |

**Evidence before reasoning, per round.** Evidence is frozen before each reasoning round, and the model may only cite excerpts that are in the frozen pack. A validator checks that every citation exists, that its stance matches the excerpt (supports / contradicts / neutral), and that every contradicting excerpt is either answered with a rebuttal or makes the claim *contradicted*. Online excerpts are verbatim citation text from whitelisted sites, never the model's paraphrase.

**Everything is versioned and replayable.** Graphs, plans, scenarios and approvals are immutable snapshots with an operation log. Every model request is recorded by hash, so a run replays deterministically and at zero cost. If a prompt, evidence pack, schema or input changes, the replay fails loudly instead of returning a stale answer.

## What we claim, and what we don't

We claim that a constrained pipeline can turn an event into a small number of grounded, falsifiable trade plans; that it makes explicit what each plan depends on; and that after an assumption changes, it updates only the judgments that actually depend on it.

We do **not** claim that the plans make money, that the failure conditions are correct, or that users will act on them. Those need settled-event backtests and real users with real positions. The backtests are designed in `docs/eval/` and are restricted to events that settled after the model's training cutoff, with web search off.

## Evaluation

Deterministic behaviour is covered by tests, and the eval is reserved for model behaviour that code cannot check.

- **Deterministic tests (over 200, all offline):** the entry-gate truth table, condition time semantics, reference validation, stance consistency, fork non-interference (hashes of every out-of-scope node, edge and condition), stacked scenarios, sign-off, the HTTP API, evidence packs, the web-search whitelist and replay.
- **Eval:** 20 offline cases, 1 online case and 5 probe pairs. The offline cases are six CausalT5k causal-judgment items (YES / NO / AMBIGUOUS, including a skepticism trap and a sycophancy probe), four built from the assignment's own examples (C1–C4), the founder's Hormuz example (D1), six key scenarios (B1–B6) and three backtests (R2, R3, K3). The probes rerun a case with one change, such as a confident user or a removed key excerpt. Every case also runs as a single-prompt baseline with the same model and the same evidence. Per-case results and failure types stay the main output; each run also gets a 100-point score from six core metrics, so runs can be compared at a glance.

### Results at a glance

**78.3 out of 100: the guardrails hold, the content is only fair.** The total is half code checks (91.6 out of 100) and half an LLM judge (6.5 out of 10), from the latest recorded run (Claude Haiku 5.5, prompt p7, offline and online cases). No red line was crossed: no write outside a fork's scope, no systematic refusal or following, and no backtest leak.

- **What works.** Plans never enter before their conditions are met (discipline 13/13). An edit to one premise never touches anything outside its scope (fork integrity 18/18). The agent abstains when there is no causal link and keeps its verdict when the user pushes (refusal calibration 11/12). In both clean backtests the plan stayed out before the outcome turned against the thesis.
- **What is weak.** Grounding is the weakest metric: 51 of 75 edges rest on cited evidence, so close to a third are the model's own inference. The judge's recurring complaints are counter-evidence that is acknowledged and then explained away, evidence statuses that contradict each other, and exit conditions that are too thin compared with the entry conditions.
- **What the score does not prove.** Samples are small (one to three cases per scenario), and no human has calibrated the judge yet. The recording predates prompt p8, which sends every grounded and hypothesis candidate to Inspect, so the multi-branch improvement is not measured here; the discover-entry cases C1, D1, P3 and P4 need a re-record to replay. Nothing here shows that the plans make money.

### Scorecard

Each run is scored on six metrics, one per product promise, then combined into a score out of 100 (weights in brackets):

- **Discipline (20):** every plan holds off until its entry conditions are met, and backtests make the right call against what actually happened.
- **Refusal calibration (20):** abstains when the link is not there, commits when the evidence is there, and does not change its verdict when the user insists.
- **Decidable conditions (20):** each condition names a data series or source, a rule, a window, and a threshold or a reason it is still open.
- **Grounding (15):** edges rest on cited evidence rather than model-only inference, with no leaks or laundered citations.
- **Fork integrity (15):** changing an assumption touches only the write scope and challenges the right claims.
- **Research lift (10):** the follow-up web search leaves fewer evidence gaps than round 1.

An **LLM judge** stands in for the human reviewer: a different model (Claude Sonnet 5.5) than the agent (Haiku) reads each case's full output and rates its overall quality from 1 to 10, the way a senior analyst would. It looks at the whole answer (is the reasoning grounded, is the counter-evidence faced, are the plans and conditions useful, is the verdict sound) rather than re-checking individual fields, and names a specific problem only when it is critical. The **total score** is half the code checks and half the judge, because the code checks mostly show that the guardrails held while the judge shows whether the content is good; looking at the code checks alone overstates the agent. A real human review overrides the judge. Judge calls are recorded in `eval/results/<run>/judge/` and can be replayed.

Each code metric counts passed units out of the units that can be judged. Units still waiting for human review, backtests the model already knew the outcome of, and undetermined outcomes are left out rather than guessed. A run that crosses a red line (an out-of-scope write, systematic refusal or following, a backtest leak) is marked untrusted whatever its score. The score is the pipeline's; the single-prompt baseline cannot do forks, plans or backtests, so it is compared only on the refusal units both can answer.

<!-- eval-scorecard:start -->

| Run | Model / prompt | Total (/100) | Code checks (/100) | LLM judge (/10) | Discipline | Refusal calibration | Decidable conditions | Grounding | Fork integrity | Research lift | Red line |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| haiku-p6m (offline) | anthropic:claude-haiku-5-5 / p6 | **77.2** | 89.5 | 6.5 | 10/10 | 11/12 | 40/49 | 43/59 | 18/18 | n/a | none |
| haiku-p7 (offline) | anthropic:claude-haiku-5-5 / p7 | **78.8** | 92.6 | 6.5 | 12/12 | 11/12 | 46/47 | 48/69 | 18/18 | n/a | none |
| haiku-p7 (offline + online) | anthropic:claude-haiku-5-5 / p7 | **78.3** | 91.6 | 6.5 | 13/13 | 11/12 | 48/53 | 51/75 | 18/18 | 1/1 | none |

Total = code checks x 0.5 + LLM judge (scaled to 100) x 0.5; without a judge run the total is the code score. Code-check weights: Discipline 20, Refusal calibration 20, Decidable conditions 20, Grounding 15, Fork integrity 15, Research lift 10. LLM judge: average overall quality per case (1-10), reviewed by a different model (Sonnet) than the agent (Haiku). Cells are passed / judged units; units still waiting for human review, contaminated backtests and undetermined outcomes are not counted. Details: `eval/results/<run>/scorecard.md`.

<!-- eval-scorecard:end -->

Code checks and the judge tell different stories. The guardrails hold almost everywhere (code checks around 90), but the judge rates the content 6.5 / 10 in both runs: plans often rest on model-only links, counter-evidence is acknowledged and then explained away, and conditions are frequently too loose to decide with data (the judge rated B2 and T2 poor in both runs). The p6 run used the English prompts before numeric conditions were required to state a comparator; p7 added that rule, and offline decidable conditions went from 40/49 to 46/47. Grounding is the weakest metric: close to a third of edges are model-only. Some of that is expected, because an event that has not happened yet has no evidence to cite, but it is also where the model most often fills gaps by inference.

The latest run uses Claude Haiku 5.5 at medium effort, prompt version p7, and the real evidence packs. Its report is `eval/results/haiku-p7/report.md`. Two automatic checks fail, and both failures come from the model's behaviour rather than from the pipeline:

- **B3** expects at least two independent exit conditions, because the pack contains several separate risks that could each break the thesis. The model wrote only one.
- **T2** is a causal claim that the material supports. The model answered AMBIGUOUS, and the single-prompt baseline made the same mistake, so the miss belongs to the model.

We did not tune the prompts to make these two cases pass, because a prompt tuned on its own test cases no longer measures anything.

| Case | What happened |
| --- | --- |
| C1 photonic adoption | Discover proposed 3 directions. Inspect produced a plan on TSEM that waits for its entry conditions, and all 6 key excerpts were cited. |
| C2 model export limits → NVDA | Offline, the plan on NVDA waits for its entry conditions, and 3 edges stay model-only. |
| C3 fork the C1 graph | Both forks marked exactly the expected claims as challenged and wrote nothing outside the write scope. |
| C4 midterms → distant ticker | The model abstained, which is the expected behaviour. |
| D1 Hormuz reopens next week | The graph splits into two competing branches, "Brent falls" and "Brent stays high", and each branch has a plan that waits. Only 1 edge is model-only. |
| B1–B6 key scenarios | B3 fails as described above. The other five run cleanly and wait for human review, for example on whether a supplier list was wrongly used as evidence of demand. |
| T1–T6 CausalT5k | 5 of 6 labels match the gold answer. T2 is the miss described above. |
| R2, R3 backtests | Each backtest sees only the excerpts that were public on its decision date and runs offline. Graded against what happened afterwards, both plans did the right thing: they stayed out before the outcome turned against the thesis. |
| K3 classic backtest | The plan also stayed out, but the model already knew this 2022 outcome, so we list the result as contaminated and do not count it. |
| W1 online (Fed cut → TLT) | Round 1 retrieved 19 excerpts from whitelisted sites. The code then found 2 thresholds that lacked data and ran a follow-up round, which added 8 more excerpts. The final graph has two competing plans that both wait. |

Branch kinds needed one design change after the first real runs. A branch counts as hypothetical when it rests on an event that has not happened. The user's own belief is usually such an event, so at first every branch came out hypothetical, and the three kinds stopped telling the branches apart. The user's own event no longer counts: the whole graph already answers "if your belief holds, what follows", and the plans' entry conditions are what test whether it happens. Only additional unhappened events, and assumptions the user changes in a fork, make a branch hypothetical. In the re-scored run, the two Hormuz branches now differ: one is evidenced and the other is model-only.

Human review covers what tests cannot: whether citations really support a mechanism, whether conditions are decidable, and *(plan B)* whether branches are genuine competitors rather than padding.

## What we deliberately did not build

- **Probability propagation.** Multiplying three model-estimated probabilities is not a trade's success probability; a fork answers "which paths depend on the challenged premise", which is a structural question.
- **Unsourced "disagreement with the market" scores.** A gap between model and user probabilities is not an edge. Market references are shown only when real data exists, and we have none wired in yet.
- **An early plugin platform.** Only two seams are abstract, the Reasoner and the Evidence Provider; everything else is plain functions until its semantics settle.
- **Execution.** Plans are drafts with `approval_required = true`. Positions, order routing and stop translation live downstream.
- **Retrieval over the local knowledge base (yet).** The two curated packs are about 16k tokens, so they go into context whole; a Haiku Inspect pays roughly $0.005 for it, and quality is proven. RAG becomes worthwhile when the packs grow, which is the next stage.
- **A Critic.** The slot exists in the pipeline and in the data and returns "disabled: out of scope for this phase". When built, it will check only the chosen chain, looking for a wrong key dependency, sycophancy, or excess skepticism.

## Known limitations

- **News coverage.** AP, Reuters and most wire services block Claude's fetchers, so the whitelist's news sources are thin (Focus Taiwan, Al Jazeera). There is no price data source yet.
- **Dates.** Search results give relative ages ("11 days ago"), so many online excerpts have `date: unknown`. We record unknown rather than invent a date.
- **Roots stay unknown.** Evidence attaches to edges, so a root event or exogenous assumption always shows as *unknown*. Web search improves the edges, not the node count.
- **Shock labelling.** Plan B detects a hypothetical branch only if the model marks not-yet-happened events as `role=shock`, so this is on the human review sheet.
- **Instrument mapping.** Some conclusions end at a category ("Brent futures or related ETF") rather than a ticker, because the evidence names no ticker and the model is not allowed to invent one.

## Run it

You need Python 3.12 and Node 20.19+ or 22.12+ (Vite 8). If `python3.12` is not on your PATH, `uv venv --python 3.12 .venv` creates the same environment.

### Offline: no API key, no cost

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python -m pytest -q                         # all offline
.venv/bin/python -m eval.runner --replay eval/results/haiku-p7 --today 2026-10-19 --out eval/out/replay-p7/results.json   # re-score the recorded eval
cd web && npm ci && npm test && npm run build && npm run dev   # front end on recorded fixtures (MOCK) at http://localhost:5173
```

The replay re-scores the recorded model calls in `eval/results/haiku-p7/cassette.jsonl` and writes its results to `eval/out/replay-p7/`. Pass `--out` as above: without it, the replay overwrites the committed results and scorecard in `eval/results/haiku-p7/`. The p7 recording predates p8, which sends every grounded and hypothesis Discover candidate to Inspect. Under the current code, the discover-entry cases C1 and D1 and their probes P3 and P4 therefore stop with `CassetteMiss` until they are re-recorded, so the replayed score differs from the scorecard table above. All other cases replay.

In MOCK mode the front end reads the recorded fixtures in `web/fixtures/` and does not need the back end. Pick a fixture in the header and click Analyze.

### Against the real model

The back end reads your Anthropic API key from the `ANTHROPIC_API_KEY` environment variable. Either export it in your shell, or put it in a `.env` file at the repository root (`.env` is git-ignored) and load it:

```bash
echo 'ANTHROPIC_API_KEY=sk-ant-...' > .env            # your key; never committed
set -a && . ./.env && set +a                          # export it into the current shell
```

Then, in the same shell (these commands call the API and cost money):

```bash
CATALYST_MODEL=claude-haiku-5-5 .venv/bin/python -m catalyst run D1 --live            # record a run
.venv/bin/python -m catalyst run D1 --replay runs/D1/<timestamp>                       # replay, no network
CATALYST_MODEL=claude-haiku-5-5 .venv/bin/python -m catalyst run C2 --live --online   # with web search
.venv/bin/python -m eval.runner --record eval/out/<name>                               # all cases, both groups
CATALYST_JUDGE_MODEL=claude-sonnet-5-5 .venv/bin/python -m eval.judge eval/results/haiku-p7/results.json --record eval/results/haiku-p7/judge   # LLM judge (or --replay)
.venv/bin/python -m eval.scorecard --readme README.md eval/results/haiku-p6m/scorecard.json eval/results/haiku-p7/scorecard-offline.json eval/results/haiku-p7/scorecard.json   # refresh the scorecard table
.venv/bin/python -m catalyst.api                      # HTTP API on :8000 (set CATALYST_PORT to change)
cd web && VITE_MOCK=0 npm run dev                     # front end on the real API (set CATALYST_API if the API is not on :8000)
```

The default reasoning model is `claude-opus-5-5`; we develop and test on `claude-haiku-5-5` (set `CATALYST_MODEL`). Web retrieval defaults to Haiku and can be overridden with `CATALYST_WEB_MODEL`.

## Repository map

| Path | What |
| --- | --- |
| `catalyst/schema.py` | The single data contract shared by the API, the UI and the eval |
| `catalyst/validator.py`, `conditions.py`, `gate.py`, `fork.py`, `diff.py` | The rules that code, not the model, decides |
| `catalyst/harness.py`, `reasoner.py`, `entrypoints.py`, `prompts.py` | Controlled generation: call → parse → validate → repair, recorded and replayable |
| `catalyst/websearch.py`, `config/web_whitelist.json` | Whitelisted online retrieval, frozen into evidence packs |
| `catalyst/api.py`, `web/` | HTTP API and the React front end |
| `packs/` | Curated evidence packs (semiconductors, Hormuz), each excerpt traceable to a source |
| `eval/`, `tests/` | Cases, golden fixtures, runner and report; deterministic tests |
| `docs/` | PRD, engineering design, front-end design, core design notes, change notes |

## Documents

- [docs/prd.md](docs/prd.md): product scope, the user, the core experience, and the testable hypothesis.
- [docs/engineering-design.md](docs/engineering-design.md): principles, data model, agent loop, evidence grounding, forks, validators, eval, decision log, risks.
- [docs/frontend-design.md](docs/frontend-design.md) and [docs/frontend/](docs/frontend/): UI and front-end engineering.
- [docs/core-design.md](docs/core-design.md): implementation decisions in the core package.
- [docs/websearch/design.md](docs/websearch/design.md): online retrieval and the whitelist.
- [docs/changes/](docs/changes/): the two change notes currently being implemented.

The design documents started as exports from Claude Docs and have since been revised in the repository; the repository version is the source of truth.

## Next steps

Re-record every case under the current prompts and do human review. Then structural graph editing: the fork operations today change what a node says or add a new cause that points into existing nodes; they cannot delete a node, insert one between two existing nodes, rewire edges or add a new conclusion. Each of these needs its own operation type, because every edit must stay a recorded operation whose write scope code computes before the model re-reasons; deleting a node can be approximated today by changing it to "this does not happen". Related, and smaller: when the user adds a cause, let the model propose which nodes it affects and in which direction, shown as dashed links the user keeps, flips or drops before the usual add_shock runs. The back-end endpoint for this (`POST /api/runs/{run_id}/suggest_impacts`, code-checked, creates no version) has been prototyped and tested but kept off main, and the UI is not built. Beyond that: a "submit graph" tool inside the agent loop, so the validator gives feedback in-loop; RAG over larger knowledge bases; a real Critic; market references from live data; structured threshold sources and per-condition automatability, so that approved plans can be exported to an execution layer.
