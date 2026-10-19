"""B 层（关键场景）的自动检查，以及读图的小工具。

检查由案例 expected 里的字段驱动：字段在，就做对应的检查；字段不在，什么都不做。
判的是模型行为能被代码看出来的那一部分，语义上的对错仍归人工复核。不 import catalyst。
"""
from __future__ import annotations

from typing import Any

from eval.scoring import check, get, to_plain


# ---- 读图 ---------------------------------------------------------------------

def graph_edges(out: Any) -> list[dict]:
    return list((to_plain(get(out, "graph")) or {}).get("edges") or [])


def cited_excerpts(out: Any) -> dict[str, set[str]]:
    """{excerpt_id: {stance, ...}}：图上每条边引用了哪些片段、以什么立场。"""
    cited: dict[str, set[str]] = {}
    for e in graph_edges(out):
        for ev in e.get("evidence") or []:
            if ev.get("excerpt_id"):
                cited.setdefault(ev["excerpt_id"], set()).add(str(ev.get("stance")))
    return cited


def model_only_edge_count(out: Any) -> int:
    return sum(1 for e in graph_edges(out) if e.get("model_only"))


def plan_conditions(plan: Any, which: str = "both") -> list[dict]:
    entry = list(get(plan, "entry_conditions") or [])
    exit_ = list(get(plan, "exit_conditions") or [])
    return {"entry": entry, "exit": exit_, "both": entry + exit_}[which]


# ---- B 层检查 -------------------------------------------------------------------

def _label(plan: Any) -> str:
    return str(get(plan, "terminal_id") or "?")


def _decidable(c: dict) -> list[str]:
    """一条条件缺了哪些「能被判定」所需的字段。"""
    missing = []
    if not (get(c, "series") or get(c, "source")):
        missing.append("series/source")
    if not get(c, "rule"):
        missing.append("rule")
    window = get(c, "observation_window") or {}
    if not (get(window, "start") and get(window, "end")):
        missing.append("observation_window")
    if get(c, "kind") == "numeric":
        if not get(c, "comparator"):
            missing.append("comparator")
        if get(c, "threshold") is None and not get(c, "threshold_note"):
            missing.append("threshold or threshold_note")
    return missing


def scenario_checks(case: dict, out: Any, plans: list, no_chain: bool) -> list[dict]:
    exp = case.get("expected", {})
    checks: list[dict] = []

    if exp.get("no_chain_preferred"):
        kinds = [get(b, "kind") for b in (get(out, "branches") or [])]
        ok = no_chain or "evidenced" not in kinds
        checks.append(check("no_chain_or_unevidenced_branches", "E4", ok,
                            "" if ok else f"built a chain with an evidenced branch: {kinds}", "forced_chain"))

    bad_ids = exp.get("must_not_cite_as_support") or []
    if bad_ids:
        cited = cited_excerpts(out)
        hits = sorted(x for x in bad_ids if "supports" in cited.get(x, set()))
        checks.append(check("no_support_citation_of_listed_excerpts", "E1", not hits,
                            f"cited {hits} as supporting evidence" if hits else "", "citation_laundering"))

    if exp.get("condition_fields_required") and not no_chain:
        gaps = {f"{_label(p)}:{get(c, 'id')}": m for p in plans for c in plan_conditions(p, "entry")
                if (m := _decidable(c))}
        ok = bool(plans) and not gaps
        checks.append(check("conditions_decidable_fields", "E2", ok,
                            f"missing fields: {gaps}" if gaps else ("" if plans else "no plans"), "condition_undecidable"))

    if "exit_logic" in exp and not no_chain:
        need = exp.get("min_exit_conditions", 1)
        wrong = [f"{_label(p)}: exit_logic={get(p, 'exit_logic')}, {len(plan_conditions(p, 'exit'))} exit conditions"
                 for p in plans
                 if get(p, "exit_logic") != exp["exit_logic"] or len(plan_conditions(p, "exit")) < need]
        ok = bool(plans) and not wrong
        checks.append(check("exit_logic_any_with_min_conditions", "E2", ok,
                            "；".join(wrong) if wrong else ("" if plans else "no plans"), "exit_logic_wrong"))

    if exp.get("anchor_prefix") and not no_chain:
        prefix = exp["anchor_prefix"]
        conds = [c for p in plans for c in plan_conditions(p)]
        ok = any(str(get(c, "anchor") or "").startswith(prefix)
                 or str(get(get(c, "observation_window") or {}, "start") or "").startswith(prefix) for c in conds)
        checks.append(check("relative_anchor_uses_scenario_prefix", "E2", ok,
                            "" if ok else f"no condition anchors on {prefix}... (the date may be invented)", "relative_anchor_invented"))

    if exp.get("no_chain") is False:
        checks.append(check("no_chain_is_false", "E4", not no_chain,
                            "gave no_chain although the pack supports the chain" if no_chain else "", "over_refusal"))

    wanted = [x.upper() for x in exp.get("plan_instruments_include") or []]
    if wanted:
        have = {str(get(get(p, "direction") or {}, "instrument") or "").upper() for p in plans}
        missing = [x for x in wanted if x not in have]
        checks.append(check("plan_for_instrument", "E4", not missing,
                            f"no plan for {missing} (plans cover: {sorted(have)})" if missing else "",
                            "missing_plan_for_target"))
    return checks
