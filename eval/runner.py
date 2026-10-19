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
from eval.loader import FIXTURES_DIR, load_all_cases, load_fixture, load_json
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
        "failure_types": [], "retrieval": None, "checks": [], "notes": [],
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


class MissingField(KeyError):
    """核心返回体缺了 eval 依赖的字段。不能当成「没有」处理，否则会静默通过。"""


_MISSING = object()


def read_proposals(out: Any, stage: str) -> list:
    """方案 B：每个 terminal 一份计划，返回体里是 `proposals` 列表（没有时是 []）。

    显式读这个字段：字段缺失、或还是旧的单数 `proposal`，直接抛 MissingField（run_case 记 ERROR），
    不能当成「没有提案」——旧写法 `get(out, "proposal") is None` 在字段改名后会恒为真。
    """
    value = get(out, "proposals", _MISSING)
    if value is _MISSING:
        legacy = " （返回体里还是旧的单数 proposal）" if get(out, "proposal", _MISSING) is not _MISSING else ""
        raise MissingField(f"{stage}: 返回体没有 proposals 字段{legacy}")
    if not isinstance(value, (list, tuple)):
        raise MissingField(f"{stage}: proposals 应该是列表，实际是 {type(value).__name__}")
    return list(value)


def _plan_label(plan: Any) -> str:
    return str(get(plan, "terminal_id") or "?")


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


# ---- 资料包 --------------------------------------------------------------------

def fixture_packs() -> dict[str, dict]:
    """eval/fixtures 下的合成资料包（顶层就是 pack，或 golden 文件里的 evidence_pack 字段）。"""
    found: dict[str, dict] = {}
    for f in sorted(FIXTURES_DIR.glob("*.json")):
        data = load_json(f)
        for pack in (data, data.get("evidence_pack") if isinstance(data, dict) else None):
            if isinstance(pack, dict) and "pack_id" in pack and "excerpts" in pack:
                found.setdefault(pack["pack_id"], {k: v for k, v in pack.items() if not k.startswith("_")})
    return found


PACK_SOURCES = ("real", "synthetic")


def _is_synthetic(evidence: Any, pack_id: str) -> bool:
    pack = evidence.pack(pack_id) if hasattr(evidence, "pack") else None
    return bool(get(pack, "synthetic", False))


def prepare_packs(case: dict, evidence: Any, source: str = "real") -> tuple[list[str], list[str]]:
    """本案例实际可用的 pack 列表 + 说明。两个组用同一份列表，保证「同一资料」。

    一次运行只用一种来源（source 由 run_all 统一传入），因为真实包复用了 sc-001…、hz-001… 这些 id，
    含义和立场都和 eval/fixtures 里的占位片段不同：
    - real：只用真实 pack；缺了就不带并写明，不拿合成包补；provider 里若已是合成包也不用。
    - synthetic：一律注入 eval/fixtures 里同 pack_id 的合成包（覆盖真实包），只验证流程；检索命中不判。
    """
    if source not in PACK_SOURCES:
        raise ValueError(source)
    packs, notes = [], []
    wanted = case.get("input", {}).get("evidence_packs", [])
    if evidence is None:
        return [], [f"没有注入 Evidence Provider，资料包 {wanted} 都没带"] if wanted else []
    synthetic = fixture_packs() if source == "synthetic" else {}
    for pid in wanted:
        if source == "synthetic":
            if pid in synthetic and hasattr(evidence, "register"):
                evidence.register(synthetic[pid])
                packs.append(pid)
                notes.append(f"资料包 {pid} 用 eval/fixtures 里的合成占位片段（只验证流程，不验证推理；检索命中不判）")
            else:
                notes.append(f"资料包 {pid} 没有可注入的合成版本，本轮两个组都不带它")
            continue
        try:
            evidence.load_pack(pid)
        except (FileNotFoundError, KeyError):
            notes.append(f"资料包 {pid} 不存在，本轮两个组都不带它（real 模式不拿合成包补）")
            continue
        if _is_synthetic(evidence, pid):
            notes.append(f"资料包 {pid} 在 provider 里是合成包，real 模式不用它")
            continue
        packs.append(pid)
    return packs, notes


def _structured_ok(res: dict, stage: str, out: Any) -> bool:
    """核心入口在重试上限内没产出合法输出时返回 ok=False + errors；记成结构化失败。"""
    if get(out, "ok", True) is False:
        errs = get(out, "errors") or []
        res["checks"].append(check(f"{stage}:structured_output", "—", False,
                                   "; ".join(map(str, errs))[:300], "structured_failure"))
        return False
    return True


