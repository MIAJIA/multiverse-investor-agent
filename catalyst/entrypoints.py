"""三个入口：discover / inspect / fork。UI、eval runner、harness CLI 都只调这里。

模型只经 Reasoner 进入；图只经校验器进入快照；gate、status、版本号、assessment 的默认值只由代码写。
"""
from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass, field

from catalyst import prompts
from catalyst.conditions import evaluate
from catalyst.diff import diff as graph_diff
from catalyst.evidence import EvidenceProvider
from catalyst.fork import PatchInvalid, ScopeViolation, apply_patch, build_scenario, compute_write_scope
from catalyst.gate import evaluate_entry
from catalyst.harness import run_stage
from catalyst.schema import (
    Condition, DiscoverOutput, EvidencePack, ForkOutput, Graph, InspectOutput, JudgmentOutput, Op, Patch,
    FieldUpdate, ProposalDraft, ProposalMeta, ScenarioRef, TradeProposal, parse_graph,
)
from catalyst.store import RunStore
from catalyst.validator import blocking, unanswered_contradictions, validate_graph, validate_references


@dataclass
class Config:
    packs: list[str] = field(default_factory=list)
    today: str = field(default_factory=lambda: _dt.date.today().isoformat())
    run_prefix: str = "g"
    max_retries: int = 2
    max_candidates: int = 3
    observations: list[dict] = field(default_factory=list)  # 条件判定用的观测数据（POC 通常为空）


def _cfg(config) -> Config:
    if config is None:
        return Config()
    return config if isinstance(config, Config) else Config(**config)


def _pack_text(pack: EvidencePack | None) -> str:
    if pack is None or not pack.excerpts:
        return "（本轮没有资料包：所有边都只能是 model_only，所有 claim 的 evidence_status 只能是 unknown。）"
    note = "（注意：这是合成的占位资料包，只用于跑通流程。）\n" if pack.synthetic else ""
    return note + "\n".join(json.dumps(x.dump(), ensure_ascii=False) for x in pack.excerpts)


def _excerpt_ids(pack: EvidencePack | None) -> list[str]:
    return [x.excerpt_id for x in pack.excerpts] if pack else []


def _issues(xs) -> tuple[list[str], list[str]]:
    return [str(i) for i in xs if i.blocking], [str(i) for i in xs if not i.blocking]


# ---- inspect -----------------------------------------------------------

def _graph_from(out: InspectOutput, version: str, op: Op, cfg: Config) -> Graph:
    now = _dt.date.fromisoformat(cfg.today)
    conds = []
    for mc in out.conditions:
        c = Condition.model_validate({**mc.dump(), "evaluation_status": "unknown"})
        conds.append(c.model_copy(update={"evaluation_status": evaluate(c, cfg.observations, now)}))
    return Graph(version=version, parent_version=None, op=op, nodes=out.nodes, edges=out.edges, conditions=conds)


def _draft_issues(d: ProposalDraft, g: Graph) -> list[str]:
    cond_ids, node_ids = {c.id for c in g.conditions}, {n.id for n in g.nodes}
    out = [f"[{i}] 提案引用了不存在的条件" for i in d.entry_condition_ids + d.exit_condition_ids if i not in cond_ids]
    if not d.entry_condition_ids:
        out.append("[proposal] 至少要有一条进场条件（空集不会自动通过，但也说明不了还需要什么）")
    kd = d.key_dependency
    if kd and kd.condition_id and kd.condition_id not in cond_ids:
        out.append(f"[{kd.condition_id}] key_dependency 引用了不存在的条件")
    if kd and kd.claim_id and kd.claim_id not in node_ids:
        out.append(f"[{kd.claim_id}] key_dependency 引用了不存在的 claim")
    instruments = {i for n in g.nodes if n.role == "terminal" for i in n.instruments}
    if d.direction.instrument not in instruments:
        out.append(f"[{d.direction.instrument}] 提案标的必须是某个 terminal 节点的 instrument：{sorted(instruments)}")
    return out


def derive_proposal(draft: ProposalDraft, g: Graph, *, model: str, scenario_ref: ScenarioRef | None = None,
                    support_status: str | None = None) -> TradeProposal:
    by_id = {c.id: c for c in g.conditions}
    entry = [by_id[i] for i in draft.entry_condition_ids]
    return TradeProposal(
        status="draft", gate=evaluate_entry(entry), direction=draft.direction, entry_conditions=entry,
        exit_conditions=[by_id[i] for i in draft.exit_condition_ids], exit_logic=draft.exit_logic,
        key_dependency=draft.key_dependency, user_judgment=draft.user_judgment, market_reference=None,
        scenario_ref=scenario_ref, support_status=support_status or draft.support_status, graph_version=g.version,
        meta=ProposalMeta(proposal_version=f"{g.version}.p", prompt_version=prompts.PROMPT_VERSION, model=model),
    )


