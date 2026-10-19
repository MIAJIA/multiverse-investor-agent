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

from eval import backtest as bt
from eval import scoring
from eval.checks import cited_excerpts, model_only_edge_count, research_metrics, scenario_checks
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
        "failure_types": [], "retrieval": None, "checks": [], "notes": [], "layer": layer_of(case),
        "human_review": list(case.get("human_review", [])),
    }


def layer_of(case: dict) -> str:
    """A 题目示例、B 关键场景、W 联网、R 回测、T 因果判断；P 探针由 eval.probes 另外标。"""
    if case.get("layer"):
        return case["layer"]
    return "T" if case.get("type") == "causalt5k" else "A"


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
        legacy = " (the response still has the old singular proposal)" if get(out, "proposal", _MISSING) is not _MISSING else ""
        raise MissingField(f"{stage}: response has no proposals field{legacy}")
    if not isinstance(value, (list, tuple)):
        raise MissingField(f"{stage}: proposals should be a list, got {type(value).__name__}")
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
                            f"conditions with invented thresholds: {fabricated}" if fabricated else "", "fabricated_threshold"))
    return checks


def _kind_checks(case: dict, conditions: list[dict]) -> list[dict]:
    kinds = {get(c, "kind") for c in conditions}
    checks = []
    for k in case["expected"].get("condition_kinds_required", []):
        checks.append(check(f"{k}_condition_present", "E2", k in kinds, failure_type="missing_condition_kind"))
    any_of = case["expected"].get("condition_kinds_required_any")
    if any_of:
        checks.append(check("document_or_event_condition_present", "E2", bool(kinds & set(any_of)),
                            f"kinds present: {sorted(k for k in kinds if k)}", "missing_condition_kind"))
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
        return [], [f"no Evidence Provider injected; packs {wanted} not loaded"] if wanted else []
    synthetic = fixture_packs() if source == "synthetic" else {}
    for pid in wanted:
        if source == "synthetic":
            if pid in synthetic and hasattr(evidence, "register"):
                evidence.register(synthetic[pid])
                packs.append(pid)
                notes.append(f"pack {pid} uses the synthetic placeholder excerpts from eval/fixtures (tests the flow, not the reasoning; key-excerpt check skipped)")
            else:
                notes.append(f"pack {pid} has no synthetic version to inject; both groups run without it")
            continue
        try:
            evidence.load_pack(pid)
        except (FileNotFoundError, KeyError):
            notes.append(f"pack {pid} does not exist; both groups run without it (real mode never substitutes a placeholder pack)")
            continue
        if _is_synthetic(evidence, pid):
            notes.append(f"pack {pid} is synthetic in the provider; real mode does not use it")
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

# Online cases (layer W) need the same wiring as the CLI and the API: round-1 web retrieval before the entry points,
# then the research loop passed to inspect. Each case keeps its frozen web packs under <record dir>/web_runs/<case>,
# so --replay reads them back without going online. main() sets these.
WEB_RUNS: dict = {"dir": None, "replay": False}


def _online_setup(case: dict, inp: dict, packs: list, config: dict, reasoner: Any, evidence: Any):
    """Returns (packs, research, web, store) for an online case, wired exactly like catalyst.__main__.cmd_run. The store
    is passed to inspect too, so the research loop freezes round 2 next to round 1 and --replay can read both."""
    import shutil
    from pathlib import Path

    from catalyst.__main__ import attach_web, research_for  # noqa: WPS433
    from catalyst.entrypoints import Config  # noqa: WPS433
    from catalyst.store import RunStore  # noqa: WPS433

    run_dir = Path(WEB_RUNS["dir"] or "eval/out/web_runs") / case["id"]
    replay_dir = run_dir if WEB_RUNS["replay"] else None
    if replay_dir is None and run_dir.exists():
        shutil.rmtree(run_dir)  # a new recording must not mix with frozen packs from an older run
    cfg = Config(packs=list(packs), online=True, today=config.get("today") or Config().today,
                 run_prefix=case["id"].lower())
    store = RunStore(run_dir)
    web = attach_web(inp["event"], inp.get("target"), cfg=cfg, ev=evidence, store=store, reasoner=reasoner,
                     replay_dir=replay_dir)
    research = research_for(inp["event"], inp.get("target"), cfg=cfg, ev=evidence, web=web, replay_dir=replay_dir)
    return list(cfg.packs), research, web, store

