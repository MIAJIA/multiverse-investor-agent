"""Fake reasoner / evidence / 核心入口：只用于测试 runner 与报告，以及生成 sample_results.json。

结果全是编的，不代表任何模型或流程的真实表现。不调模型，不读 API key。
"""
from __future__ import annotations

import copy
import json
from typing import Any

from eval.loader import load_case, load_fixture


class FakeEvidence:
    def load_pack(self, pack_id: str) -> list[dict]:
        if pack_id == "semiconductor":
            return load_fixture("c1_evidence_pack.json")["excerpts"]
        if pack_id == "hormuz":
            return load_fixture("d1_hormuz.json")["evidence_pack"]["excerpts"]
        return []


class FakeReasoner:
    """baseline 组：按提示词里出现的关键词返回预设 JSON 字符串。"""

    def __init__(self, responses: dict[str, str] | None = None, default: str = '{"label": "YES", "rationale": "fake"}'):
        self.responses = responses or {}
        self.default = default
        self.calls: list[str] = []

    def single_prompt(self, prompt: str) -> str:
        self.calls.append(prompt)
        for key, resp in self.responses.items():
            if key in prompt:
                return resp
        return self.default


def _apply_patch_for_fake(graph: dict, patch: dict, version: str) -> dict:
    """fake 用的打补丁：不检查范围（范围检查是核心的事）。"""
    g = copy.deepcopy(graph)
    for kind, key in (("nodes", "node_updates"), ("edges", "edge_updates"), ("conditions", "condition_updates")):
        idx = {e["id"]: e for e in g[kind]}
        for u in patch.get(key, []):
            idx[u["id"]].update(copy.deepcopy(u["fields"]))
    g["nodes"] += copy.deepcopy(patch.get("node_adds", []))
    g["edges"] += copy.deepcopy(patch.get("edge_adds", []))
    g["parent_version"], g["version"] = graph["version"], version
    return g


class FakeEntrypoints:
    """pipeline 组的假入口。labels 覆盖 CausalT5k 的预测（默认等于 gold）；leak_edge 让 fork 偷改一条范围外的边。"""

    def __init__(self, labels: dict[str, str] | None = None, leak_edge: str | None = None,
                 raise_on: set[str] | None = None, observations: list[str] | None = None):
        self.labels = labels or {}
        self.leak_edge = leak_edge
        self.raise_on = raise_on or set()
        self.observations = observations if observations is not None else ["sc-001", "sc-003", "sc-005", "hz-001", "hz-003"]
        self.calls: list[tuple[str, str]] = []

    def _maybe_raise(self, event: str):
        if any(k in event for k in self.raise_on):
            raise RuntimeError(f"fake failure for {event}")

    def discover(self, event: str, target: str | None = None, **kw) -> dict:
        self.calls.append(("discover", event))
        self._maybe_raise(event)
        if "选举" in event:
            return {"candidates": [], "abstained": True, "abstain_reason": "fake: 缺少因果依据", "observations": []}
        return {"candidates": [{"id": "cand-1", "direction": "fake", "label": "grounded", "rationale": "fake"},
                               {"id": "cand-2", "direction": "fake", "label": "hypothesis", "rationale": "fake"}],
                "abstained": False, "observations": list(self.observations)}

    def inspect(self, event: str, target: str | None = None, **kw) -> dict:
        self.calls.append(("inspect", event))
        self._maybe_raise(event)
        if kw.get("judgment_only"):
            case_id = next(c for c in ("T1", "T2", "T3", "T4", "T5", "T6")
                           if load_case(c)["input"]["material"] == kw.get("material"))
            label = self.labels.get(case_id, load_case(case_id)["expected"]["label"])
            return {"graph": None, "no_chain": False, "proposal": None,
                    "judgment": {"label": label, "rationale": "fake rationale"}, "observations": []}
        if "霍尔木兹" in event:
            conds = load_fixture("d1_hormuz.json")["entry_conditions"]
            uj = {"requires_user_confirmation": True}
        elif target:
            conds = [{"id": "cond.fake.doc", "kind": "document", "predicate": "observed_by", "threshold": None,
                      "threshold_note": "文件型条件"}]
            uj = {}
        else:
            conds = load_fixture("c1_graph_v1.json")["conditions"][:1]
            uj = {}
        proposal = {"entry_conditions": conds, "exit_conditions": [], "gate": "WAIT", "support_status": "draft",
                    "user_judgment": uj, "meta": {"approval_required": True}}
        return {"graph": {"version": "fake"}, "no_chain": False, "proposal": proposal,
                "judgment": None, "observations": list(self.observations)}

    def fork(self, graph: dict, op: dict, **kw) -> dict:
        self.calls.append(("fork", op["kind"]))
        fx = load_fixture("c3_change_assumption.json" if op["kind"] == "change_assumption" else "c3_add_shock.json")
        new = _apply_patch_for_fake(graph, fx["patch_in_scope"], graph["version"] + "-" + op["kind"])
        if self.leak_edge:
            next(e for e in new["edges"] if e["id"] == self.leak_edge)["mechanism"] = "fake 越界写入"
        return {"graph": new, "base_graph": graph, "scope": fx["expected_scope"], "diff": {},
                "scenario": {"version": new["version"], "base_version": graph["version"], "ops": [op],
                             "assessment": dict(fx["patch_in_scope"]["assessment"])},
                "proposal": None}


def sample_baseline_reasoner() -> FakeReasoner:
    """生成 sample_results.json 用的 baseline：故意制造几种失败，检验报告能把它们写出来。"""
    return FakeReasoner(responses={
        "中期选举": json.dumps({"abstained": False, "candidates": [{"direction": "fake", "label": "hypothesis"}]}),
        "霍尔木兹": json.dumps({"abstained": False, "candidates": [{"direction": "fake", "label": "grounded"}],
                              "conditions": [{"kind": "numeric", "series": "portwatch.hormuz.daily_transits",
                                              "threshold": 20, "threshold_note": None}]}),
        "光子芯片": json.dumps({"abstained": False, "candidates": [{"direction": "fake", "label": "grounded"}],
                              "conditions": [{"kind": "numeric", "series": "fake", "threshold": None, "threshold_note": "fake"}]}),
        "出口限制": "抱歉，我无法给出 JSON",
    })


def write_sample_results(path: str) -> list[dict]:
    from eval.loader import load_all_cases
    from eval.runner import run_all

    cases = load_all_cases()
    results = run_all(cases, ("pipeline",), reasoner=FakeReasoner(), evidence=FakeEvidence(),
                      entrypoints=FakeEntrypoints(labels={"T2": "AMBIGUOUS"}, leak_edge="c1.e5",
                                                  observations=["sc-001", "sc-003", "hz-001", "hz-003"]))
    results += run_all(cases, ("baseline",), reasoner=sample_baseline_reasoner(), evidence=FakeEvidence())
    for r in results:
        r["fake"] = True
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return results


if __name__ == "__main__":
    import sys
    write_sample_results(sys.argv[1] if len(sys.argv) > 1 else "eval/sample_results.json")
