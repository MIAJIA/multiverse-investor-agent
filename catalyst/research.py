"""Inspect's research loop (runs only with web retrieval on), per docs/changes/2026-10-18-agent-loop.md.

  Round 1: the web retrieval before the entry points (websearch.run_web_stage, round=1); its pack is already frozen
           and registered.
  Draft:   Inspect runs as usual (graph + plan) into runs/<id>/research/r1/; this pass is only used to find gaps.
  Gaps:    found by code: find_gaps_by_branch, i.e. model_only edges of model_only branches (branches.py) plus
           numeric conditions missing data; hypothetical branches are not researched.
  Round 2: only when there are gaps. Its input is the event, the claims / edges / conditions where the gaps are, and
           the ids of excerpts already collected, never the conclusions or the plan. Stance is still labelled by
           web.label, and the round is frozen as a second pack (the retrieval key includes the round and the gaps).
  Final:   Inspect reruns from scratch with all packs into the run directory. Without a follow-up the rerun's requests
           are identical to the draft pass, so Memo returns the same outputs and no extra model calls are made.

At most two rounds (MAX_ROUNDS); code, not the model, decides whether to follow up. The external contract does not
change: graph, plan and version bundle keep their shape, and new information appears only in dump() (the web field of
case.json and the API response). Status lines (message / gap reason) stay in Chinese because the CLI and UI show them.
"""
from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from catalyst.evidence import EvidenceProvider
from catalyst.reasoner import Completion, Reasoner, request_hash
from catalyst.store import RunStore
from catalyst.websearch import Searcher, WebResult, run_web_stage

MAX_ROUNDS = 2
MAX_GAPS = 8

GapDetector = Callable[[dict], list[dict]]
"""Takes an inspect result and returns the gaps (one dict each, with kind and id). An empty list means no follow-up."""

# threshold_note wording that means "missing data" (the model writes notes in the prompt language, so both)
_NEEDS_DATA = re.compile(r"缺|没有|无法|不知道|未知|数据|资料|基准|序列|data|missing|unknown|no baseline|not available", re.I)


def find_gaps(result: dict) -> list[dict]:
    """Default rule (D-A5): model_only edges; numeric conditions whose threshold is null because data is missing
    (or that have no series at all). Gives only the claims, edges and conditions where the gaps are, never the
    conclusions (edge mechanism) or the plan (proposal)."""
    g = result.get("graph")
    if not g:
        return []
    stmt = {n["id"]: n["statement"] for n in g["nodes"]}
    gaps = [{"kind": "edge", "id": e["id"], "from": stmt.get(e["from"]), "to": stmt.get(e["to"]), "channel": e["channel"]}
            for e in g["edges"] if e["model_only"]]
    for c in g.get("conditions", []):
        if c["kind"] == "numeric" and c.get("threshold") is None and (
                c.get("series") is None or _NEEDS_DATA.search(c.get("threshold_note") or "")):
            gaps.append({"kind": "condition", "id": c["id"], "claim": stmt.get(c["claim_id"]), "rule": c["rule"],
                         "series": c.get("series"), "threshold_note": c.get("threshold_note")})
    return sorted(gaps, key=lambda x: (x["kind"], x["id"]))[:MAX_GAPS]


def find_gaps_by_branch(result: dict) -> list[dict]:
    """Plan B rule (D-A5 after plan B): research only where a branch is model_only. Edges are the model_only edges in
    the own part of model_only branches, plus model_only trunk edges shared by them; hypothetical branches are skipped
    (an event that has not happened has no evidence to find). Conditions follow find_gaps."""
    from catalyst.branches import derive_views  # local import: research is optional for the core

    g = result.get("graph")
    if not g:
        return []
    edge_kinds = derive_views(g)["edge_kinds"]  # an edge takes its target node's kind (own branch or weakest trunk)
    edge_ids = {eid for eid, kind in edge_kinds.items() if kind == "model_only"}
    base = find_gaps(result)
    return [x for x in base if x["kind"] == "condition" or (x["kind"] == "edge" and x["id"] in edge_ids)][:MAX_GAPS]


