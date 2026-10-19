"""R 层回测：时点资料包、强制离线、污染检查、泄漏检查、按事后真相回判条件。

回测判的是「关键依赖和条件放到现实里对不对」，不是收益。三处泄漏：
1. 联网：R 层强制离线，请求联网直接报错（BacktestOnlineError）。
2. 资料包：只把 allowed_excerpts 组成本轮资料包；事后片段只在这里判分时用。
3. 模型记忆：关不掉，跑前问一句（contamination_probe），命中 contamination_markers 的标「受污染」，单独报。

不 import catalyst：条件判定函数由调用方注入（CLI 里用 catalyst.conditions.evaluate）。
"""
from __future__ import annotations

import copy
import datetime as _dt
from typing import Any, Callable

from eval.checks import cited_excerpts, plan_conditions
from eval.scoring import check, get

ConditionEvaluator = Callable[[dict, list, _dt.date], str]


class BacktestOnlineError(RuntimeError):
    """回测请求了联网：会泄漏决策日之后的信息，直接拒绝。"""


class PackAssemblyError(RuntimeError):
    """时点资料包组不出来（片段不在资料包里，或 provider 不能注册新包）。"""


def is_backtest(case: dict) -> bool:
    return case.get("type") == "backtest" or case.get("layer") == "R"


def refuse_online(case: dict, online: bool) -> None:
    if online and (case.get("online_locked") or is_backtest(case)):
        raise BacktestOnlineError(f"{case['id']}: backtests must run offline; refusing --online (it would leak information after {case.get('as_of')})")


# ---- 资料包 ---------------------------------------------------------------------

def filtered_pack(evidence: Any, pack_id: str, *, keep: set[str] | None = None, drop: set[str] = frozenset(),
                  tag: str) -> str:
    """从一个资料包里只留 keep（None 表示全部）、去掉 drop，注册成新包，返回新 pack_id。"""
    if not hasattr(evidence, "register"):
        raise PackAssemblyError("the Evidence Provider cannot register packs, so the point-in-time pack cannot be built")
    excerpts = [x for x in evidence.load_pack(pack_id)
                if (keep is None or x["excerpt_id"] in keep) and x["excerpt_id"] not in drop]
    if keep is not None:
        missing = keep - {x["excerpt_id"] for x in excerpts} - set(drop)
        if missing:
            raise PackAssemblyError(f"{pack_id} does not contain {sorted(missing)}")
    new_id = f"{pack_id}@{tag}"
    evidence.register({"pack_id": new_id, "synthetic": False, "excerpts": copy.deepcopy(excerpts),
                       "note": f"assembled by eval: subset of {pack_id} ({tag})"})
    return new_id


def point_in_time_packs(case: dict, evidence: Any, drop: set[str] = frozenset()) -> tuple[list[str], set[str]]:
    """按 allowed_excerpts 组时点资料包。返回（本轮 pack_id 列表, 实际放进去的片段 id）。"""
    allowed = set(case["allowed_excerpts"]) - set(drop)
    packs, placed = [], set()
    for pid in case["input"]["evidence_packs"]:
        own = {x["excerpt_id"] for x in evidence.load_pack(pid)} & allowed
        if own:
            packs.append(filtered_pack(evidence, pid, keep=own, tag=f"asof-{case['as_of']}"))
            placed |= own
    missing = allowed - placed
    if missing:
        raise PackAssemblyError(f"{case['id']}: allowed_excerpts lists excerpts missing from the packs: {sorted(missing)}")
    return packs, placed


# ---- 污染检查 -------------------------------------------------------------------

def contamination_probe(case: dict, ask: Callable[[str], str]) -> dict:
    """不给资料，问模型结局。命中任一标记即视为受污染（只是提示，原文留给人工看）。"""
    question = case.get("contamination_probe")
    if not question:
        return {"ran": False}
    answer = ask(question) or ""
    low = answer.lower()
    hits = [m for m in case.get("contamination_markers", []) if m.lower() in low]
    return {"ran": True, "question": question, "answer": answer[:800], "markers_hit": hits, "contaminated": bool(hits)}


# ---- 泄漏检查 -------------------------------------------------------------------