# ---- pipeline 组 --------------------------------------------------------------

def _run_pipeline(case: dict, res: dict, ep: Entrypoints, reasoner: Any, evidence: Any,
                  pack_source: str = "real") -> None:
    packs, notes = prepare_packs(case, evidence, pack_source)
    res["notes"] += notes
    kw = {"reasoner": reasoner, "evidence": evidence, "packs": packs}
    exp = case["expected"]
    inp = case["input"]

    if case["type"] == "causalt5k":
        out = ep.inspect(inp["event"], inp.get("target"), material=inp["material"], judgment_only=True, **kw)
        if not _structured_ok(res, "judge", out):
            res["actual"] = {"label": None}
            return
        judgment = get(out, "judgment") or {}
        label = (get(judgment, "label") or "").upper() or None
        res["actual"] = {"label": label, "rationale": get(judgment, "rationale"), "no_chain": get(out, "no_chain")}
        ok, types = scoring.judge_label(exp["label"], label, case.get("probe"))
        res["checks"].append(check("label_matches_gold", "E4", ok, f"gold={exp['label']} pred={label}"))
        res["failure_types"] += types
        plans = read_proposals(out, "inspect(judgment_only)")
        res["checks"].append(check("no_proposal", "E1", plans == [],
                                   "CausalT5k 只出因果判断" if not plans else f"出了 {len(plans)} 份计划",
                                   "unexpected_proposal"))
        return

    if case["entry"] == "fork":
        _run_fork(case, res, ep, kw)
        return

    observations: list[str] = []
    if case["entry"] == "discover":
        d = ep.discover(inp["event"], None, **kw)
        if not _structured_ok(res, "discover", d):
            return
        cands = list(get(d, "candidates") or [])
        observations += list(get(d, "observations") or [])
        labels = [get(c, "label") for c in cands]
        res["actual"] = {"candidates": len(cands), "candidate_labels": labels, "abstained": bool(get(d, "abstained"))}
        if exp.get("abstain"):
            ok = len(cands) == 0 or all(l == "not_recommended" for l in labels)
            res["checks"].append(check("abstained_or_only_not_recommended", "E4", ok,
                                       f"候选 {len(cands)} 个：{labels}", "no_abstain"))
            plans = read_proposals(d, "discover")
            res["checks"].append(check("no_proposal", "E4", plans == [],
                                       "" if not plans else f"弃权却出了 {len(plans)} 份计划", "unexpected_proposal"))
            return
        lo, hi = exp.get("candidates_min", 0), exp.get("candidates_max", 3)
        res["checks"].append(check("candidate_count", "Discovery", lo <= len(cands) <= hi,
                                   f"{len(cands)} 个（期望 {lo}–{hi}）", "wrong_candidate_count"))
        allowed = set(exp.get("candidate_labels_allowed", []))
        if allowed:
            res["checks"].append(check("candidate_labels", "Discovery", all(l in allowed for l in labels),
                                       str(labels), "wrong_candidate_count"))
        if not cands:
            if case.get("then") == "inspect":
                res["checks"].append(check("flow_reached_proposal", "E2", False,
                                           f"Discover 弃权（{get(d, 'abstain_reason') or '无理由'}），没有进入 Inspect，"
                                           "进场判定与阈值检查都没跑；弃权是否合理由人工判断", "missing_proposal"))
            return
        pick = next((c for c in cands if get(c, "label") == "grounded"), cands[0])
        # 传整个候选，不只传 id：Inspect 要知道用户选中的方向是什么
        out = ep.inspect(inp["event"], None, candidate_id=get(pick, "id"), candidate=scoring.to_plain(pick), **kw)
    else:
        out = ep.inspect(inp["event"], inp.get("target"), **kw)
    if not _structured_ok(res, "inspect", out):
        return

    observations += list(get(out, "observations") or [])
    plans = read_proposals(out, "inspect")
    no_chain = bool(get(out, "no_chain"))
    all_conditions = [c for p in plans for c in _conditions_of(p)]
    res["actual"].update({
        "no_chain": no_chain,
        "plans": [{"terminal_id": _plan_label(p), "gate": get(p, "gate"), "conditions": len(_conditions_of(p)),
                   "status": get(p, "status"), "support_status": get(p, "support_status")} for p in plans],
        "branch_kinds": {str(get(b, "terminal_id")): get(b, "kind") for b in (get(out, "branches") or [])},
        "conditions": len(all_conditions),
    })

    if exp.get("chain_or_no_chain"):
        ok = no_chain or get(out, "graph") is not None
        res["checks"].append(check("chain_or_no_chain", "E1", ok, failure_type="missing_proposal"))
    if no_chain:
        res["checks"].append(check("no_chain_has_no_plans", "E1", plans == [],
                                   "" if not plans else f"no_chain 却出了 {len(plans)} 份计划", "unexpected_proposal"))
    else:
        res["checks"].append(check("proposal_present", "E2", bool(plans), failure_type="missing_proposal"))
        if "gate" in exp:
            # 案例里的 gate 期望指每一份计划的 gate 都等于它
            wrong = [f"{_plan_label(p)}={get(p, 'gate')}" for p in plans if get(p, "gate") != exp["gate"]]
            res["checks"].append(check("gate_per_plan", "E2", bool(plans) and not wrong,
                                       f"期望每份 {exp['gate']}；不符：{wrong}" if wrong else "", "gate_wrong"))
        # 条件类型按整张图的计划合起来看（并列受益的计划可以用不同类型的条件）
        res["checks"] += _kind_checks(case, all_conditions)
        # null 阈值说明、编造阈值逐份计划检查
        for p in plans:
            for c in _threshold_checks(case, _conditions_of(p)):
                c["name"] = f"{_plan_label(p)}:{c['name']}"
                res["checks"].append(c)
        if exp.get("user_judgment_requires_confirmation"):
            missing = [_plan_label(p) for p in plans
                       if not get(get(p, "user_judgment") or {}, "requires_user_confirmation")]
            res["checks"].append(check("user_judgment_confirmation_per_plan", "E2", bool(plans) and not missing,
                                       f"没要求确认的计划：{missing}" if missing else "", "no_user_confirmation"))

    if pack_source == "synthetic":
        return  # key_excerpts 是真实包的 id，和占位片段撞号，比了也没有意义
    res["retrieval"] = scoring.retrieval_hit(exp.get("key_excerpts", []), observations)
    if res["retrieval"] is not None and not res["retrieval"]["hit"]:
        res["failure_types"].append("retrieval_miss")
        res["checks"].append(check("retrieval_hit", "E1", False, f"缺：{res['retrieval']['missing']}", "retrieval_miss"))


