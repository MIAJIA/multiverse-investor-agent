"""校验器：只裁决结构，不裁决因果是否成立。

每条错误的文本都带出错对象的 id（node / edge / condition / excerpt），harness 把它原样回给
模型重写那一部分，eval 用它定位。校验失败的输出不进版本快照，只进 trace。
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

from catalyst.schema import Condition, EvidencePack, Graph, parse_condition, parse_graph, parse_pack


@dataclass(frozen=True)
class Issue:
    ref: str
    message: str
    blocking: bool = True

    def __str__(self) -> str:
        return f"[{self.ref}] {self.message}"


def _is_date(v: str | None) -> bool:
    """只接受 YYYY-MM-DD（Python 3.11+ 的 fromisoformat 也接受 20261001，这里不接受）。"""
    try:
        return bool(v) and len(v) == 10 and _dt.date.fromisoformat(v).isoformat() == v
    except ValueError:
        return False


# ---- Condition ----------------------------------------------------------

def validate_condition(condition: Condition | dict) -> list[Issue]:
    c = parse_condition(condition)
    out: list[Issue] = []
    if c.kind == "numeric":
        if c.threshold is None and not (c.threshold_note or "").strip():
            out.append(Issue(c.id, "a numeric condition with threshold=null must have a threshold_note (why it is unknown and who confirms it)"))
        if c.comparator is None:
            # The direction of the comparison is known even when the number is not ("growth above ?"), so a
            # numeric condition always needs one; otherwise it cannot be decided once the threshold is confirmed.
            out.append(Issue(c.id, "a numeric condition must have a comparator, even when its threshold is still null"))
        if not c.series and c.verification_status == "verifiable":
            out.append(Issue(c.id, "a verifiable numeric condition must name a series; if you do not know one, mark it unverified and explain in threshold_note"))
        if not c.series and not (c.threshold_note or "").strip():
            out.append(Issue(c.id, "a numeric condition without a series must say in threshold_note what data is missing"))
    elif not (c.source or c.series):
        out.append(Issue(c.id, f"a {c.kind} condition must name the source that decides it"))
    if not _is_date(c.deadline):
        out.append(Issue(c.id, f"deadline must be an absolute date YYYY-MM-DD: {c.deadline!r}"))
    if c.anchor.startswith("scenario:"):
        pass  # 情景起点由用户确认，不做日期比较
    elif not _is_date(c.anchor):
        out.append(Issue(c.id, f"anchor must be an absolute date or scenario:<event>: {c.anchor!r}"))
    elif _is_date(c.deadline) and c.deadline < c.anchor:
        out.append(Issue(c.id, f"deadline {c.deadline} is before anchor {c.anchor}"))
    w = c.observation_window
    if w.start.startswith("scenario:") or w.end.startswith("scenario:"):
        pass
    elif w.end < w.start:
        out.append(Issue(c.id, f"observation_window ends {w.end}, before it starts {w.start}"))
    if _is_date(c.deadline) and _is_date(w.end) and w.end > c.deadline:
        out.append(Issue(c.id, f"observation_window ends {w.end}, after the deadline {c.deadline}"))
    if not c.rule.strip():
        out.append(Issue(c.id, "rule cannot be empty: it must say how met / not_met is decided"))
    return out


# ---- 图结构 -------------------------------------------------------------

def _cycle(graph: Graph) -> list[str] | None:
    adj: dict[str, list[str]] = {n.id: [] for n in graph.nodes}
    for e in graph.edges:
        adj.setdefault(e.from_, []).append(e.to)
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(u: str) -> list[str] | None:
        state[u] = 1
        stack.append(u)
        for v in adj.get(u, []):
            if state.get(v) == 1:
                return stack[stack.index(v):] + [v]
            if v not in state and (found := visit(v)):
                return found
        stack.pop()
        state[u] = 2
        return None

    for n in adj:
        if n not in state and (found := visit(n)):
            return found
    return None


def validate_graph(graph: Graph | dict) -> list[Issue]:
    g = parse_graph(graph)
    out: list[Issue] = []
    ids = [n.id for n in g.nodes]
    node_ids = set(ids)
    for dup in {i for i in ids if ids.count(i) > 1}:
        out.append(Issue(dup, "duplicate node id"))
    edge_ids = [e.id for e in g.edges]
    for dup in {i for i in edge_ids if edge_ids.count(i) > 1}:
        out.append(Issue(dup, "duplicate edge id"))
    cond_ids = [c.id for c in g.conditions]
    for dup in {i for i in cond_ids if cond_ids.count(i) > 1}:
        out.append(Issue(dup, "duplicate condition id"))

    for e in g.edges:
        for end in (e.from_, e.to):
            if end not in node_ids:
                out.append(Issue(e.id, f"edge points to a node that does not exist: {end}"))
        if not e.evidence and not e.model_only:
            out.append(Issue(e.id, "every edge must either cite evidence or be marked model_only"))
    if out:
        return out  # 引用都不完整时，后面的图论检查没有意义

    if cyc := _cycle(g):
        out.append(Issue(cyc[0], "the graph has a cycle: " + " → ".join(cyc)))
        return out

    terminals = {n.id for n in g.nodes if n.role == "terminal"}
    if not terminals:
        out.append(Issue("graph", "there must be at least one terminal node (landing on an instrument)"))
    for n in g.nodes:
        if n.role == "terminal" and not n.instruments:
            out.append(Issue(n.id, "a terminal node must list instruments"))
        if n.role != "terminal" and n.instruments:
            out.append(Issue(n.id, "only terminal nodes list instruments"))
        if not n.original_statement.strip():
            out.append(Issue(n.id, "original_statement must keep the original wording"))

    # 每个节点都在通往某个 terminal 的路径上
    rev: dict[str, set[str]] = {n: set() for n in node_ids}
    for e in g.edges:
        rev[e.to].add(e.from_)
    reach, todo = set(terminals), list(terminals)
    while todo:
        for p in rev[todo.pop()]:
            if p not in reach:
                reach.add(p)
                todo.append(p)
    for n in sorted(node_ids - reach):
        out.append(Issue(n, "node is not on any path to a terminal"))

    for c in g.conditions:
        if c.claim_id not in node_ids:
            out.append(Issue(c.id, f"condition is attached to a claim that does not exist: {c.claim_id}"))
        out += validate_condition(c)
    return out


# ---- 引用（Reference Validator）----------------------------------------

def validate_references(graph: Graph | dict, evidence_pack: EvidencePack | dict | None) -> list[Issue]:
    """引用必须存在于当前资料包，立场与片段一致（supports / contradicts / neutral 互相不能翻转）；
    model_only 不能冒充有证据；supported 必须有 supports 证据撑（neutral 是背景，不算）；
    未被驳回（无 rebuttal）的 contradicts 片段不能挂在 supported 的 claim 上（neutral 不需要 rebuttal）。"""
    g = parse_graph(graph)
    pack = parse_pack(evidence_pack) if evidence_pack is not None else None
    known = {x.excerpt_id: x for x in pack.excerpts} if pack else {}
    out: list[Issue] = []
    status = {n.id: n.evidence_status for n in g.nodes}
    supported_in: dict[str, bool] = {n.id: False for n in g.nodes}
    inbound: dict[str, int] = {n.id: 0 for n in g.nodes}

    for e in g.edges:
        inbound[e.to] = inbound.get(e.to, 0) + 1
        for ev in e.evidence:
            if ev.excerpt_id not in known:
                where = f"evidence pack {pack.pack_id}" if pack else "the current evidence pack (empty)"
                out.append(Issue(ev.excerpt_id, f"edge {e.id} cites excerpt {ev.excerpt_id}, which is not in {where}"))
            elif known[ev.excerpt_id].source_id != ev.source_id:
                out.append(Issue(ev.excerpt_id, f"edge {e.id}: source_id {ev.source_id} does not match the excerpt's source {known[ev.excerpt_id].source_id}"))
            elif known[ev.excerpt_id].stance != ev.stance:
                out.append(Issue(ev.excerpt_id, f"edge {e.id} cites the {known[ev.excerpt_id].stance} excerpt {ev.excerpt_id} as {ev.stance}: a stance cannot be flipped"))
            if ev.stance == "contradicts" and not ev.rebuttal and status.get(e.to) == "supported":
                out.append(Issue(e.to, f"edge {e.id} carries the unrebutted contradicting excerpt {ev.excerpt_id}: write a rebuttal or mark {e.to} contradicted"))
        if e.model_only and any(ev.stance == "supports" for ev in e.evidence):
            out.append(Issue(e.id, "a model_only edge cannot carry supports evidence"))
        if not e.model_only and any(ev.stance == "supports" for ev in e.evidence):
            supported_in[e.to] = True

    for n in g.nodes:
        if n.evidence_status == "supported" and inbound.get(n.id) and not supported_in[n.id]:
            out.append(Issue(n.id, "marked supported, but no non-model_only incoming edge carries supports evidence"))
    return out


def unanswered_contradictions(graph: Graph | dict, evidence_pack: EvidencePack | dict | None) -> list[Issue]:
    """资料包里的反方片段一条都没被引用 → 非阻断提示（片段可能与所选路径无关）。"""
    if evidence_pack is None:
        return []
    g, pack = parse_graph(graph), parse_pack(evidence_pack)
    cited = {ev.excerpt_id for e in g.edges for ev in e.evidence}
    return [Issue(x.excerpt_id, "a contradicting excerpt in the evidence pack was not answered", blocking=False)
            for x in pack.excerpts if x.stance == "contradicts" and x.excerpt_id not in cited]


# ---- Plans (exactly one per terminal) ------------------------------------------------

def validate_plans(graph: Graph | dict, drafts: list) -> list[Issue]:
    """Plan drafts (ProposalDraft, or TradeProposal with the same fields) against the graph. Blocking:
    - the set of plan terminals equals the set of terminals in the graph: one plan each, no more, no less;
    - direction.instrument belongs to that terminal's instruments;
    - referenced conditions and claims exist; at least one entry condition;
    - all plans share one reading of the user's words: user_judgment.original_statement and clarified_statement are
      identical across plans (the UI confirms it once for the whole graph; code never picks one of several).
    Non-blocking: an entry condition on a claim that is not upstream of the plan's terminal (conditions may be
    shared). Exit conditions get no hint: the prompt encourages mirror exit conditions that sit on a rival branch."""
    from catalyst.branches import ancestors  # branches only imports schema; local import keeps module order simple

    g = parse_graph(graph)
    out: list[Issue] = []
    nodes = {n.id: n for n in g.nodes}
    conds = {c.id: c for c in g.conditions}
    terminals = [n.id for n in g.nodes if n.role == "terminal"]
    seen: list[str] = [d.terminal_id for d in drafts]
    for t in sorted({t for t in seen if seen.count(t) > 1}):
        out.append(Issue(t, f"terminal {t} has {seen.count(t)} plans; write exactly one plan per terminal"))
    for t in sorted(set(seen) - set(terminals)):
        what = "is not a terminal node" if t in nodes else "is not in the graph"
        out.append(Issue(t, f"plan terminal_id {t} {what}; plans may only target these terminals: {terminals}"))
    for t in terminals:
        if t not in seen:
            out.append(Issue(t, f"terminal {t} has no plan; every terminal in the graph needs one plan with a "
                                "direction and an instrument"))
    for field in ("original_statement", "clarified_statement"):
        values = {getattr(d.user_judgment, field) for d in drafts}
        if len(values) > 1:
            out.append(Issue("proposals", f"user_judgment.{field} differs across plans ({sorted(values)}); "
                                          "it is one reading of the user's words for the whole graph, so write the "
                                          "same text in every plan"))
    for d in drafts:
        t = d.terminal_id
        if hasattr(d, "entry_condition_ids"):
            entry, exit_ = list(d.entry_condition_ids), list(d.exit_condition_ids)
        else:
            entry, exit_ = [c.id for c in d.entry_conditions], [c.id for c in d.exit_conditions]
        out += [Issue(i, f"plan {t} references unknown condition {i}") for i in entry + exit_ if i not in conds]
        if not entry:
            out.append(Issue(t, f"plan {t} needs at least one entry condition (an empty set never passes, and it "
                                "says nothing about what is still needed)"))
        kd = d.key_dependency
        if kd and kd.condition_id and kd.condition_id not in conds:
            out.append(Issue(kd.condition_id, f"key_dependency of plan {t} references an unknown condition"))
        if kd and kd.claim_id and kd.claim_id not in nodes:
            out.append(Issue(kd.claim_id, f"key_dependency of plan {t} references an unknown claim"))
        if t in nodes and nodes[t].role == "terminal":
            if d.direction.instrument not in nodes[t].instruments:
                out.append(Issue(t, f"plan {t} trades {d.direction.instrument}, which is not an instrument of this "
                                    f"terminal: {nodes[t].instruments}"))
            upstream = ancestors(g, t) | {t}
            for i in dict.fromkeys(entry):
                if i in conds and conds[i].claim_id not in upstream:
                    out.append(Issue(i, f"entry condition {i} of plan {t} sits on {conds[i].claim_id}, which is not "
                                        f"upstream of {t}", blocking=False))
    return out


def blocking(issues: list[Issue]) -> list[Issue]:
    return [i for i in issues if i.blocking]
