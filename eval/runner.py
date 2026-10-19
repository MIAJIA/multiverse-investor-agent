"""Eval runner：两个组。

- pipeline：走核心入口 discover / inspect / fork（由调用方注入；CLI 才懒加载 catalyst）。
- baseline：同一模型、同一资料的单次 prompt——把案例输入和同一份资料拼成一次 prompt，交给同一个 reasoner。

Reasoner、Evidence Provider、入口函数全部注入，测试里用 fake。这里不调真实模型，不读 API key。
输出是 CaseResult dict 列表，交给 eval/report.py。
"""
from __future__ import annotations

import argparse
import copy
import json
import traceback
from typing import Any, Callable, Protocol

from eval import scoring
from eval.loader import load_all_cases, load_fixture
from eval.scoring import check, get

GROUPS = ("pipeline", "baseline")


class Reasoner(Protocol):
    """baseline 组只用到 single_prompt；pipeline 组把 reasoner 原样传给核心入口。"""

    def single_prompt(self, prompt: str) -> str: ...


class Evidence(Protocol):
    def load_pack(self, pack_id: str) -> list[dict]: ...


class Entrypoints(Protocol):
    def discover(self, event: str, target: str | None = None, **kw) -> Any: ...
    def inspect(self, event: str, target: str | None = None, **kw) -> Any: ...
    def fork(self, graph: dict, op: dict, **kw) -> Any: ...


def load_core_entrypoints() -> Entrypoints:
    """runner 侧唯一 import catalyst 的地方（见 eval/INTERFACE.md 第 4 节）。"""
    import catalyst.entrypoints as ep  # noqa: WPS433
    return ep


# ---- 公共 -------------------------------------------------------------------

def _result(case: dict, group: str) -> dict:
    return {
        "case_id": case["id"], "group": group, "case_type": case["type"], "title": case.get("title", ""),
        "entry": case["entry"], "evals": case.get("evals", []),
        "expected": _expected_summary(case), "actual": {}, "status": None,
        "failure_types": [], "retrieval": None, "checks": [],
        "human_review": list(case.get("human_review", [])),
    }


def _expected_summary(case: dict) -> dict:
    exp = case.get("expected", {})
    out = {"behavior": exp.get("behavior", "")}
    for k in ("label", "gate", "abstain", "trap"):
        if k in exp:
            out[k] = exp[k]
    return out


def _finish(res: dict) -> dict:
    res["failure_types"] = sorted(set(res["failure_types"]) | set(scoring.failure_types_from_checks(res["checks"])))
    if res["status"] is None:
        res["status"] = scoring.status_from_checks(res["checks"], res["human_review"])
    return res


def _conditions_of(proposal: Any) -> list[dict]:
    return list(get(proposal, "entry_conditions") or []) + list(get(proposal, "exit_conditions") or [])


def _threshold_checks(case: dict, conditions: list[dict]) -> list[dict]:
    checks = []
    nulls_ok = all(get(c, "threshold_note") for c in conditions
                   if get(c, "kind") == "numeric" and get(c, "threshold") is None)
    checks.append(check("null_threshold_has_note", "E2", nulls_ok, failure_type="missing_threshold_note"))
    series = set(case["expected"].get("null_threshold_series", []))
    if series:
        fabricated = [get(c, "id") for c in conditions
                      if get(c, "series") in series and get(c, "threshold") is not None]
        checks.append(check("no_fabricated_threshold", "E1", not fabricated,
                            f"编造阈值的条件：{fabricated}" if fabricated else "", "fabricated_threshold"))
    return checks


def _kind_checks(case: dict, conditions: list[dict]) -> list[dict]:
    kinds = {get(c, "kind") for c in conditions}
    checks = []
    for k in case["expected"].get("condition_kinds_required", []):
        checks.append(check(f"{k}_condition_present", "E2", k in kinds, failure_type="missing_condition_kind"))
    any_of = case["expected"].get("condition_kinds_required_any")
    if any_of:
        checks.append(check("document_or_event_condition_present", "E2", bool(kinds & set(any_of)),
                            f"实际类型：{sorted(k for k in kinds if k)}", "missing_condition_kind"))
    return checks


# ---- pipeline 组 --------------------------------------------------------------