def _draft_of(p: TradeProposal) -> ProposalDraft:
    return ProposalDraft(direction=p.direction, entry_condition_ids=[c.id for c in p.entry_conditions],
                         exit_condition_ids=[c.id for c in p.exit_conditions], exit_logic=p.exit_logic,
                         key_dependency=p.key_dependency, user_judgment=p.user_judgment, support_status=p.support_status)


def inspect(event: str, target: str | None = None, *, candidate_id: str | None = None, candidate: dict | None = None,
            material: str | None = None, judgment_only: bool = False, reasoner, evidence: EvidenceProvider | None,
            config=None, store: RunStore | None = None) -> dict:
    cfg = _cfg(config)
    if judgment_only:
        user = f"材料：\n{material}\n\n因果断言：{event}" + (f" → {target}" if target else "")
        r = run_stage("judge", system=prompts.JUDGE, user=user, output_model=JudgmentOutput, reasoner=reasoner,
                      max_retries=cfg.max_retries, store=store)
        j = r.value.judgment.dump() if r.ok else None
        return _finish(store, {"graph": None, "no_chain": None, "proposal": None, "judgment": j,
                               "observations": [], "ok": r.ok, "errors": r.errors, "attempts": r.attempts})

    pack = evidence.combined(cfg.packs) if evidence else None
    version = f"{cfg.run_prefix}-v1"
    op = Op(kind="inspect", target=target, value=event)
    focus = ""
    if candidate:
        focus = f"\n用户选中的方向（来自 Discover，id={candidate_id}）：{json.dumps(candidate, ensure_ascii=False)}"
    user = (f"今天：{cfg.today}\n事件（用户原话）：{event}\n目标标的：{target or '（未给出，从选中方向或资料里确定）'}{focus}\n\n"
            f"资料包：\n{_pack_text(pack)}")

    def check(out: InspectOutput):
        if out.no_chain:
            ok = not out.nodes and not out.edges and out.proposal is None and bool(out.no_chain_reason)
            return ([] if ok else ["[no_chain] no_chain=true 时 nodes/edges/conditions 留空、proposal=null，并写 no_chain_reason"]), []
        if out.proposal is None:
            return ["[proposal] 有因果链时必须给出提案草稿"], []
        g = _graph_from(out, version, op, cfg)
        errs, warns = _issues(validate_graph(g) + validate_references(g, pack) + unanswered_contradictions(g, pack))
        return errs + _draft_issues(out.proposal, g), warns

    r = run_stage("inspect", system=prompts.INSPECT, user=user, output_model=InspectOutput, reasoner=reasoner,
                  validate=check, max_retries=cfg.max_retries, store=store)
    result = {"graph": None, "no_chain": None, "no_chain_reason": None, "proposal": None, "judgment": None,
              "observations": _excerpt_ids(pack), "ok": r.ok, "errors": r.errors, "warnings": r.warnings,
              "attempts": r.attempts}
    if not r.ok:
        return _finish(store, result)
    out = r.value
    result.update(no_chain=out.no_chain, no_chain_reason=out.no_chain_reason)
    if out.no_chain:
        return _finish(store, result)
    g = _graph_from(out, version, op, cfg)
    p = derive_proposal(out.proposal, g, model=r.meta.get("model", reasoner.name))
    result.update(graph=g.dump(), proposal=p.dump())
    if store:
        store.put_snapshot(g.dump())
        store.put_observations(g.version, [x.dump() for x in pack.excerpts] if pack else [])
        store.put_proposal(g.version, p.dump())
        store.log_op(op="inspect", actor="model", input_version=None, output_version=g.version,
                     prompt_version=prompts.PROMPT_VERSION, model=r.meta.get("model"), attempts=r.attempts)
    return _finish(store, result)


# ---- discover ----------------------------------------------------------

def discover(event: str, target: str | None = None, *, reasoner, evidence: EvidenceProvider | None,
             config=None, store: RunStore | None = None) -> dict:
    cfg = _cfg(config)
    pack = evidence.combined(cfg.packs) if evidence else None
    known = set(_excerpt_ids(pack))
    user = f"今天：{cfg.today}\n事件（用户原话）：{event}\n\n资料包：\n{_pack_text(pack)}"

    def check(out: DiscoverOutput):
        errs = []
        if len(out.candidates) > cfg.max_candidates:
            errs.append(f"[candidates] 最多 {cfg.max_candidates} 个候选，现在 {len(out.candidates)} 个")
        if out.abstained != (len(out.candidates) == 0):
            errs.append("[abstained] abstained=true 当且仅当 candidates 为空")
        if out.abstained and not out.abstain_reason:
            errs.append("[abstain_reason] 弃权必须写明原因")
        for c in out.candidates:
            errs += [f"[{x}] 候选 {c.id} 引用了不在资料包里的片段" for x in c.excerpt_ids if x not in known]
            if c.label == "grounded" and not c.excerpt_ids:
                errs.append(f"[{c.id}] grounded 候选必须列出支持它的片段")
        return errs, []

    r = run_stage("discover", system=prompts.DISCOVER, user=user, output_model=DiscoverOutput, reasoner=reasoner,
                  validate=check, max_retries=cfg.max_retries, store=store)
    result = {"candidates": [], "abstained": None, "abstain_reason": None, "proposal": None,
              "observations": sorted(known), "ok": r.ok, "errors": r.errors, "attempts": r.attempts}
    if r.ok:
        result.update(candidates=[c.dump() for c in r.value.candidates], abstained=r.value.abstained,
                      abstain_reason=r.value.abstain_reason)
        if store:
            store.log_op(op="discover", actor="model", input_version=None, output_version=None,
                         prompt_version=prompts.PROMPT_VERSION, model=r.meta.get("model"),
                         candidates=[c.id for c in r.value.candidates])
    return _finish(store, result, name="discover")


