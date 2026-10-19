"""三个入口：discover / inspect / fork。UI、eval runner、harness CLI 都只调这里。

模型只经 Reasoner 进入；图只经校验器进入快照。下面这些只由代码写：gate、status、support_status、
版本号、条件判定、范围外的 assessment，以及用户判断里的确认字段。
"""
from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass, field

from catalyst import prompts
from catalyst.conditions import evaluate
from catalyst.diff import diff as graph_diff
from catalyst.evidence import EvidenceProvider
from catalyst.fork import (
    PatchInvalid, ScopeViolation, apply_patch, build_scenario, compute_write_scope, next_version,
)
from catalyst.gate import evaluate_entry
from catalyst.harness import run_stage
from catalyst.schema import (
    Condition, DiscoverOutput, EvidencePack, FieldUpdate, ForkOutput, Graph, InspectOutput, JudgmentOutput,
    Mechanism, ModelUserJudgment, Op, Patch, ProposalDraft, ProposalMeta, ScenarioRef, TradeProposal, UserJudgment,
    parse_graph, parse_pack,
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


def _cfg(config, packs: list[str] | None = None) -> Config:
    cfg = Config() if config is None else config if isinstance(config, Config) else Config(**config)
    if packs is not None:
        cfg = Config(**{**cfg.__dict__, "packs": list(packs)})
    return cfg


def _pack_text(pack: EvidencePack | None) -> str:
    if pack is None or not pack.excerpts:
        return "（本轮没有资料包：所有边都只能是 model_only，所有 claim 的 evidence_status 只能是 unknown。）"
    note = "（注意：这是合成的占位资料包，只用于跑通流程。）\n" if pack.synthetic else ""
    return note + "\n".join(json.dumps(x.dump(), ensure_ascii=False) for x in pack.excerpts)


def _excerpt_ids(pack: EvidencePack | None) -> list[str]:
    return [x.excerpt_id for x in pack.excerpts] if pack else []


def _issues(xs) -> tuple[list[str], list[str]]:
    return [str(i) for i in xs if i.blocking], [str(i) for i in xs if not i.blocking]


def _reevaluate(g: Graph, cfg: Config) -> Graph:
    """条件判定只由代码按规则和观测给出；任何改过条件的新版本都要重算。"""
    now = _dt.date.fromisoformat(cfg.today)
    conds = [c.model_copy(update={"evaluation_status": evaluate(c, cfg.observations, now)}) for c in g.conditions]
    return g.model_copy(update={"conditions": conds})


# ---- 提案（全部由代码从图派生）---------------------------------------------

def _user_judgment(m: ModelUserJudgment) -> UserJudgment:
    """确认、概率、确认过的 claim 只能由用户写；模型改写过原话就必须让用户确认。"""
    changed = m.clarified_statement.strip() != m.original_statement.strip()
    return UserJudgment(original_statement=m.original_statement, clarified_statement=m.clarified_statement,
                        criteria=m.criteria, deadline=m.deadline,
                        requires_user_confirmation=m.requires_user_confirmation or changed)


def _support_status(g: Graph, claim_ids: set[str], challenged: set[str]) -> str:
    status = {n.id: n.evidence_status for n in g.nodes}
    relevant = [status[c] for c in claim_ids if c in status]
    if claim_ids & challenged or "contradicted" in relevant:
        return "challenged"
    return "supported" if relevant and all(s == "supported" for s in relevant) else "unknown"


def derive_proposal(draft: ProposalDraft, g: Graph, *, model: str, user_judgment: UserJudgment | None = None,
                    scenario_ref: ScenarioRef | None = None) -> TradeProposal:
    by_id = {c.id: c for c in g.conditions}
    entry = [by_id[i] for i in draft.entry_condition_ids]
    gate = evaluate_entry(entry)
    kd = draft.key_dependency
    claims = {c.claim_id for c in entry} | ({kd.claim_id} if kd and kd.claim_id else set()) \
        | ({by_id[kd.condition_id].claim_id} if kd and kd.condition_id in by_id else set())
    challenged = set(scenario_ref.challenged_claim_ids) if scenario_ref else set()
    return TradeProposal(
        status="needs_review" if gate == "READY_FOR_REVIEW" else "draft", gate=gate, direction=draft.direction,
        entry_conditions=entry, exit_conditions=[by_id[i] for i in draft.exit_condition_ids],
        exit_logic=draft.exit_logic, key_dependency=kd,
        user_judgment=user_judgment or _user_judgment(draft.user_judgment), market_reference=None,
        scenario_ref=scenario_ref, support_status=_support_status(g, claims, challenged), graph_version=g.version,
        meta=ProposalMeta(proposal_version=f"{g.version}.p", prompt_version=prompts.PROMPT_VERSION, model=model),
    )


def _draft_of(p: TradeProposal) -> ProposalDraft:
    uj = p.user_judgment
    return ProposalDraft(
        direction=p.direction, entry_condition_ids=[c.id for c in p.entry_conditions],
        exit_condition_ids=[c.id for c in p.exit_conditions], exit_logic=p.exit_logic, key_dependency=p.key_dependency,
        user_judgment=ModelUserJudgment(original_statement=uj.original_statement, clarified_statement=uj.clarified_statement,
                                        criteria=uj.criteria, deadline=uj.deadline,
                                        requires_user_confirmation=uj.requires_user_confirmation))


# ---- inspect -----------------------------------------------------------

def _graph_from(out: InspectOutput, version: str, op: Op, cfg: Config) -> Graph:
    conds = [Condition.model_validate({**mc.dump(), "evaluation_status": "unknown"}) for mc in out.conditions]
    g = Graph(version=version, parent_version=None, op=op, nodes=out.nodes, edges=out.edges, conditions=conds)
    return _reevaluate(g, cfg)


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


def _root_issues(g: Graph) -> list[str]:
    """证据只挂在边上：没有入边的节点没有可审查的证据，不能标 supported。"""
    has_in = {e.to for e in g.edges}
    return [f"[{n.id}] 没有入边的节点没有可引用的证据，evidence_status 只能是 unknown 或 contradicted"
            for n in g.nodes if n.id not in has_in and n.evidence_status == "supported"]


def inspect(event: str, target: str | None = None, *, candidate_id: str | None = None, candidate: dict | None = None,
            material: str | None = None, judgment_only: bool = False, reasoner, evidence: EvidenceProvider | None,
            config=None, packs: list[str] | None = None, store: RunStore | None = None) -> dict:
    cfg = _cfg(config, packs)
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
    focus, warnings = "", []
    if candidate:
        focus = f"\n用户选中的方向（来自 Discover，id={candidate_id or candidate.get('id')}）：{json.dumps(candidate, ensure_ascii=False)}"
    elif candidate_id:
        warnings.append(f"只收到 candidate_id={candidate_id}，没有候选内容：请传 candidate=<Discover 返回的候选>")
        focus = f"\n用户选中的方向 id：{candidate_id}（内容未提供）"
    user = (f"今天：{cfg.today}\n事件（用户原话）：{event}\n目标标的：{target or '（未给出，从选中方向或资料里确定）'}{focus}\n\n"
            f"资料包：\n{_pack_text(pack)}")

    def check(out: InspectOutput):
        if out.no_chain:
            ok = (not out.nodes and not out.edges and not out.conditions and out.proposal is None
                  and bool(out.no_chain_reason))
            return ([] if ok else ["[no_chain] no_chain=true 时 nodes/edges/conditions 留空、proposal=null，并写 no_chain_reason"]), []
        if out.proposal is None:
            return ["[proposal] 有因果链时必须给出提案草稿"], []
        g = _graph_from(out, version, op, cfg)
        errs, warns = _issues(validate_graph(g) + validate_references(g, pack) + unanswered_contradictions(g, pack))
        return errs + _root_issues(g) + _draft_issues(out.proposal, g), warns

    r = run_stage("inspect", system=prompts.INSPECT, user=user, output_model=InspectOutput, reasoner=reasoner,
                  validate=check, max_retries=cfg.max_retries, store=store)
    result = {"graph": None, "no_chain": None, "no_chain_reason": None, "proposal": None, "judgment": None,
              "observations": _excerpt_ids(pack), "ok": r.ok, "errors": r.errors, "warnings": warnings + r.warnings,
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
             config=None, packs: list[str] | None = None, store: RunStore | None = None) -> dict:
    cfg = _cfg(config, packs)
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


def _new_edge_reference_issues(edges: list[Mechanism], pack: EvidencePack | None) -> list[str]:
    """fork 里模型改不了任何证据引用（补丁不含 evidence 字段），只有 Stage 1 新增的边带新引用。"""
    known = {x.excerpt_id: x for x in pack.excerpts} if pack else {}
    out = []
    for e in edges:
        for ev in e.evidence:
            x = known.get(ev.excerpt_id)
            if x is None or x.source_id != ev.source_id or x.stance != ev.stance:
                out.append(f"[{ev.excerpt_id}] Stage 1 新边 {e.id} 的引用不在当前资料包里或与片段不一致")
        if e.model_only and any(ev.stance == "supports" for ev in e.evidence):
            out.append(f"[{e.id}] model_only 的边不能带 supports 证据")
    return out


def fork(graph, op, *, reasoner, evidence: EvidenceProvider | None, config=None, packs: list[str] | None = None,
         pack: EvidencePack | dict | None = None, proposal: dict | None = None, store: RunStore | None = None) -> dict:
    """pack：本轮资料包；不给就用 cfg.packs。基线图已有的引用在生成时校验过，fork 只校验新增的边。"""
    cfg = _cfg(config, packs)
    base = parse_graph(graph)
    o = op if isinstance(op, Op) else Op.model_validate(op)
    result = {"graph": None, "base_graph": base.dump(), "scope": None, "diff": None, "scenario": None,
              "proposal": None, "ok": False, "errors": [], "attempts": 0}
    try:
        scope = compute_write_scope(base, o)
    except ScopeViolation as e:
        result["errors"] = [str(e)]
        if store:
            store.log_attempt(stage="fork.scope", attempt=0, ok=False, errors=[str(e)], warnings=[], raw=None, meta={})
        return _finish(store, result, name="fork")
    result["scope"] = scope.to_dict()
    pk = parse_pack(pack) if pack is not None else (evidence.combined(cfg.packs) if evidence else None)
    if errs := _new_edge_reference_issues(list(o.new_edges), pk):
        result["errors"] = errs
        return _finish(store, result, name="fork")

    version = next_version(base.version)
    while store and (store.root / "snapshots" / f"{version}.json").exists():
        version = next_version(version)
    new = {"new_nodes": [n.dump() for n in o.new_nodes], "new_edges": [e.dump() for e in o.new_edges]} \
        if o.kind == "add_shock" else {}
    user = (f"今天：{cfg.today}\n操作：{json.dumps(o.dump(), ensure_ascii=False)}\n"
            f"写范围（只能改这些）：{json.dumps(scope.to_dict(), ensure_ascii=False)}\n"
            f"{json.dumps(new, ensure_ascii=False) if new else ''}\n"
            f"基线图：\n{json.dumps(base.dump(), ensure_ascii=False)}\n\n资料包：\n{_pack_text(pk)}")
    holder: dict = {}

    def check(out: ForkOutput):
        try:
            patch = _to_patch(out, base).model_copy(update={"node_adds": list(o.new_nodes), "edge_adds": list(o.new_edges)})
            holder["graph"] = _reevaluate(apply_patch(base, patch, scope, op=o, new_version=version), cfg)
            holder["patch"] = patch
        except (ScopeViolation, PatchInvalid) as e:
            return [str(e)], []
        missing = sorted(set(scope.nodes) - {a.claim_id for a in out.assessment})
        return [f"[{m}] 写范围内的 claim 都要给出 assessment" for m in missing], []

    r = run_stage("fork", system=prompts.FORK, user=user, output_model=ForkOutput, reasoner=reasoner,
                  validate=check, max_retries=cfg.max_retries, store=store)
    result.update(ok=r.ok, errors=r.errors, attempts=r.attempts)
    if not r.ok:
        return _finish(store, result, name=f"fork.{version}")
    new_g, patch = holder["graph"], holder["patch"]
    scenario = build_scenario(base, new_g, o, patch)
    challenged = sorted(k for k, v in scenario.assessment.items() if v == "challenged")
    result.update(graph=new_g.dump(), diff=graph_diff(base, new_g), scenario=scenario.dump())
    if proposal:
        old = TradeProposal.model_validate(proposal)
        ref = ScenarioRef(base_version=base.version, challenged_claim_ids=challenged, next_checks=r.value.next_checks)
        result["proposal"] = derive_proposal(_draft_of(old), new_g, model=r.meta.get("model", reasoner.name),
                                             user_judgment=old.user_judgment, scenario_ref=ref).dump()
    if store:
        store.put_snapshot(base.dump())
        store.put_snapshot(new_g.dump())
        store.put_scenario(scenario.dump())
        store.put_observations(new_g.version, [x.dump() for x in pk.excerpts] if pk else [])
        if result["proposal"]:
            store.put_proposal(new_g.version, result["proposal"])
        store.log_op(op=o.kind, actor="user+model", input_version=base.version, output_version=new_g.version,
                     prompt_version=prompts.PROMPT_VERSION, model=r.meta.get("model"), scope=scope.to_dict())
    return _finish(store, result, name=f"fork.{version}")


def _finish(store: RunStore | None, result: dict, name: str = "inspect") -> dict:
    if store:
        path = store.root / f"{name}.result.json"
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result
