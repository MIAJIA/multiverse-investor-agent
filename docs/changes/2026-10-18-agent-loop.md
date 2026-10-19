# Change note: the research loop (agent loop) for Inspect

2026-10-18 · Version 1 · Status: **decided by Mia**

This note is the only basis for this change. It is being done at the same time as "One graph, several branches + approve a plan" (`2026-10-18-branches-and-plans.md`, scope set to **B-minimal**). If the two documents conflict, ask the main session. Do not rule on it yourself.

## 1. In one sentence

When web search is on, Inspect first runs a research loop. The model decides for itself what to look up on the whitelisted sites. The code freezes the source text the tools return into this round's evidence pack. Then the graph and plans are built as usual. After that, the code finds where evidence is missing and runs one targeted follow-up round, and the graph and plans are rerun from scratch.

## 2. Why change it

- Checking a claim is an open-ended task. What to look up, and how many times, cannot be fixed in advance. Today web search runs once at the start, and if reasoning finds missing evidence there is no way to go back and search again.
- This puts into practice the split "the agent finds and thinks, the code decides and guards, the user signs". Finding evidence goes to the agent. Whether to enter, and which parts to change, is still decided by the code.

## 3. Decisions

| # | Decision |
| --- | --- |
| D-A1 | **Research and graph building are separate (option A).** When the research loop ends, the evidence pack is frozen. Graph building and plans keep the existing single structured call. A "submit graph" tool inside the loop (option B) is left for the next phase |
| D-A2 | **The local knowledge base stays whole in the context.** The two packs total about 16k tokens, so one Inspect on Haiku costs about $0.005. No kb.search tool, and no automatic switch by size. The README says: when the packs grow, switch to RAG, which belongs to the next phase |
| D-A3 | **Research only when web search is on.** With web search off, behaviour is exactly as today, and offline requests do not change by a single character |
| D-A4 | **At most 1 follow-up round** (at most 2 research rounds in total). The search and fetch limits per round stay as in `Config` (5 each). The code decides whether to run a follow-up. The model does not |
| D-A5 | **The code finds the gaps**: an edge that leads to a terminal is model_only; or a condition's threshold is null and its threshold_note says the data is missing. Once plan B is merged, this changes to `kind == "model_only"` from `branches.py`, and the interface is left ready for it |
| D-A6 | **Input to the follow-up**: the event, a summary of the previous round's graph (only the claims, edges and conditions where the gaps are, not the conclusions or plans), and a list of the excerpt ids already held. It must look first for evidence on the premise at the divergence point, and for the data the thresholds need |
| D-A7 | **Every round must look for the other side.** The prompt requires at least one query per round that looks specifically for material that weakens the argument. The query terms are recorded in provenance, and one item is added to the human review sheet. The code cannot check this semantically, and does not pretend to |
| D-A8 | **Stance is still labelled by a separate step that cannot see the conclusion** (the existing `web.label`). The model that draws the conclusion does not judge the stance of web excerpts |
| D-A9 | **Record and replay by round.** Each round freezes one evidence pack (`runs/<id>/packs/web-<hash>.json`), and the retrieval key includes the round number and the gap list. Replay reads round by round and does not go online. If any input changes it raises `CassetteMiss` |
| D-A10 | **The external contract does not change**: the shapes of the graph, the plans and the version bundle do not change. New content appears only in the `web` field of `case.json` and of the API response: how many excerpts each round got, whether a follow-up was triggered, and why |
| D-A11 | **Test with Haiku only**: every real call uses `CATALYST_MODEL=claude-haiku-5-5`. Whether the final demo switches to Opus is Mia's call |
| D-A12 | **No prompt caching for now**: on Haiku the cost is already negligible, and caching means keeping the prefix stable, which is extra upkeep. Re-evaluate when the demo moves to Opus |

**Explicitly not doing**: making Discover an agent (on hold); researching again at fork time; retrieval over the local knowledge base / RAG; the "submit graph" tool; a retrieval hit-rate metric.

## 4. Scope of change and file ownership (parallel with the plan B back end; must be respected)

| File | Owner |
| --- | --- |
| `catalyst/websearch.py`, the new file `catalyst/research.py` (if needed), `tests/websearch/`, `tests/research/` | agent loop |
| `catalyst/prompts.py` | The agent loop may only **add new** research and follow-up constants at the **end** of the file. It does **not** change `BASE` / `INSPECT` / `DISCOVER` / `FORK` or `PROMPT_VERSION`. The follow-up prompt has its own version number, which goes into the retrieval key |
| `catalyst/entrypoints.py` | The agent loop adds only **one hook** inside inspect (the follow-up loop). The rest belongs to the plan B back end |
| `catalyst/__main__.py`, `catalyst/api.py` | The agent loop changes only the wiring for web search and the follow-up. `sign` / `promote` / the version bundle belong to the plan B back end |
| `catalyst/schema.py`, `validator.py`, `fork.py`, `store.py`, `branches.py` | Plan B back end; the agent loop does not touch them |

The main session handles merge conflicts. Conflicts are expected only near the hook in `entrypoints.inspect`.

## 5. Acceptance

- The full `pytest -q` passes. Offline unit tests use fake search results and a scripted reasoner.
- With web search off, the request hashes of the 10 eval cases are identical to those before the change.
- Test 3 web-enabled cases on Haiku: W1, C2, D1. For each case, report the number of model_only edges, the number of conditions with an empty threshold, and the number of new excerpts and their sources, for round 1 and round 2, plus the cost.
- Replay is byte-for-byte identical to the recording, and replay does not go online.

## 6. README items still to write (the main session will collect them)

- The knowledge base currently goes into the context whole. When it grows, switch to RAG (next phase).
- The trade-off of keeping research and graph building separate, and the "submit graph" tool as the next step.
- Limits of web search: AP, Reuters and other wire services are closed to Claude, so the news sources have gaps; the whitelist lacks official company sources and stock price data; PR Newswire lets law-firm advertising in.
