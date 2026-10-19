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


def decidable_missing(c: dict) -> list[str]:
    """公开版本：一条条件缺了哪些「能被数据判定」所需的字段（空列表 = 字段齐全）。"""
    return _decidable(c)


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


# ---- W 层：研究 loop 补查前后的对比 ----------------------------------------------------

def gap_counts(result: Any) -> dict:
    """一次 Inspect 结果里还剩多少「没证据」的地方：纯推断的边、纯推断的分支、阈值为空的数值条件。"""
    graph = to_plain(get(result, "graph")) or {}
    conditions = list(graph.get("conditions") or [])
    return {
        "model_only_edges": sum(1 for e in graph.get("edges") or [] if e.get("model_only")),
        "model_only_branches": sum(1 for b in (get(result, "branches") or []) if get(b, "kind") == "model_only"),
        "null_threshold_conditions": sum(1 for c in conditions if c.get("kind") == "numeric" and c.get("threshold") is None),
        "no_chain": bool(get(result, "no_chain")),
    }


def research_metrics(draft: Any, final: Any, web: dict | None) -> dict:
    """第 1 轮（研究 loop 存下的草稿）和最终结果（补查后重跑）的缺口数，加上每轮拿到的片段数和查询数。

    没触发补查时，最终结果就是用同一批资料重跑，数字应当和第 1 轮一样。只报数字。
    """
    web = web or {}
    rounds = web.get("rounds") or ([web] if web else [])
    followup = web.get("followup") or {}
    return {
        "round1": gap_counts(draft) if draft is not None else None,
        "final": gap_counts(final),
        "excerpts_by_round": [r.get("excerpts") for r in rounds],
        "queries_by_round": [r.get("queries") or [] for r in rounds],
        "followup_triggered": bool(followup.get("triggered")),
        "followup_reason": followup.get("reason"),
        "gaps": len(followup.get("gaps") or []),
    }


# ---- 给 LLM judge 看的输出摘要 -----------------------------------------------------

_COND_KEYS = ("id", "claim_id", "kind", "predicate", "series", "source", "comparator", "threshold", "threshold_note",
              "anchor", "deadline", "observation_window", "rule")


def output_digest(out: Any, evidence: Any = None, packs: list | None = None, extra_ids: set | None = None) -> dict:
    """一次 Inspect 结果的精简版：图、计划、分支类别，以及被引用（和案例点名要回应）的片段原文。"""
    graph = to_plain(get(out, "graph")) or {}
    plans = [to_plain(p) for p in (get(out, "proposals") or [])]
    wanted = set(cited_excerpts(out)) | set(extra_ids or ())
    texts = {}
    if evidence is not None and packs and wanted:
        for p in packs:
            try:
                for x in evidence.load_pack(p):
                    if x["excerpt_id"] in wanted:
                        texts[x["excerpt_id"]] = {k: x.get(k) for k in ("text", "stance", "date", "source")}
            except (FileNotFoundError, KeyError):
                continue
    return {
        "no_chain": bool(get(out, "no_chain")), "no_chain_reason": get(out, "no_chain_reason"),
        "nodes": [{k: n.get(k) for k in ("id", "role", "statement", "evidence_status")} for n in graph.get("nodes") or []],
        "edges": [{"from": e.get("from"), "to": e.get("to"), "sign": e.get("sign"), "mechanism": e.get("mechanism"),
                   "model_only": bool(e.get("model_only")),
                   "evidence": [{"excerpt_id": ev.get("excerpt_id"), "stance": ev.get("stance"), "supports": ev.get("supports"),
                                 "rebuttal": ev.get("rebuttal")} for ev in e.get("evidence") or []]}
                  for e in graph.get("edges") or []],
        "plans": [{"terminal_id": p.get("terminal_id"), "direction": p.get("direction"), "gate": p.get("gate"),
                   "key_dependency": p.get("key_dependency"), "exit_logic": p.get("exit_logic"),
                   "user_judgment": {k: (p.get("user_judgment") or {}).get(k) for k in
                                     ("original_statement", "clarified_statement", "requires_user_confirmation")},
                   "entry_conditions": [{k: c.get(k) for k in _COND_KEYS} for c in p.get("entry_conditions") or []],
                   "exit_conditions": [{k: c.get(k) for k in _COND_KEYS} for c in p.get("exit_conditions") or []]}
                  for p in plans],
        "branches": [{"terminal_id": get(b, "terminal_id"), "kind": get(b, "kind")} for b in (get(out, "branches") or [])],
        "excerpts": texts,
    }
