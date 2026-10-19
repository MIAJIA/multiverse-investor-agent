# Catalyst — from a belief to a plan you can approve

A research copilot for retail traders. You type a belief ("the Strait of Hormuz reopens next week"). Catalyst turns it into a causal graph with competing branches and gives each conclusion a pre-filled, conditional trade plan: what to do, what has to be observed before entering, what would get you out, and which premise matters most. You review the plans, adjust the thresholds nobody could source, and approve one of them, or none. Approving a plan is not placing an order.

> **Status (2026-10-18).** `main` contains everything in the "Merged" column below. Plan B (competing branches with one plan per conclusion) and the Inspect research loop are being built on parallel branches and will be merged next; this README already describes them and marks them as such. Numbers in the evaluation section come from real model runs, not estimates.

| Merged on `main` | In progress |
| --- | --- |
| Discover / Inspect / Fork pipeline, validators, entry gate, scoped forks, stacked scenarios, sign-off, versioned snapshots, record / replay harness, HTTP API, React front end (B1 graph, B2 sign-off, B3 scenario diff), eval runner and report, two curated evidence packs, online search switch with a domain whitelist | Plan B: competing branches, one plan per conclusion, approve-a-plan, branch kinds derived by code. Research loop: agent-driven web research before graph building, plus one gap-driven follow-up round |

**Demo video:** _link to be added._ A walkthrough of the system design is in the separate presentation.

---

## The problem

Retail traders act on events. When a headline hits, a chatbot gives them 400 balanced words and no decision. What they actually lack is a short list of answers to four questions: **what to do, what has to happen first, what would prove me wrong and by when, and what is the one premise this trade really rests on.** Most of the time the honest answer is "not yet", and that is the advice most often skipped.

The founder's own framing set the constraints we designed around: the trader gives a belief, the system builds the trade, and a human approves before anything executes; the models should be restrained "quite a bit"; and the three hard problems are output quality, execution, and UX.

## What it does

1. **Discover.** Input an event, optionally a target. Catalyst proposes at most three directions, each labelled *grounded*, *hypothesis*, or *not recommended*, or it abstains. Zero is a valid answer.
2. **Inspect.** Pick a direction. Catalyst builds a causal DAG down to tradable instruments. *(Plan B, in progress:)* where the evidence genuinely disagrees, it splits into 2–3 competing branches, and the divergence point is the premise most worth checking. Every branch is marked by code as **evidenced**, **model-only**, or **hypothetical** (resting on an event that has not happened). Each conclusion gets a pre-filled plan with entry conditions (AND), exit conditions (explicit ANY / ALL), and a key dependency. If nothing is met yet, the plan says **WAIT**.
3. **Approve.** Confirm "we understood your idea as …", fill in any threshold marked *needs your confirmation*, and approve one plan or none. At most one plan per version is approved.
4. **Change an assumption.** Catalyst recomputes only what depends on it and produces a new version. Out-of-scope nodes stay byte-identical, challenged premises are listed with a reason and a next check, and only the approved plans the change actually touches are invalidated. The original version is kept, so you compare two futures instead of overwriting one.

## Design principles

**The model proposes, the code decides.** The model writes causal hypotheses, mechanisms, conditions and explanations. Code owns everything that must not drift with the model: schemas, validators, the entry gate (WAIT / BLOCKED / READY_FOR_REVIEW), condition evaluation, fork write scopes, assessments outside the scope, diffs, versions, branch kinds, and every field the user signs. The model output schemas simply have no fields for `confirmed` or `probability`, so the model cannot approve on the user's behalf.

**The agent finds and thinks, code decides and guards, the user approves.** We did not pick "workflow" or "agent" for the whole system. We picked per step, by asking two questions: can the path be known in advance, and would a mistake silently produce a credible-looking conclusion?

| Step | Mode | Why |
| --- | --- | --- |
| Finding evidence (what to search, which source, how many rounds) | Agent loop *(in progress)* | The path is open-ended; one extra round costs only time and money |
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
- **Eval:** 11 cases. Six are CausalT5k causal-judgment items (YES / NO / AMBIGUOUS, including a skepticism trap and a sycophancy probe), four are built from the assignment's own examples (C1–C4), and one is the founder's Hormuz example (D1). Every case also runs as a single-prompt baseline with the same model and the same evidence. We report per-case results and failure types, never percentages.

Latest run on the real evidence packs (Claude Haiku 5.5):

| Case | Result |
| --- | --- |
| C1 photonic adoption → laser / foundry names | 3 grounded directions with real tickers (LITE, AVGO, TSEM); the key dependency came from counter-evidence: external light sources cut laser count to a quarter, so CPO volume must grow more than 4× before laser demand grows |
| C2 frontier-model export limits → NVDA | Declined to build a chain offline: the model-weight rule had been rescinded and the remaining material covers chips, not models. With web search on, it retrieved 17 excerpts from whitelisted sites (BIS, SEC, ECB, Al Jazeera) and built a chain that ends in WAIT |
| C3 fork the C1 graph twice | Both forks pass: challenged claims match the golden set, 0 out-of-scope writes |
| C4 midterm split → distant ticker | Abstains, as intended |
| D1 Hormuz reopens next week | Three directions (grounded / hypothesis / not recommended); the plan is WAIT; "transits recover" is marked contradicted by history; the key dependency is the Saudi East-West pipeline |
| T1–T6 CausalT5k | 4 of 6 match; T2 (YES → AMBIGUOUS) and T5 (AMBIGUOUS → NO) miss in both the pipeline and the baseline, which points at the model rather than the pipeline |

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

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python -m pytest -q                         # all offline
cd web && npm ci && npm test && npm run build && cd ..
```

```bash
set -a && . ./.env && set +a                          # ANTHROPIC_API_KEY; never committed
CATALYST_MODEL=claude-haiku-5-5 .venv/bin/python -m catalyst run D1 --live            # record a run
.venv/bin/python -m catalyst run D1 --replay runs/D1/<timestamp>                       # replay, no network
CATALYST_MODEL=claude-haiku-5-5 .venv/bin/python -m catalyst run C2 --live --online   # with web search
.venv/bin/python -m eval.runner --record eval/out/<name>                               # all cases, both groups
.venv/bin/python -m catalyst.api                      # HTTP API on :8000
cd web && VITE_MOCK=0 npm run dev                     # front end on the real API (default: recorded fixtures)
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

Merge plan B and the research loop, re-record every case, and do human review. Beyond that: a "submit graph" tool inside the agent loop, so the validator gives feedback in-loop; RAG over larger knowledge bases; a real Critic; market references from live data; structured threshold sources and per-condition automatability, so that approved plans can be exported to an execution layer.
