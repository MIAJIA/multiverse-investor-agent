# haiku-p6m

Offline eval run recorded on 2026-10-19 with Claude Haiku 5.5 and prompt version p6 (core commit 0497efa).
Kept as the run before p7, so the scorecard can compare two runs.

- `cassette.jsonl`: every model request and response.
- `results.json`, `report.md`, `scorecard.json`, `scorecard.md`: re-scored with the current eval code.

Replaying needs the core as it was at 0497efa (p7 changed the prompts, so today's core misses the cassette):

```bash
git archive 0497efa catalyst packs | tar -x -C /tmp/core-0497efa
.venv/bin/python -c "import sys; sys.path.insert(0, '/tmp/core-0497efa'); import catalyst, eval.runner as r; r.main(['--replay', 'eval/results/haiku-p6m', '--today', '2026-10-19'])"
```

The p6m online run is not kept: it was recorded before the eval runner wired the research loop for online cases, so W1 effectively ran offline.