# ---- fork --------------------------------------------------------------

def _to_patch(out: ForkOutput, base: Graph) -> Patch:
    def updates(items):
        return [FieldUpdate(id=u.id, fields={k: v for k, v in u.dump().items() if k != "id" and v is not None})
                for u in items]
    return Patch(base_version=base.version, node_updates=updates(out.node_updates),
                 edge_updates=updates(out.edge_updates), condition_updates=updates(out.condition_updates),
                 assessment={a.claim_id: a.status for a in out.assessment},
                 assessment_reason={a.claim_id: a.reason for a in out.assessment})


def fork(graph, op, *, reasoner, evidence: EvidenceProvider | None, config=None, proposal: dict | None = None,
         store: RunStore | None = None) -> dict:
    cfg = _cfg(config)
    base = parse_graph(graph)
    o = op if isinstance(op, Op) else Op.model_validate(op)
    scope = compute_write_scope(base, o)
    pack = evidence.combined(cfg.packs) if evidence else None
    if o.kind == "add_shock":  # Stage 1 由代码给出（预定义接入点），这里只把新增对象交给模型补全
        new = {"new_nodes": [n.dump() for n in o.new_nodes], "new_edges": [e.dump() for e in o.new_edges]}
    else:
        new = {}
    user = (f"今天：{cfg.today}\n操作：{json.dumps(o.dump(), ensure_ascii=False)}\n"
            f"写范围（只能改这些）：{json.dumps(scope.to_dict(), ensure_ascii=False)}\n{json.dumps(new, ensure_ascii=False) if new else ''}\n"
            f"基线图：\n{json.dumps(base.dump(), ensure_ascii=False)}\n\n资料包：\n{_pack_text(pack)}")
    holder: dict = {}

    def check(out: ForkOutput):
        try:
            patch = _to_patch(out, base)
            patch = patch.model_copy(update={"node_adds": list(o.new_nodes), "edge_adds": list(o.new_edges)})
            holder["graph"] = apply_patch(base, patch, scope, op=o)
            holder["patch"] = patch
        except (ScopeViolation, PatchInvalid) as e:
            return [str(e)], []
        missing = sorted(set(scope.nodes) - {a.claim_id for a in out.assessment})
        errs = [f"[{m}] 写范围内的 claim 都要给出 assessment" for m in missing]
        g = holder["graph"]
        return errs + [str(i) for i in blocking(validate_references(g, pack))], []

    r = run_stage("fork", system=prompts.FORK, user=user, output_model=ForkOutput, reasoner=reasoner,
                  validate=check, max_retries=cfg.max_retries, store=store)
    result = {"graph": None, "base_graph": base.dump(), "scope": scope.to_dict(), "diff": None, "scenario": None,
              "proposal": None, "ok": r.ok, "errors": r.errors, "attempts": r.attempts}
    if not r.ok:
        return _finish(store, result, name="fork")
    new_g, patch = holder["graph"], holder["patch"]
    scenario = build_scenario(base, new_g, o, patch)
    challenged = sorted(k for k, v in scenario.assessment.items() if v == "challenged")
    result.update(graph=new_g.dump(), diff=graph_diff(base, new_g), scenario=scenario.dump())
    if proposal:
        old = TradeProposal.model_validate(proposal)
        draft = _draft_of(old)
        touched = {c.claim_id for c in old.entry_conditions} | {old.key_dependency.claim_id if old.key_dependency else None}
        support = "challenged" if touched & set(challenged) else old.support_status
        ref = ScenarioRef(base_version=base.version, challenged_claim_ids=challenged, next_checks=r.value.next_checks)
        result["proposal"] = derive_proposal(draft, new_g, model=r.meta.get("model", reasoner.name),
                                             scenario_ref=ref, support_status=support).dump()
    if store:
        store.put_snapshot(base.dump())
        store.put_snapshot(new_g.dump())
        store.put_scenario(scenario.dump())
        if result["proposal"]:
            store.put_proposal(new_g.version, result["proposal"])
        store.log_op(op=o.kind, actor="user+model", input_version=base.version, output_version=new_g.version,
                     prompt_version=prompts.PROMPT_VERSION, model=r.meta.get("model"), scope=scope.to_dict())
    return _finish(store, result, name="fork")


def _finish(store: RunStore | None, result: dict, name: str = "inspect") -> dict:
    if store:
        path = store.root / f"{name}.result.json"
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result