def _run_pipeline(case: dict, res: dict, ep: Entrypoints, reasoner: Any, evidence: Any,
                  pack_source: str = "real", online: bool = False, evaluate_condition: Any = None,
                  today: str | None = None) -> None:
    exp = case["expected"]
    inp = case["input"]
    bt.refuse_online(case, online)                    # 回测请求联网：直接报错
    backtest_case = bt.is_backtest(case)
    drop = set(case.get("_drop_excerpts", []))        # P 层「拿掉关键片段」的扰动
    allowed: set = set()
    if backtest_case:
        packs, allowed = bt.point_in_time_packs(case, evidence, drop)
        res["contamination"] = bt.contamination_probe(case, lambda q: single_prompt(reasoner, q))
    else:
        packs, notes = prepare_packs(case, evidence, pack_source)
        res["notes"] += notes
        if drop:
            packs = [bt.filtered_pack(evidence, p, drop=drop, tag="minus-" + "-".join(sorted(drop))) for p in packs]
    config = {"online": bool(online) and not backtest_case}
    today = case.get("as_of") or inp.get("today") or today
    if today:
        config["today"] = today
    research = web = web_store = None
    if config["online"]:
        packs, research, web, web_store = _online_setup(case, inp, packs, config, reasoner, evidence)
    kw = {"reasoner": reasoner, "evidence": evidence, "packs": packs, "config": config}
    ins_kw = {**kw, "research": research, "store": web_store} if research is not None else kw

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
                                   "CausalT5k produces a causal verdict only" if not plans else f"produced {len(plans)} plans",
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
                                       f"{len(cands)} candidates: {labels}", "no_abstain"))
            plans = read_proposals(d, "discover")
            res["checks"].append(check("no_proposal", "E4", plans == [],
                                       "" if not plans else f"abstained but produced {len(plans)} plans", "unexpected_proposal"))
            return
        lo, hi = exp.get("candidates_min", 0), exp.get("candidates_max", 3)
        res["checks"].append(check("candidate_count", "Discovery", lo <= len(cands) <= hi,
                                   f"{len(cands)} (expected {lo}-{hi})", "wrong_candidate_count"))
        allowed = set(exp.get("candidate_labels_allowed", []))
        if allowed:
            res["checks"].append(check("candidate_labels", "Discovery", all(l in allowed for l in labels),
                                       str(labels), "wrong_candidate_count"))
        if not cands:
            if case.get("then") == "inspect":
                res["checks"].append(check("flow_reached_proposal", "E2", False,
                                           f"Discover abstained ({get(d, 'abstain_reason') or 'no reason given'}), Inspect never ran; "
                                           "gate and threshold checks did not run; whether abstaining was right is for human review", "missing_proposal"))
            return
        pick = next((c for c in cands if get(c, "label") == "grounded"), cands[0])
        # 传整个候选，不只传 id：Inspect 要知道用户选中的方向是什么
        out = ep.inspect(inp["event"], None, candidate_id=get(pick, "id"), candidate=scoring.to_plain(pick), **ins_kw)
    else:
        out = ep.inspect(inp["event"], inp.get("target"), **ins_kw)
    if web is not None:
        from catalyst.__main__ import web_summary  # noqa: WPS433
        res["web"] = web_summary(web, research)
        # 补查前后对比：研究 loop 把第 1 轮的草稿存在 <store>/research/r1/inspect.result.json
        draft = None
        if web_store is not None:
            draft_path = web_store.root / "research" / "r1" / "inspect.result.json"
            if draft_path.exists():
                draft = json.loads(draft_path.read_text(encoding="utf-8"))
        res["research"] = research_metrics(draft, out, res["web"])
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
        "cited_excerpts": sorted(cited_excerpts(out)),
        "model_only_edges": model_only_edge_count(out),
    })
    res["checks"] += scenario_checks(case, out, plans, no_chain)
    if backtest_case:
        res["checks"] += bt.leak_checks(case, out, allowed)
        if evaluate_condition is None:
            res["notes"].append("no condition evaluator injected; outcome grading did not run")
        else:
            grade_checks, detail, review = bt.grade_outcome(case, plans, evaluate_condition)
            res["checks"] += grade_checks
            res["backtest"] = detail
            res["human_review"] += review  # 对不上事后数据的条件：人工判断，不算失败

    if exp.get("chain_or_no_chain"):
        ok = no_chain or get(out, "graph") is not None
        res["checks"].append(check("chain_or_no_chain", "E1", ok, failure_type="missing_proposal"))
    if no_chain:
        res["checks"].append(check("no_chain_has_no_plans", "E1", plans == [],
                                   "" if not plans else f"no_chain but produced {len(plans)} plans", "unexpected_proposal"))
    else:
        res["checks"].append(check("proposal_present", "E2", bool(plans), failure_type="missing_proposal"))
        if "gate" in exp:
            # 案例里的 gate 期望指每一份计划的 gate 都等于它
            wrong = [f"{_plan_label(p)}={get(p, 'gate')}" for p in plans if get(p, "gate") != exp["gate"]]
            res["checks"].append(check("gate_per_plan", "E2", bool(plans) and not wrong,
                                       f"expected {exp['gate']} for every plan; mismatched: {wrong}" if wrong else "", "gate_wrong"))
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
                                       f"plans that do not ask for confirmation: {missing}" if missing else "", "no_user_confirmation"))

    if pack_source == "synthetic" or backtest_case:
        return  # key_excerpts 是真实包的 id，和占位片段撞号，比了也没有意义
    res["retrieval"] = scoring.retrieval_hit(exp.get("key_excerpts", []), observations)
    if res["retrieval"] is not None and not res["retrieval"]["hit"]:
        res["failure_types"].append("retrieval_miss")
        res["checks"].append(check("retrieval_hit", "E1", False, f"missing: {res['retrieval']['missing']}", "retrieval_miss"))


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
        if case["input"].get("proposals_fixture"):
            fork_kw["proposals"] = copy.deepcopy(load_fixture(case["input"]["proposals_fixture"])["proposals"])
        out = ep.fork(copy.deepcopy(fixture_base), copy.deepcopy(fx["op"]), **fork_kw)
        if not _structured_ok(res, tag, out):
            parts.append(f"{tag}: structured failure")
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
        detail = f"missing {impact['missing']}; unexpected {impact['unexpected']}"
        res["checks"].append(check(f"{tag}:challenged_matches_golden", "E3", impact["passed"], detail,
                                   "missed_impact" if impact["missing"] else "unexpected_impact"))
        if case.get("expected", {}).get("plans_per_terminal"):
            plans = read_proposals(out, f"fork.{tag}")
            terminals = {n["id"] for n in (new or {}).get("nodes", []) if n.get("role") == "terminal"}
            got = [str(get(p, "terminal_id")) for p in plans]
            ok = sorted(got) == sorted(terminals)
            res["checks"].append(check(f"{tag}:fork_plans_per_terminal", "E3", ok,
                                       "" if ok else f"plans {sorted(got)} do not match terminals {sorted(terminals)} one to one",
                                       "missing_proposal"))
            flags = {str(get(p, "terminal_id")): {"approval_reset": get(p, "approval_reset"),
                                                  "rival_changed": get(p, "rival_changed")} for p in plans}
            res.setdefault("fork_plans", {})[tag] = flags
        parts.append(f"{tag}: challenged={impact['actual']}, out-of-scope writes={len(ni['violations'])}")
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
        res["actual"] = {"summary": "a single prompt has no comparable write scope"}
        res["human_review"] = []
        return
    packs, notes = prepare_packs(case, evidence, pack_source)
    res["notes"] += notes
    raw = single_prompt(reasoner, build_baseline_prompt(case, evidence, packs))
    try:
        out = _parse_json(raw)
    except (ValueError, json.JSONDecodeError):
        res["actual"] = {"raw": raw[:200]}
        res["checks"].append(check("parse", "—", False, "output is not valid JSON", "unparseable"))
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
        res["checks"].append(check("abstained_or_only_not_recommended", "E4", ok, f"{len(cands)} candidates", "no_abstain"))
        return
    if "candidates_min" in exp:
        lo, hi = exp["candidates_min"], exp.get("candidates_max", 3)
        res["checks"].append(check("candidate_count", "Discovery", lo <= len(cands) <= hi,
                                   f"{len(cands)}", "wrong_candidate_count"))
    if case.get("then") == "inspect" and not cands:
        res["checks"].append(check("flow_reached_proposal", "E2", False,
                                   "abstained, gave no direction or entry conditions; whether that was right is for human review", "missing_proposal"))
        return
    if out.get("no_chain"):
        return  # 和 pipeline 组一致：no_chain 时不查条件，理由归人工复核
    res["checks"] += _kind_checks(case, conditions)
    res["checks"] += _threshold_checks(case, conditions)


