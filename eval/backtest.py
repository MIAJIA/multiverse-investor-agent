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
#
# 模型看不到事后数据，不可能猜中我们给事后序列起的名字。所以对照分两步：
# 1. 名字或别名完全一致（series_aliases）；
# 2. 否则用事后数据项的 match 关键词去匹配条件的 series、source、rule 文本，取命中最多的一项；
#    只在同类数据里找（数值条件对数值序列，事件 / 文件条件对事件序列）。
# 一条都对不上的条件不算失败：结果是「判定不了」，进人工复核，问「这条条件能否用某某事后数据判定」。
# 只有对上了、并且按真实结局判错了（例如该先别动时进了场），才算 FAIL。

def _d(v: str) -> _dt.date:
    return _dt.date.fromisoformat(v)


def _obs_kind(obs: dict) -> str:
    if obs.get("kind"):
        return "numeric" if obs["kind"] == "numeric" else "event"
    has_value = any(r.get("value") is not None for r in obs.get("records", []))
    return "numeric" if has_value else "event"


def _cond_kind(cond: dict) -> str:
    return "numeric" if get(cond, "kind") == "numeric" else "event"


def match_observation(cond: dict, case: dict) -> tuple[dict | None, str]:
    """返回（改好 source 的事后观测, 匹配方式）。对不上返回 (None, "")。"""
    key = get(cond, "series") or get(cond, "source")
    if not key:
        return None, ""
    observations = [o for o in case["outcome"]["observations"] if _obs_kind(o) == _cond_kind(cond)]
    names = {str(x).lower() for x in (get(cond, "series"), get(cond, "source")) if x}
    aliases = case["outcome"].get("series_aliases", {})
    chosen, how = None, ""
    for obs in observations:
        if names & {obs["source"].lower(), *(a.lower() for a in aliases.get(obs["source"], []))}:
            chosen, how = obs, "name"
            break
    if chosen is None:
        text = " ".join(str(x) for x in (get(cond, "series"), get(cond, "source"), get(cond, "rule")) if x).lower()
        best = 0
        for obs in observations:
            hits = sum(1 for k in obs.get("match", []) if k.lower() in text)
            if hits > best:
                chosen, best, how = obs, hits, "keywords"
    if chosen is None:
        return None, ""
    o = copy.deepcopy(chosen)
    o["source"] = key
    for k in ("note", "match", "kind"):
        o.pop(k, None)
    return o, f"{how}:{chosen['source']}"


def _status(cond: dict, case: dict, evaluate: ConditionEvaluator, on: str) -> str | None:
    """met / not_met / unknown；对不上任何事后数据时返回 None（判定不了）。"""
    obs, _ = match_observation(cond, case)
    return evaluate(cond, [obs], _d(on)) if obs else None


def entry_not_met(plan: Any, case: dict, evaluate: ConditionEvaluator, on: str) -> tuple[bool | None, list]:
    """进场 AND。True = 到 on 为止没进场；False = 进场了；None = 判定不了。

    对上了的条件里有一条不是 met（not_met 或 unknown），AND 就不成立，确定没进场；
    对上了的都是 met、但还有对不上的条件时，判定不了。
    """
    conds = plan_conditions(plan, "entry")
    statuses = [_status(c, case, evaluate, on) for c in conds]
    if not conds or any(st is not None and st != "met" for st in statuses):
        return True, statuses
    if all(st == "met" for st in statuses):
        return False, statuses
    return None, statuses


def exit_met(plan: Any, case: dict, evaluate: ConditionEvaluator, on: str) -> tuple[bool | None, list]:
    """离场。True = 到 on 为止触发了；False = 没触发；None = 判定不了。"""
    conds = plan_conditions(plan, "exit")
    statuses = [_status(c, case, evaluate, on) for c in conds]
    if not conds:
        return False, statuses
    if get(plan, "exit_logic") == "ALL":
        if any(st is not None and st != "met" for st in statuses):
            return False, statuses
        return (True if all(st == "met" for st in statuses) else None), statuses
    if any(st == "met" for st in statuses):
        return True, statuses
    return (False if all(st is not None for st in statuses) else None), statuses


def grade_outcome(case: dict, plans: list, evaluate: ConditionEvaluator) -> tuple[list[dict], dict, list[str]]:
    """按 expected.backtest.pass_if_any 回判每份计划。

    返回（检查, 明细, 人工复核项）。每份计划三种结果：pass（有一条规则确定成立）、
    fail（所有规则都确定不成立）、undetermined（有规则判定不了）。只有 fail 让案例 FAIL；
    undetermined 列进人工复核。
    """
    rules = case["expected"]["backtest"].get("pass_if_any", [])
    sources = [o["source"] for o in case["outcome"]["observations"]]
    per_plan, failed, review = [], [], []
    for p in plans:
        tid = str(get(p, "terminal_id") or "?")
        results = {}
        for rule in rules:
            kind, on = rule.split(":", 1)
            if kind == "entry_not_met_by":
                verdict, statuses = entry_not_met(p, case, evaluate, on)
            elif kind == "exit_met_by":
                verdict, statuses = exit_met(p, case, evaluate, on)
            else:
                raise ValueError(f"unknown grading rule: {rule}")
            results[rule] = {"verdict": verdict, "statuses": statuses}
        verdicts = [r["verdict"] for r in results.values()]
        outcome = "pass" if True in verdicts else ("fail" if verdicts and all(v is False for v in verdicts) else "undetermined")
        matches = {str(get(c, "id")): match_observation(c, case)[1] or None for c in plan_conditions(p)}
        unmatched = [cid for cid, m in matches.items() if m is None]
        conditions = [{k: get(c, k) for k in ("id", "kind", "predicate", "series", "source", "comparator", "threshold",
                                              "rule")} for c in plan_conditions(p)]
        per_plan.append({"terminal_id": tid, "outcome": outcome, "pass": outcome == "pass", "rules": results,
                         "matches": matches, "unmatched": unmatched, "decidable": outcome != "undetermined",
                         "conditions": conditions})
        if outcome == "fail":
            failed.append(tid)
        elif outcome == "undetermined":
            for c in plan_conditions(p):
                if str(get(c, "id")) in unmatched:
                    review.append(f"Backtest {case['id']} / {tid}: can condition {get(c, 'id')} "
                                  f"(\"{str(get(c, 'rule') or '')[:100]}\") be decided with the outcome data {sources}?")
    checks = [check("backtest_outcome", "Backtest", not failed,
                    f"plans that made the wrong call against the real outcome: {failed}" if failed else
                    ("" if plans else "no plans to grade"), "backtest_wrong_call")]
    return checks, {"rules": rules, "plans": per_plan}, review