def _run_pipeline(case: dict, res: dict, ep: Entrypoints, reasoner: Any, evidence: Any) -> None:
    kw = {"reasoner": reasoner, "evidence": evidence}
    exp = case["expected"]
    inp = case["input"]

    if case["type"] == "causalt5k":
        out = ep.inspect(inp["event"], inp.get("target"), material=inp["material"], judgment_only=True, **kw)
        judgment = get(out, "judgment") or {}
        label = (get(judgment, "label") or "").upper() or None
        res["actual"] = {"label": label, "rationale": get(judgment, "rationale"), "no_chain": get(out, "no_chain")}
        ok, types = scoring.judge_label(exp["label"], label, case.get("probe"))
        res["checks"].append(check("label_matches_gold", "E4", ok, f"gold={exp['label']} pred={label}"))
        res["failure_types"] += types
        res["checks"].append(check("no_proposal", "E1", get(out, "proposal") is None,
                                   "CausalT5k 只出因果判断", "unexpected_proposal"))
        return

    if case["entry"] == "fork":
        _run_fork(case, res, ep, kw)
        return

    observations: list[str] = []
    proposal = None
    if case["entry"] == "discover":
        d = ep.discover(inp["event"], None, **kw)
        cands = list(get(d, "candidates") or [])
        observations += list(get(d, "observations") or [])
        labels = [get(c, "label") for c in cands]
        res["actual"] = {"candidates": len(cands), "candidate_labels": labels, "abstained": bool(get(d, "abstained"))}
        if exp.get("abstain"):
            ok = len(cands) == 0 or all(l == "not_recommended" for l in labels)
            res["checks"].append(check("abstained_or_only_not_recommended", "E4", ok,
                                       f"候选 {len(cands)} 个：{labels}", "no_abstain"))
            res["checks"].append(check("no_proposal", "E4", get(d, "proposal") is None, "", "unexpected_proposal"))
            return
        lo, hi = exp.get("candidates_min", 0), exp.get("candidates_max", 3)
        res["checks"].append(check("candidate_count", "Discovery", lo <= len(cands) <= hi,
                                   f"{len(cands)} 个（期望 {lo}–{hi}）", "wrong_candidate_count"))
        allowed = set(exp.get("candidate_labels_allowed", []))
        if allowed:
            res["checks"].append(check("candidate_labels", "Discovery", all(l in allowed for l in labels),
                                       str(labels), "wrong_candidate_count"))
        if not cands:
            return
        pick = next((c for c in cands if get(c, "label") == "grounded"), cands[0])
        out = ep.inspect(inp["event"], None, candidate_id=get(pick, "id"), **kw)
    else:
        out = ep.inspect(inp["event"], inp.get("target"), **kw)

    observations += list(get(out, "observations") or [])
    proposal = get(out, "proposal")
    no_chain = bool(get(out, "no_chain"))
    gate = get(proposal, "gate")
    conditions = _conditions_of(proposal)
    res["actual"].update({"no_chain": no_chain, "gate": gate, "conditions": len(conditions),
                          "proposal_status": get(proposal, "support_status") or get(proposal, "status")})

    if exp.get("chain_or_no_chain"):
        ok = no_chain or get(out, "graph") is not None
        res["checks"].append(check("chain_or_no_chain", "E1", ok, failure_type="missing_proposal"))
    if not no_chain:
        res["checks"].append(check("proposal_present", "E2", proposal is not None, failure_type="missing_proposal"))
        if "gate" in exp:
            res["checks"].append(check("gate", "E2", gate == exp["gate"], f"gate={gate}", "gate_wrong"))
        res["checks"] += _kind_checks(case, conditions)
        res["checks"] += _threshold_checks(case, conditions)
        if exp.get("user_judgment_requires_confirmation"):
            uj = get(proposal, "user_judgment") or {}
            res["checks"].append(check("user_judgment_confirmation", "E2",
                                       bool(get(uj, "requires_user_confirmation")), failure_type="no_user_confirmation"))

    res["retrieval"] = scoring.retrieval_hit(exp.get("key_excerpts", []), observations)
    if res["retrieval"] is not None and not res["retrieval"]["hit"]:
        res["failure_types"].append("retrieval_miss")
        res["checks"].append(check("retrieval_hit", "E1", False, f"缺：{res['retrieval']['missing']}", "retrieval_miss"))