def _run_fork(case: dict, res: dict, ep: Entrypoints, kw: dict) -> None:
    fixture_base = {k: v for k, v in load_fixture(case["input"]["base_graph_fixture"]).items() if not k.startswith("_")}
    parts = []
    for fx_name in case["input"]["forks"]:
        fx = load_fixture(fx_name)
        tag = fx["op"]["kind"]
        fork_kw = dict(kw)
        if case["input"].get("fork_pack_fixture"):
            # golden 图引用的是占位片段 id：只配 c1_evidence_pack，不带真实包（同号不同义）
            fork_kw["packs"] = []
            fork_kw["pack"] = {k: v for k, v in load_fixture(case["input"]["fork_pack_fixture"]).items()
                               if not k.startswith("_")}
        out = ep.fork(copy.deepcopy(fixture_base), copy.deepcopy(fx["op"]), **fork_kw)
        if not _structured_ok(res, tag, out):
            parts.append(f"{tag}: 结构化失败")
            continue
        new = scoring.to_plain(get(out, "graph"))
        # 哈希比对两边都用核心的规范形式：基线取核心回传的 base_graph（parse_graph(d).dump()），
        # 不直接哈希手写 fixture，否则省略的默认字段会被误判成改动
        base = scoring.to_plain(get(out, "base_graph")) or fixture_base
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
                                   base_back is not None and get(base_back, "version") == fixture_base["version"],
                                   failure_type="baseline_retained_fail"))
        assessment = get(get(out, "scenario") or {}, "assessment") or {}
        impact = scoring.expected_impact(assessment, fx["expected_challenged"])
        detail = f"缺 {impact['missing']}；多 {impact['unexpected']}"
        res["checks"].append(check(f"{tag}:challenged_matches_golden", "E3", impact["passed"], detail,
                                   "missed_impact" if impact["missing"] else "unexpected_impact"))
        parts.append(f"{tag}: challenged={impact['actual']}, 越界={len(ni['violations'])}")
    res["actual"] = {"summary": " | ".join(parts)}