def _gap_reason(gaps: list[dict]) -> str:
    edges = sum(g["kind"] == "edge" for g in gaps)
    conds = len(gaps) - edges
    return f"{edges} 条没有证据的边（model_only）、{conds} 个缺数据的阈值"


class Memo:
    """Within one run, an identical request returns the previous output. Without a follow-up the final rerun makes no
    extra model calls; recording and replay take the same path, so each request appears once in the cassette."""

    def __init__(self, inner: Reasoner):
        self.inner, self.name, self._seen = inner, inner.name, {}

    def complete(self, *, stage: str, system: str, user: str, schema: dict) -> Completion:
        h = request_hash(stage, system, user, schema)
        if h not in self._seen:
            self._seen[h] = self.inner.complete(stage=stage, system=system, user=user, schema=schema)
        return self._seen[h]


@dataclass
class ResearchLoop:
    event: str
    target: str | None
    evidence: EvidenceProvider
    round1: WebResult
    replay_dir: Path | str | None = None
    searcher: Searcher | None = None
    detect: GapDetector = find_gaps_by_branch
    rounds: list[WebResult] = field(default_factory=list)
    followup: dict = field(default_factory=lambda: {"triggered": False, "reason": "研究 loop 没有运行", "gaps": []})

    def __call__(self, run: Callable[..., dict], cfg, store: RunStore | None, reasoner: Reasoner) -> dict:
        """run(config=, store=, reasoner=) runs Inspect once (passed in by the hook in entrypoints.inspect)."""
        self.rounds = [self.round1]
        memo = Memo(reasoner)
        scratch = RunStore(store.root / "research" / "r1") if store else None
        first = run(config=cfg, store=scratch, reasoner=memo)
        gaps = self.detect(first)
        final_cfg = cfg
        if not gaps:
            why = "第 1 轮建图后没有缺口" if first.get("graph") else "第 1 轮没有产出图（no_chain 或校验失败）"
            self.followup = {"triggered": False, "reason": why, "gaps": []}
        elif len(self.rounds) >= MAX_ROUNDS:
            self.followup = {"triggered": False, "reason": f"已到研究轮数上限 {MAX_ROUNDS}", "gaps": gaps}
        else:
            self.followup = {"triggered": True, "reason": _gap_reason(gaps), "gaps": gaps}
            prior = [r.pack for r in self.rounds if r.pack is not None]
            r2 = run_web_stage(self.event, self.target, cfg=cfg, store=store, reasoner=memo, replay_dir=self.replay_dir,
                               searcher=self.searcher, round=2, gaps=gaps, prior=prior)
            self.rounds.append(r2)
            if r2.pack is not None:
                self.evidence.register(r2.pack)
                final_cfg = dataclasses.replace(cfg, packs=[*cfg.packs, r2.pack.pack_id])
        return run(config=final_cfg, store=store, reasoner=memo)

    @property
    def packs(self) -> list[str]:
        return [r.pack.pack_id for r in self.rounds if r.pack is not None]

    def message(self) -> str:
        msg = self.round1.message()
        f = self.followup
        if not f["triggered"]:
            return f"{msg}；补查：未触发（{f['reason']}）"
        r2 = self.rounds[1] if len(self.rounds) > 1 else None
        if r2 is not None and r2.pack is not None:
            return f"{msg}；补查：第 2 轮拿到 {r2.n} 段（触发原因：{f['reason']}），图和计划已带上全部片段重跑"
        return f"{msg}；补查：触发（{f['reason']}）但没有拿到新片段：{r2.reason if r2 else '未运行'}"

    def dump(self) -> dict:
        """The web field: round 1's fields (backward compatible) plus per-round details and follow-up info."""
        rounds = self.rounds or [self.round1]
        return {**self.round1.dump(), "excerpts": sum(r.n for r in rounds), "pack_ids": self.packs,
                "rounds": [r.dump() for r in rounds],
                "followup": {"triggered": self.followup["triggered"], "reason": self.followup["reason"],
                             "gaps": [{"kind": g["kind"], "id": g["id"]} for g in self.followup["gaps"]]},
                "message": self.message()}