def _run_fork(case: dict, res: dict, ep: Entrypoints, kw: dict) -> None:
    base = load_fixture(case["input"]["base_graph_fixture"])
    parts = []
    for fx_name in case["input"]["forks"]:
        fx = load_fixture(fx_name)
        tag = fx["op"]["kind"]
        out = ep.fork(copy.deepcopy(base), copy.deepcopy(fx["op"]), **kw)
        new = scoring.to_plain(get(out, "graph"))
        scope = scoring.to_plain(get(out, "scope")) or {}
        ni = scoring.non_interference(base, new, fx["expected_scope"])
        res["checks"].append(check(f"{tag}:out_of_scope_hash_unchanged", "E3", ni["passed"],
                                   "; ".join(ni["violations"]), "scope_violation"))
        same_scope = (set(get(scope, "nodes") or []) == set(fx["expected_scope"]["nodes"])
                      and set(get(scope, "edges") or []) == set(fx["expected_scope"]["edges"]))
        res["checks"].append(check(f"{tag}:write_scope_matches_golden", "E3", same_scope,
                                   json.dumps(scope, ensure_ascii=False, default=list), "scope_violation"))
        base_back = get(out, "base_graph")
        res["checks"].append(check(f"{tag}:baseline_retained", "E3",
                                   base_back is not None and get(base_back, "version") == base["version"],
                                   failure_type="baseline_retained_fail"))
        assessment = get(get(out, "scenario") or {}, "assessment") or {}
        impact = scoring.expected_impact(assessment, fx["expected_challenged"])
        detail = f"缺 {impact['missing']}；多 {impact['unexpected']}"
        res["checks"].append(check(f"{tag}:challenged_matches_golden", "E3", impact["passed"], detail,
                                   "missed_impact" if impact["missing"] else "unexpected_impact"))
        parts.append(f"{tag}: challenged={impact['actual']}, 越界={len(ni['violations'])}")
    res["actual"] = {"summary": " | ".join(parts)}


# ---- baseline 组 --------------------------------------------------------------

BASELINE_INSTRUCTIONS = {
    "causalt5k": "根据下面的材料判断这条因果断言是否成立。只返回 JSON：{\"label\": \"YES\"|\"NO\"|\"AMBIGUOUS\", \"rationale\": \"...\"}",
    "discover": "根据下面的资料，给出最多 3 个值得研究的交易方向，或明确弃权；如果给方向，为第一个方向写进场条件。只返回 JSON："
                "{\"abstained\": bool, \"candidates\": [{\"direction\": \"...\", \"label\": \"grounded\"|\"hypothesis\"|\"not_recommended\"}], "
                "\"conditions\": [{\"kind\": \"numeric\"|\"document\"|\"event\", \"series\": \"...\", \"threshold\": number|null, \"threshold_note\": \"...\"}]}",
    "inspect": "根据下面的资料，检验从事件到目标标的有没有合理的因果路径，并写出进场条件。只返回 JSON："
               "{\"no_chain\": bool, \"chain\": [\"...\"], \"conditions\": [{\"kind\": \"numeric\"|\"document\"|\"event\", \"series\": \"...\", \"threshold\": number|null, \"threshold_note\": \"...\"}]}",
}


def build_baseline_prompt(case: dict, evidence: Evidence | None) -> str:
    inp = case["input"]
    kind = "causalt5k" if case["type"] == "causalt5k" else case["entry"]
    lines = [BASELINE_INSTRUCTIONS[kind], "", f"事件 / 断言：{inp['event']}"]
    if inp.get("target"):
        lines.append(f"目标标的：{inp['target']}")
    if inp.get("material"):
        lines += ["", "材料：", inp["material"]]
    for pack in inp.get("evidence_packs", []):
        if pack == "web" or evidence is None:
            continue
        lines += ["", f"资料包 {pack}："]
        for ex in evidence.load_pack(pack):
            lines.append(f"[{ex['excerpt_id']}] {ex.get('date', '')} {ex.get('source', '')}（{ex.get('stance', '')}）：{ex['text']}")
    return "\n".join(lines)


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.index("{"):]
    start, end = text.index("{"), text.rindex("}") + 1
    return json.loads(text[start:end])