def leak_checks(case: dict, out: Any, allowed: set[str]) -> list[dict]:
    checks = []
    in_context = set(get(out, "observations") or [])
    extra = sorted(in_context - allowed)
    checks.append(check("backtest_pack_point_in_time", "Backtest", not extra,
                        f"excerpts outside the point-in-time pack were in context: {extra}" if extra else "", "leak"))
    cited = cited_excerpts(out)
    outside = sorted(set(cited) - allowed)
    urls = sorted({ev.get("url") for e in (get(get(out, "graph") or {}, "edges") or [])
                   for ev in (e.get("evidence") or []) if ev.get("url") and ev.get("excerpt_id") not in allowed})
    bad = outside + urls
    checks.append(check("only_allowed_excerpts_cited", "Backtest", not bad,
                        f"cited excerpts or URLs outside the point-in-time pack: {bad}" if bad else "", "leak"))
    return checks


# ---- 事后回判 -------------------------------------------------------------------

def _d(v: str) -> _dt.date:
    return _dt.date.fromisoformat(v)


def _observations_for(cond: dict, case: dict) -> list[dict]:
    """把事后观测按序列名（含别名）对到这条条件上。对不上返回 []。"""
    names = {str(x).lower() for x in (get(cond, "series"), get(cond, "source")) if x}
    aliases = case["outcome"].get("series_aliases", {})
    matched = []
    for obs in case["outcome"]["observations"]:
        keys = {obs["source"].lower(), *(a.lower() for a in aliases.get(obs["source"], []))}
        if names & keys:
            o = copy.deepcopy(obs)
            o["source"] = get(cond, "series") or get(cond, "source")
            o.pop("note", None)
            matched.append(o)
    return matched


def _status(cond: dict, case: dict, evaluate: ConditionEvaluator, on: str) -> tuple[str, bool]:
    obs = _observations_for(cond, case)
    return (evaluate(cond, obs, _d(on)) if obs else "unknown"), bool(obs)


def entered_by(plan: Any, case: dict, evaluate: ConditionEvaluator, on: str) -> tuple[bool, list[str]]:
    """进场 AND：每一条进场条件在 on 当天都判定为 met 才算进场；unknown 不算（系统会一直先别动）。"""
    conds = plan_conditions(plan, "entry")
    statuses = [_status(c, case, evaluate, on) for c in conds]
    return bool(conds) and all(s == "met" for s, _ in statuses), [s for s, _ in statuses]


def exited_by(plan: Any, case: dict, evaluate: ConditionEvaluator, on: str) -> tuple[bool, list[str]]:
    conds = plan_conditions(plan, "exit")
    statuses = [_status(c, case, evaluate, on)[0] for c in conds]
    if not conds:
        return False, []
    hit = all(s == "met" for s in statuses) if get(plan, "exit_logic") == "ALL" else any(s == "met" for s in statuses)
    return hit, statuses


def grade_outcome(case: dict, plans: list, evaluate: ConditionEvaluator) -> tuple[list[dict], dict]:
    """按 expected.backtest.pass_if_any 回判每份计划；任一规则成立即该计划通过，全部计划通过才算通过。

    另外单独记「条件能不能被事后数据判定」：一份计划没有一条条件对得上事后观测，记 condition_undecidable。
    """
    rules = case["expected"]["backtest"].get("pass_if_any", [])
    per_plan, failed, undecidable = [], [], []
    for p in plans:
        tid = str(get(p, "terminal_id") or "?")
        results = {}
        for rule in rules:
            kind, on = rule.split(":", 1)
            if kind == "entry_not_met_by":
                entered, statuses = entered_by(p, case, evaluate, on)
                results[rule] = {"pass": not entered, "statuses": statuses}
            elif kind == "exit_met_by":
                hit, statuses = exited_by(p, case, evaluate, on)
                results[rule] = {"pass": hit, "statuses": statuses}
            else:
                raise ValueError(f"unknown grading rule: {rule}")
        ok = any(r["pass"] for r in results.values()) if results else False
        decidable = any(_observations_for(c, case) for c in plan_conditions(p))
        per_plan.append({"terminal_id": tid, "pass": ok, "rules": results, "decidable": decidable})
        if not ok:
            failed.append(tid)
        if not decidable:
            undecidable.append(tid)
    checks = [
        check("backtest_outcome", "Backtest", bool(plans) and not failed,
              f"plans that fail against the real outcome: {failed}" if failed else ("" if plans else "no plans to grade"),
              "backtest_wrong_call"),
        check("backtest_conditions_decidable", "Backtest", bool(plans) and not undecidable,
              f"plans whose conditions match no outcome data and cannot be decided: {undecidable}" if undecidable else "",
              "condition_undecidable"),
    ]
    return checks, {"rules": rules, "plans": per_plan}
