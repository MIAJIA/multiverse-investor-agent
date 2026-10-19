"""Inspect 的研究 loop（联网打开时才跑），依据 docs/changes/2026-10-18-agent-loop.md。

  第 1 轮：入口之前的联网检索（websearch.run_web_stage，round=1），资料包已经冻结并注册。
  建图：照常跑 Inspect（建图 + 出计划），这一遍写进 runs/<id>/research/r1/，只用来找缺口。
  缺口：由代码找（find_gaps；方案 B 合并后换成 branches.py 的 kind，接口是 GapDetector）。
  第 2 轮：有缺口才补查。输入只有事件、缺口所在的 claim / 边 / 条件、已有片段 id，不给结论和计划；
         仍由 web.label 标立场，冻结成第二份资料包（检索键含轮次和缺口）。
  定稿：带上全部资料包，从头重跑 Inspect，写进运行目录。没有补查时，重跑的请求和第 1 遍逐字相同，
       由 Memo 直接返回同一份输出，不多调模型。

研究最多 2 轮（MAX_ROUNDS）；要不要补查由代码决定，不由模型决定。对外契约不变：图、计划、版本包形状不改，
新增信息只在 dump() 里（case.json 与 API 返回体的 web 字段）。
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
"""输入 inspect 的返回值，输出缺口清单（每个缺口一个 dict，含 kind 与 id）。空清单 = 不补查。"""

_NEEDS_DATA = re.compile(r"缺|没有|无法|不知道|未知|数据|资料|基准|序列|data|missing|unknown", re.I)


def find_gaps(result: dict) -> list[dict]:
    """默认规则（D-A5）：model_only 的边；numeric 条件阈值为 null 且 threshold_note 写的是缺数据（或连序列都没有）。
    只给缺口所在的 claim、边、条件，不给结论（edge 的 mechanism）和计划（proposal）。"""
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


def _gap_reason(gaps: list[dict]) -> str:
    edges = sum(g["kind"] == "edge" for g in gaps)
    conds = len(gaps) - edges
    return f"{edges} 条没有证据的边（model_only）、{conds} 个缺数据的阈值"


class Memo:
    """同一次运行里请求逐字相同就直接返回上一次的输出：没有补查时，定稿重跑不多调模型；录制和回放走同一条路，
    所以 cassette 里每个请求只出现一次。"""

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
    detect: GapDetector = find_gaps
    rounds: list[WebResult] = field(default_factory=list)
    followup: dict = field(default_factory=lambda: {"triggered": False, "reason": "研究 loop 没有运行", "gaps": []})

    def __call__(self, run: Callable[..., dict], cfg, store: RunStore | None, reasoner: Reasoner) -> dict:
        """run(config=, store=, reasoner=) 跑一遍 Inspect（由 entrypoints.inspect 的挂钩传进来）。"""
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
        """web 字段：保留第 1 轮的字段（向后兼容），加上每轮明细和补查信息。"""
        rounds = self.rounds or [self.round1]
        return {**self.round1.dump(), "excerpts": sum(r.n for r in rounds), "pack_ids": self.packs,
                "rounds": [r.dump() for r in rounds],
                "followup": {"triggered": self.followup["triggered"], "reason": self.followup["reason"],
                             "gaps": [{"kind": g["kind"], "id": g["id"]} for g in self.followup["gaps"]]},
                "message": self.message()}