# ---- baseline 组 --------------------------------------------------------------

BASELINE_INSTRUCTIONS = {  # 送进模型的文字一律英文（Mia 定）
    "causalt5k": "Using only the material below, decide whether this causal claim holds. Return JSON only: "
                 "{\"label\": \"YES\"|\"NO\"|\"AMBIGUOUS\", \"rationale\": \"...\"}",
    "discover": "Using only the evidence below, propose at most 3 trade directions worth researching, or abstain explicitly; "
                "if you propose directions, write entry conditions for the first one. Return JSON only: "
                "{\"abstained\": bool, \"candidates\": [{\"direction\": \"...\", \"label\": \"grounded\"|\"hypothesis\"|\"not_recommended\"}], "
                "\"conditions\": [{\"kind\": \"numeric\"|\"document\"|\"event\", \"series\": \"...\", \"threshold\": number|null, \"threshold_note\": \"...\"}]}",
    "inspect": "Using only the evidence below, check whether there is a plausible causal path from the event to the target instrument, "
               "and write entry conditions. Return JSON only: "
               "{\"no_chain\": bool, \"chain\": [\"...\"], \"conditions\": [{\"kind\": \"numeric\"|\"document\"|\"event\", \"series\": \"...\", \"threshold\": number|null, \"threshold_note\": \"...\"}]}",
}


def build_baseline_prompt(case: dict, evidence: Evidence | None, packs: list[str] | None = None) -> str:
    inp = case["input"]
    kind = "causalt5k" if case["type"] == "causalt5k" else case["entry"]
    lines = [BASELINE_INSTRUCTIONS[kind], "", f"Event / claim: {inp['event']}"]
    if inp.get("target"):
        lines.append(f"Target instrument: {inp['target']}")
    if inp.get("material"):
        lines += ["", "Material:", inp["material"]]
    for pack in (packs if packs is not None else inp.get("evidence_packs", [])):
        if pack == "web" or evidence is None:
            continue
        lines += ["", f"Evidence pack {pack}:"]
        for ex in evidence.load_pack(pack):
            lines.append(f"[{ex['excerpt_id']}] {ex.get('date', '')} {ex.get('source', '')} ({ex.get('stance', '')}): {ex['text']}")
    return "\n".join(lines)


def single_prompt(reasoner: Any, prompt: str) -> str:
    """同一个 reasoner 做单次 prompt：优先 single_prompt；没有时退回 complete（无 schema 约束）。"""
    if hasattr(reasoner, "single_prompt"):
        return reasoner.single_prompt(prompt)
    out = reasoner.complete(stage="baseline", system="", user=prompt, schema={"type": "object"})
    return get(out, "text", out)


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.index("{"):]
    start, end = text.index("{"), text.rindex("}") + 1
    return json.loads(text[start:end])


def _run_baseline(case: dict, res: dict, reasoner: Reasoner, evidence: Evidence | None,
                  pack_source: str = "real") -> None:
    if case["entry"] == "fork":
        res["status"] = "N/A"
        res["actual"] = {"summary": "单次 prompt 没有可比的写范围"}
        res["human_review"] = []
        return
    packs, notes = prepare_packs(case, evidence, pack_source)
    res["notes"] += notes
    raw = single_prompt(reasoner, build_baseline_prompt(case, evidence, packs))
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
    if case.get("then") == "inspect" and not cands:
        res["checks"].append(check("flow_reached_proposal", "E2", False,
                                   "弃权，没有给出方向与进场条件；弃权是否合理由人工判断", "missing_proposal"))
        return
    if out.get("no_chain"):
        return  # 和 pipeline 组一致：no_chain 时不查条件，理由归人工复核
    res["checks"] += _kind_checks(case, conditions)
    res["checks"] += _threshold_checks(case, conditions)


# ---- 入口 --------------------------------------------------------------------