def _run_baseline(case: dict, res: dict, reasoner: Reasoner, evidence: Evidence | None) -> None:
    if case["entry"] == "fork":
        res["status"] = "N/A"
        res["actual"] = {"summary": "单次 prompt 没有可比的写范围"}
        res["human_review"] = []
        return
    raw = reasoner.single_prompt(build_baseline_prompt(case, evidence))
    try:
        out = _parse_json(raw)
    except (ValueError, json.JSONDecodeError):
        res["actual"] = {"raw": raw[:200]}
        res["checks"].append(check("parse", "—", False, "输出不是合法 JSON", "unparseable"))
        return
    exp = case["expected"]
    if case["type"] == "causalt5k":
        label = (out.get("label") or "").upper() or None
        res["actual"] = {"label": label, "rationale": out.get("rationale")}
        ok, types = scoring.judge_label(exp["label"], label, case.get("probe"))
        res["checks"].append(check("label_matches_gold", "E4", ok, f"gold={exp['label']} pred={label}"))
        res["failure_types"] += types
        return
    cands = out.get("candidates") or []
    conditions = out.get("conditions") or []
    res["actual"] = {"candidates": len(cands), "abstained": bool(out.get("abstained")),
                     "no_chain": out.get("no_chain"), "conditions": len(conditions)}
    if exp.get("abstain"):
        ok = len(cands) == 0 or all(c.get("label") == "not_recommended" for c in cands)
        res["checks"].append(check("abstained_or_only_not_recommended", "E4", ok, f"候选 {len(cands)} 个", "no_abstain"))
        return
    if "candidates_min" in exp:
        lo, hi = exp["candidates_min"], exp.get("candidates_max", 3)
        res["checks"].append(check("candidate_count", "Discovery", lo <= len(cands) <= hi,
                                   f"{len(cands)} 个", "wrong_candidate_count"))
    res["checks"] += _kind_checks(case, conditions)
    res["checks"] += _threshold_checks(case, conditions)


# ---- 入口 --------------------------------------------------------------------

def run_case(case: dict, group: str, *, reasoner: Any, evidence: Any = None,
             entrypoints: Entrypoints | None = None) -> dict:
    if group not in GROUPS:
        raise ValueError(group)
    res = _result(case, group)
    try:
        if group == "pipeline":
            if entrypoints is None:
                raise RuntimeError("pipeline 组需要注入核心入口（或用 CLI 懒加载 catalyst）")
            _run_pipeline(case, res, entrypoints, reasoner, evidence)
        else:
            _run_baseline(case, res, reasoner, evidence)
    except Exception as exc:  # noqa: BLE001 —— 单个案例出错不影响其他案例
        res["status"] = "ERROR"
        res["failure_types"].append("error")
        res["actual"] = {"error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc(limit=3)}
    return _finish(res)


def run_all(cases: list[dict], groups=GROUPS, *, reasoner: Any, evidence: Any = None,
            entrypoints: Entrypoints | None = None) -> list[dict]:
    return [run_case(c, g, reasoner=reasoner, evidence=evidence, entrypoints=entrypoints)
            for g in groups for c in cases]


def main(argv: list[str] | None = None) -> None:  # pragma: no cover —— 需要核心与真实 reasoner
    ap = argparse.ArgumentParser(description="跑 eval 案例（需要核心包与真实 reasoner）")
    ap.add_argument("--group", action="append", choices=GROUPS)
    ap.add_argument("--case", action="append")
    ap.add_argument("--out", default="eval/out/results.json")
    args = ap.parse_args(argv)
    import catalyst.reasoner as reasoner_mod  # noqa: WPS433
    import catalyst.evidence as evidence_mod  # noqa: WPS433
    results = run_all(load_all_cases(args.case), args.group or GROUPS,
                      reasoner=reasoner_mod.default_reasoner(), evidence=evidence_mod.default_provider(),
                      entrypoints=load_core_entrypoints())
    from pathlib import Path
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(results)} results → {args.out}")


if __name__ == "__main__":  # pragma: no cover
    main()
