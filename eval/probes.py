"""P 层行为探针：成对扰动，只报每对的差异，不报百分比。

一对 = 同一个案例跑两次（只跑 pipeline 组），只改一处：
- pressure：在用户输入前加一句确定语气（T4 本身带加压句，plain 一侧用数据集原文 claim）；
- drop_excerpt：从本轮资料包里拿掉指定片段（回测案例从 allowed_excerpts 里拿掉）。
不 import catalyst。
"""
from __future__ import annotations

import copy
from typing import Any

from eval.loader import load_case, load_json, CASES_DIR

# 报告里比较的字段：只列出两次运行不一样的那些
COMPARED = ("label", "no_chain", "candidates", "abstained", "plans", "branch_kinds", "conditions",
            "cited_excerpts", "model_only_edges")


def load_probes() -> dict:
    return load_json(CASES_DIR / "probes.json")


def _plain_event(case: dict) -> str:
    rec = case.get("source", {}).get("record", {})
    if case.get("probe") == "sycophancy" and rec.get("claim"):
        return rec["claim"]  # T4：去掉案例里自带的加压句
    return case["input"]["event"]


def variant(case: dict, side: dict, prefix: str, pair_id: str, label: str) -> dict:
    c = copy.deepcopy(case)
    if side.get("event") == "plain":
        c["input"]["event"] = _plain_event(case)
    elif side.get("event") == "pressure":
        c["input"]["event"] = case["input"]["event"] if case.get("probe") == "sycophancy" else prefix + _plain_event(case)
    if side.get("drop_excerpts"):
        c["_drop_excerpts"] = list(side["drop_excerpts"])
    c["_probe"] = {"pair": pair_id, "side": label}
    return c


def diff(a: dict, b: dict) -> dict:
    out = {}
    for k in COMPARED:
        va, vb = a.get(k), b.get(k)
        if va != vb and not (va is None and vb is None):
            out[k] = {"a": va, "b": vb}
    return out


def run_probes(run_case_fn, *, reasoner: Any, evidence: Any = None, entrypoints: Any = None,
               evaluate_condition: Any = None, ids: list[str] | None = None) -> list[dict]:
    """run_case_fn 是 eval.runner.run_case（由调用方传入，避免循环 import）。"""
    spec = load_probes()
    results = []
    for pair in spec["pairs"]:
        if ids and pair["id"] not in ids:
            continue
        base = load_case(pair["case"])
        runs = {}
        for label in ("a", "b"):
            c = variant(base, pair[label], spec["pressure_prefix"], pair["id"], label)
            runs[label] = run_case_fn(c, "pipeline", reasoner=reasoner, evidence=evidence, entrypoints=entrypoints,
                                      evaluate_condition=evaluate_condition)
        errors = {k: r["actual"].get("error") for k, r in runs.items() if r["status"] == "ERROR"}
        results.append({
            "case_id": pair["id"], "group": "pipeline", "layer": "P", "case_type": "probe",
            "probe": {"base_case": pair["case"], "kind": pair["kind"], "question": pair["question"],
                      "a": pair["a"], "b": pair["b"]},
            "diff": diff(runs["a"]["actual"], runs["b"]["actual"]) if not errors else {},
            "runs": {k: {"status": r["status"], "failure_types": r["failure_types"], "actual": r["actual"]}
                     for k, r in runs.items()},
            "status": "ERROR" if errors else "PENDING_REVIEW",
            "failure_types": ["error"] if errors else [],
            "actual": {"error": "; ".join(f"{k}: {v}" for k, v in errors.items())} if errors else {},
            "human_review": [pair["question"]],
        })
    return results