def run_case(case: dict, group: str, *, reasoner: Any, evidence: Any = None,
             entrypoints: Entrypoints | None = None, pack_source: str = "real") -> dict:
    if group not in GROUPS:
        raise ValueError(group)
    res = _result(case, group)
    res["pack_source"] = pack_source
    try:
        if group == "pipeline":
            if entrypoints is None:
                raise RuntimeError("pipeline 组需要注入核心入口（或用 CLI 懒加载 catalyst）")
            _run_pipeline(case, res, entrypoints, reasoner, evidence, pack_source)
        else:
            _run_baseline(case, res, reasoner, evidence, pack_source)
    except Exception as exc:  # noqa: BLE001 —— 单个案例出错不影响其他案例
        res["status"] = "ERROR"
        res["failure_types"].append("error")
        res["actual"] = {"error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc(limit=3)}
    return _finish(res)


def run_all(cases: list[dict], groups=GROUPS, *, reasoner: Any, evidence: Any = None,
            entrypoints: Entrypoints | None = None, pack_source: str = "real") -> list[dict]:
    """一次运行统一一种资料来源（pack_source），两个组、所有案例都一样。"""
    if pack_source not in PACK_SOURCES:
        raise ValueError(pack_source)
    return [run_case(c, g, reasoner=reasoner, evidence=evidence, entrypoints=entrypoints, pack_source=pack_source)
            for g in groups for c in cases]


def main(argv: list[str] | None = None) -> None:  # pragma: no cover —— 需要核心与真实 reasoner
    """真实运行。模型由核心的 CATALYST_MODEL / CATALYST_EFFORT 决定（默认 claude-opus-5-5 / high）。

    例：CATALYST_MODEL=claude-haiku-5-5 python -m eval.runner --case T1 --record eval/out/haiku
    --record 会把每次模型请求（含 baseline 的单次 prompt）录进 <DIR>/cassette.jsonl，之后可零成本回放。
    """
    from pathlib import Path

    ap = argparse.ArgumentParser(description="跑 eval 案例（需要核心包与真实 reasoner）")
    ap.add_argument("--group", action="append", choices=GROUPS)
    ap.add_argument("--case", action="append")
    ap.add_argument("--out", default=None, help="results.json 路径；默认 <record 目录>/results.json 或 eval/out/results.json")
    ap.add_argument("--record", metavar="DIR", help="录制目录（cassette.jsonl、results.json、report.md）")
    ap.add_argument("--today", help="条件判定用的日期，默认今天")
    ap.add_argument("--packs", choices=PACK_SOURCES, default="real",
                    help="资料来源：real 只用 packs/ 下的真实包（默认）；synthetic 一律用 eval/fixtures 的占位片段。一次运行只用一种")
    ap.add_argument("--replay", metavar="DIR", help="按 <DIR>/cassette.jsonl 零成本回放（只重新判分，不调模型）")
    args = ap.parse_args(argv)

    import catalyst.evidence as evidence_mod  # noqa: WPS433
    import catalyst.reasoner as reasoner_mod  # noqa: WPS433
    from eval import report

    if args.replay:
        out_dir = Path(args.replay)
        reasoner = reasoner_mod.ReplayReasoner(out_dir / "cassette.jsonl")
        prev = out_dir / "results.json"
        model = (json.loads(prev.read_text(encoding="utf-8"))[0].get("model", "unknown") + "（回放）") \
            if prev.exists() else reasoner.name
    else:
        reasoner = reasoner_mod.default_reasoner()
        model = getattr(reasoner, "name", "unknown")
        out_dir = Path(args.record) if args.record else Path("eval/out")
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.record:
        reasoner = reasoner_mod.RecordingReasoner(reasoner, out_dir / "cassette.jsonl")
    entrypoints = load_core_entrypoints()
    if args.today:
        import functools
        ep = entrypoints
        cfg = {"today": args.today}

        class _WithToday:
            discover = staticmethod(functools.partial(ep.discover, config=cfg))
            inspect = staticmethod(functools.partial(ep.inspect, config=cfg))
            fork = staticmethod(functools.partial(ep.fork, config=cfg))
        entrypoints = _WithToday
    results = run_all(load_all_cases(args.case), args.group or GROUPS,
                      reasoner=reasoner, evidence=evidence_mod.default_provider(), entrypoints=entrypoints,
                      pack_source=args.packs)
    for r in results:
        r["model"] = model
    out = Path(args.out) if args.out else out_dir / "results.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    md = report.render_report(results, title=f"Catalyst eval 逐例报告（{model}）")
    (out.parent / "report.md").write_text(md, encoding="utf-8")
    print(f"wrote {len(results)} results → {out}；report → {out.parent / 'report.md'}")
    for r in results:
        print(f"  {r['case_id']:3} {r['group']:8} {r['status']:15} {','.join(r['failure_types']) or '-'}")


if __name__ == "__main__":  # pragma: no cover
    main()
