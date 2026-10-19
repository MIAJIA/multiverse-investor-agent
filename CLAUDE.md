# Catalyst (multiverse-investor-agent)

A research tool for retail traders. The user enters an event. The system returns a causal graph and a conditional trade proposal (a draft, never executed). The user can change one assumption to fork, and see which premises are challenged. This is an interview take-home. Product and architecture follow `docs/prd.md` and `docs/engineering-design.md` (they started as exports from Claude Docs; the repository version is now the source of truth). Implementation-level decisions are recorded in `docs/core-design.md`.

## One principle

**The model proposes, the code decides.** The model enters only through `catalyst/reasoner.py`, and it can only propose causal hypotheses, mechanisms, conditions and explanations. The items below are written by code only. No change may hand them to the model:
- the gate, a proposal's status and support_status, and version numbers;
- condition evaluation (evaluation_status);
- a fork's write scope, and the assessment of claims outside that scope;
- the diff;
- confirmed, confirmed_claim_ids and probability in the user's judgment.

## Data contract

**The only source is `catalyst/schema.py`.** The UI, the eval and the harness do not keep their own copy.

- Snapshots, the API, diffs and hashes always use the canonical form from `.dump()`: all fields present, including defaults.
- When you change a field, change these together:
  - `web/src/types.ts` (the TS mirror; field names unchanged, character for character);
  - `eval/INTERFACE.md`;
  - if needed, `eval/fixtures/` and `tests/_adapter.py`.
- The shapes of model output are `*Output` and `ProposalDraft`. They deliberately have fewer fields than the persisted objects. No field that code decides is in them.
- Graph snapshots are immutable. Approval (the interface name is still sign) and fork both produce a new version and never overwrite the old one.
- **Plan B — competing branches, one plan per terminal** (`docs/changes/2026-10-18-branches-and-plans.md`):
  - The version bundle `VersionBundle` is `{graph, proposals, branches, node_kinds, edge_kinds, scenario, diff, excerpts}`. There is **no** `proposal` field. inspect / fork / sign results also carry a `proposals` list (`[]` when there are none).
  - `proposals` follow the graph's terminal order. Each has a `terminal_id`, and `meta.proposal_version = "{graph_version}.{terminal_id}"`. `parse_proposals` reads a legacy single-dict file as a one-item list.
  - `catalyst/branches.py` (`derive_views`) derives the following; kinds are decided by code, never by the model:
    - `branches`: `{terminal_id, divergence_node_ids, own_node_ids, own_edge_ids, kind, trunk, synthetic_evidence}`;
    - the lookup tables `node_kinds: {node_id: kind}` and `edge_kinds: {edge_id: kind}`, with kind one of hypothetical / evidenced / model_only.
  - Approval:
    - approved means `user_judgment.confirmed`, and at most one plan per version is approved;
    - `sign` with `terminal_id: null` approves none (no trade);
    - `user_judgment.note` is written by the user only.
  - `approval_reset` and `rival_changed` are written by fork only. They describe what changed relative to the parent version and are never inherited.
  - `validator.validate_plans` blocks unless:
    - the plans' terminals are exactly the graph's terminals;
    - each instrument belongs to its plan's terminal;
    - every plan carries the same `original_statement` / `clarified_statement`.

## Directories and ownership

| Directory | Contents | Owner |
| --- | --- | --- |
| `catalyst/` | Core: schema, validator, conditions, gate, fork, diff, store, reasoner, harness, entrypoints, prompts, api, CLI | core line |
| `catalyst/evidence.py` | Evidence Provider and BM25 `search()` | evidence line (the schema does not belong to the evidence line) |
| `packs/` | Real evidence packs (EvidencePack); every excerpt traces back to a source | evidence line |
| `eval/`, `tests/` (except `tests/core/` and `tests/evidence/`) | Cases, golden fixtures, runner, reports, eval tests | eval line |
| `tests/core/` | Core regression tests | core line |
| `tests/evidence/` | Evidence pack tests | evidence line |
| `web/`, `docs/frontend/` | Front end (Vite + React + @xyflow/react); one page, three tabs sharing one state | front-end line |
| `fixtures/` | Shared fixtures generated from real recordings by `python -m catalyst promote` | never hand-written |

**Rules for parallel work**: each line works in its own git worktree and branch, edits only its own files, and does not push. The main session does the merging, and runs the full test suite after each merge.

## How to run

```bash
.venv/bin/python -m pytest -q                       # core + eval + evidence, all offline
cd web && npm test && npm run typecheck && npm run build
.venv/bin/python web/scripts/check_fixtures.py      # front-end fixtures match the schema
```

```bash
set -a && . ./.env && set +a                        # load the API key (.env is never committed)
.venv/bin/python -m catalyst run D1 --live          # run one case: recording + snapshots go to runs/D1/<timestamp>/
.venv/bin/python -m catalyst run D1 --replay runs/D1/<ts>   # zero-cost, deterministic replay
.venv/bin/python -m catalyst run <case.json> --live --online   # first search the whitelisted sites (config/web_whitelist.json), freeze the results into an evidence pack, then reason; off by default, replay never goes online
.venv/bin/python -m catalyst promote runs/D1/<ts> d1        # promote to fixtures/d1.json
.venv/bin/python -m eval.runner --record eval/out/<name>    # all cases x pipeline / baseline groups, with a per-case report
.venv/bin/python -m catalyst.api                    # HTTP API for the front end, http://localhost:8000
cd web && VITE_MOCK=0 npm run dev                   # front end on the real back end (default VITE_MOCK=1 reads fixtures)
```

- Model: `CATALYST_MODEL`, default `claude-opus-5-5`; use `claude-haiku-5-5` for debugging. Set effort with `CATALYST_EFFORT`. The web search step has its own `CATALYST_WEB_MODEL`, default `claude-haiku-5-5` (stance labelling and reasoning still use `CATALYST_MODEL`).
- Replay matches on the request hash. If the prompt, the evidence pack, the schema or the input changes, old recordings raise `CassetteMiss`. When you change a prompt, bump `PROMPT_VERSION`.

## What not to do

- Do not hand-write graph-level fixtures. A person may write the expectations (what the gate should be, which claims should be challenged). The graph must be promoted from a real recording.
- Do not tune a prompt to make an eval case pass. Few-shot examples must not contain eval cases.
- Do not let code silently rewrite the model's output. If validation fails, send the errors, with object ids, back to the model to rewrite.
- Evidence packs do not take content that cannot be traced to a source, and do not invent numbers or dates.
- Do not commit `.env`, `runs/` or `web/node_modules/`.