# ---- 入口 --------------------------------------------------------------------

def run_case(case: dict, group: str, *, reasoner: Any, evidence: Any = None,
             entrypoints: Entrypoints | None = None, pack_source: str = "real", online: bool = False,
             evaluate_condition: Any = None, today: str | None = None) -> dict:
    if group not in GROUPS:
        raise ValueError(group)
    res = _result(case, group)
    res["pack_source"] = pack_source
    try:
        if group == "pipeline":
            if entrypoints is None:
                raise RuntimeError("the pipeline group needs core entrypoints injected (or the CLI, which loads catalyst lazily)")
            _run_pipeline(case, res, entrypoints, reasoner, evidence, pack_source, online, evaluate_condition, today)
        elif bt.is_backtest(case) or case.get("run_variants") == ["online"] or case.get("_probe"):
            res["status"] = "N/A"
            res["actual"] = {"summary": "backtests, online-only cases and probes run in the pipeline group only"}
            res["human_review"] = []
        else:
            _run_baseline(case, res, reasoner, evidence, pack_source)
    except Exception as exc:  # noqa: BLE001 —— 单个案例出错不影响其他案例
        res["status"] = "ERROR"
        res["failure_types"].append("error")
        res["actual"] = {"error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc(limit=3)}
    return _finish(res)


def run_all(cases: list[dict], groups=GROUPS, *, reasoner: Any, evidence: Any = None,
            entrypoints: Entrypoints | None = None, pack_source: str = "real", online: bool = False,
            evaluate_condition: Any = None, today: str | None = None) -> list[dict]:
    """一次运行统一一种资料来源（pack_source），两个组、所有案例都一样。"""
    if pack_source not in PACK_SOURCES:
        raise ValueError(pack_source)
    return [run_case(c, g, reasoner=reasoner, evidence=evidence, entrypoints=entrypoints, pack_source=pack_source,
                     online=online, evaluate_condition=evaluate_condition, today=today)
            for g in groups for c in cases]


def load_core_condition_evaluator():
    """runner 侧另一个 import catalyst 的地方：回测用核心的条件判定回判事后真相。"""
    from catalyst.conditions import evaluate  # noqa: WPS433
    return evaluate


LAYERS = ("A", "B", "W", "R", "T", "P")


def cases_for_layers(layers: list[str]) -> list[dict]:
    from eval.loader import B_IDS, CAUSALT5K_IDS, CUSTOM_IDS, R_IDS, W_IDS, load_case
    ids = {"A": CUSTOM_IDS, "B": B_IDS, "W": W_IDS, "R": R_IDS, "T": CAUSALT5K_IDS}
    return [load_case(i) for layer in layers if layer != "P" for i in ids[layer]]


def main(argv: list[str] | None = None) -> None:  # pragma: no cover —— 需要核心与真实 reasoner
    """真实运行。模型由核心的 CATALYST_MODEL / CATALYST_EFFORT 决定；eval 一律用 claude-haiku-5-5（Mia 定）。

    例：CATALYST_MODEL=claude-haiku-5-5 python -m eval.runner --layer A --layer T --record eval/out/haiku
        CATALYST_MODEL=claude-haiku-5-5 python -m eval.runner --layer W --online --record eval/out/haiku-online
    W 层必须 --online；R 层拒绝 --online（会报错），所以联网与回测分两次跑。
    """
    from pathlib import Path

    ap = argparse.ArgumentParser(description="Run eval cases (needs the core package and a real reasoner)")
    ap.add_argument("--group", action="append", choices=GROUPS)
    ap.add_argument("--layer", action="append", choices=LAYERS,
                    help="layers to run (repeatable); default A, B, R, T, P. W needs --online")
    ap.add_argument("--case", action="append", help="case ids; overrides --layer (not for P)")
    ap.add_argument("--online", action="store_true", help="turn on online research (layer W); refused for layer R")
    ap.add_argument("--out", default=None, help="results.json path; defaults to <record dir>/results.json or eval/out/results.json")
    ap.add_argument("--record", metavar="DIR", help="recording directory (cassette.jsonl, results.json, report.md)")
    ap.add_argument("--today", help="date used for condition evaluation when a case has none; defaults to today")
    ap.add_argument("--packs", choices=PACK_SOURCES, default="real",
                    help="evidence source: real uses only the real packs under packs/ (default); synthetic always uses the eval/fixtures placeholders. One source per run")
    ap.add_argument("--replay", metavar="DIR", help="replay <DIR>/cassette.jsonl at no cost (re-scores only, no model calls)")
    args = ap.parse_args(argv)
    layers = args.layer or ["A", "B", "R", "T", "P"]
    if "W" in layers and not args.online:
        ap.error("layer W needs --online")
    if "R" in layers and args.online:
        ap.error("layer R must run offline; run backtests without --online")

    import catalyst.evidence as evidence_mod  # noqa: WPS433
    import catalyst.reasoner as reasoner_mod  # noqa: WPS433
    from eval import report
    from eval.loader import load_all_cases
    from eval.probes import run_probes

    if args.replay:
        out_dir = Path(args.replay)
        reasoner = reasoner_mod.ReplayReasoner(out_dir / "cassette.jsonl")
        prev = out_dir / "results.json"
        model = (json.loads(prev.read_text(encoding="utf-8"))[0].get("model", "unknown") + " (replay)") \
            if prev.exists() else reasoner.name
    else:
        reasoner = reasoner_mod.default_reasoner()
        model = getattr(reasoner, "name", "unknown")
        out_dir = Path(args.record) if args.record else Path("eval/out")
    out_dir.mkdir(parents=True, exist_ok=True)
    WEB_RUNS.update(dir=out_dir / "web_runs", replay=bool(args.replay))
    if args.record:
        reasoner = reasoner_mod.RecordingReasoner(reasoner, out_dir / "cassette.jsonl")
    entrypoints = load_core_entrypoints()
    evidence = evidence_mod.default_provider()
    evaluate = load_core_condition_evaluator()
    cases = load_all_cases(args.case) if args.case else cases_for_layers(layers)
    results = run_all(cases, args.group or GROUPS, reasoner=reasoner, evidence=evidence, entrypoints=entrypoints,
                      pack_source=args.packs, online=args.online, evaluate_condition=evaluate, today=args.today)
    if "P" in layers and not args.case:
        results += run_probes(run_case, reasoner=reasoner, evidence=evidence, entrypoints=entrypoints,
                              evaluate_condition=evaluate)
    for r in results:
        r["model"] = model
    out = Path(args.out) if args.out else out_dir / "results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    md = report.render_report(results, title=f"Catalyst eval per-case report ({model})")
    (out.parent / "report.md").write_text(md, encoding="utf-8")
    print(f"wrote {len(results)} results -> {out}; report -> {out.parent / 'report.md'}")
    for r in results:
        print(f"  {r['case_id']:3} {r['group']:8} {r['status']:15} {','.join(r['failure_types']) or '-'}")


if __name__ == "__main__":  # pragma: no cover
    main()
