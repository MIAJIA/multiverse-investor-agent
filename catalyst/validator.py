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
            out.append(Issue(c.id, "数值条件的 threshold 为 null 时必须写 threshold_note（为什么不知道、由谁确认）"))
        if c.threshold is not None and c.comparator is None:
            out.append(Issue(c.id, "数值条件有 threshold 时必须给 comparator"))
        if not c.series and c.verification_status == "verifiable":
            out.append(Issue(c.id, "标 verifiable 的数值条件必须指向一个 series；不知道序列就标 unverified 并在 threshold_note 说明"))
        if not c.series and not (c.threshold_note or "").strip():
            out.append(Issue(c.id, "数值条件没有 series 时必须在 threshold_note 写明缺什么数据"))
    elif not (c.source or c.series):
        out.append(Issue(c.id, f"{c.kind} 条件必须写明判定来源 source"))
    if not _is_date(c.deadline):
        out.append(Issue(c.id, f"deadline 必须是绝对日期 YYYY-MM-DD：{c.deadline!r}"))
    if c.anchor.startswith("scenario:"):
        pass  # 情景起点由用户确认，不做日期比较
    elif not _is_date(c.anchor):
        out.append(Issue(c.id, f"anchor 必须是绝对日期或 scenario:<事件>：{c.anchor!r}"))
    elif _is_date(c.deadline) and c.deadline < c.anchor:
        out.append(Issue(c.id, f"deadline {c.deadline} 早于 anchor {c.anchor}"))
    w = c.observation_window
    if w.start.startswith("scenario:") or w.end.startswith("scenario:"):
        pass
    elif w.end < w.start:
        out.append(Issue(c.id, f"observation_window 结束 {w.end} 早于开始 {w.start}"))
    if _is_date(c.deadline) and _is_date(w.end) and w.end > c.deadline:
        out.append(Issue(c.id, f"observation_window 结束 {w.end} 晚于 deadline {c.deadline}"))
    if not c.rule.strip():
        out.append(Issue(c.id, "rule 不能为空：必须写明怎么判定 met / not_met"))
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
        out.append(Issue(dup, "节点 id 重复"))
    edge_ids = [e.id for e in g.edges]
    for dup in {i for i in edge_ids if edge_ids.count(i) > 1}:
        out.append(Issue(dup, "边 id 重复"))
    cond_ids = [c.id for c in g.conditions]
    for dup in {i for i in cond_ids if cond_ids.count(i) > 1}:
        out.append(Issue(dup, "条件 id 重复"))

    for e in g.edges:
        for end in (e.from_, e.to):
            if end not in node_ids:
                out.append(Issue(e.id, f"边指向不存在的节点 {end}"))
        if not e.evidence and not e.model_only:
            out.append(Issue(e.id, "每条边要么引用证据，要么显式标 model_only"))
    if out:
        return out  # 引用都不完整时，后面的图论检查没有意义

    if cyc := _cycle(g):
        out.append(Issue(cyc[0], "图里有环：" + " → ".join(cyc)))
        return out

    terminals = {n.id for n in g.nodes if n.role == "terminal"}
    if not terminals:
        out.append(Issue("graph", "至少要有一个 terminal 节点（落到具体标的）"))
    for n in g.nodes:
        if n.role == "terminal" and not n.instruments:
            out.append(Issue(n.id, "terminal 节点必须写 instruments"))
        if n.role != "terminal" and n.instruments:
            out.append(Issue(n.id, "只有 terminal 节点写 instruments"))
        if not n.original_statement.strip():
            out.append(Issue(n.id, "original_statement 必须保留原话"))

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
        out.append(Issue(n, "节点不在任何通往 terminal 的路径上"))

    for c in g.conditions:
        if c.claim_id not in node_ids:
            out.append(Issue(c.id, f"条件挂在不存在的 claim {c.claim_id} 上"))
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
                where = f"资料包 {pack.pack_id}" if pack else "当前资料包（为空）"
                out.append(Issue(ev.excerpt_id, f"边 {e.id} 引用的片段 {ev.excerpt_id} 不在{where}里"))
            elif known[ev.excerpt_id].source_id != ev.source_id:
                out.append(Issue(ev.excerpt_id, f"边 {e.id} 的 source_id {ev.source_id} 与片段来源 {known[ev.excerpt_id].source_id} 不一致"))
            elif known[ev.excerpt_id].stance != ev.stance:
                out.append(Issue(ev.excerpt_id, f"边 {e.id} 把 {known[ev.excerpt_id].stance} 片段 {ev.excerpt_id} 引用成了 {ev.stance}：立场不能翻转"))
            if ev.stance == "contradicts" and not ev.rebuttal and status.get(e.to) == "supported":
                out.append(Issue(e.to, f"边 {e.id} 带未驳回的反方片段 {ev.excerpt_id}：要么写 rebuttal，要么把 {e.to} 标 contradicted"))
        if e.model_only and any(ev.stance == "supports" for ev in e.evidence):
            out.append(Issue(e.id, "model_only 的边不能带 supports 证据"))
        if not e.model_only and any(ev.stance == "supports" for ev in e.evidence):
            supported_in[e.to] = True

    for n in g.nodes:
        if n.evidence_status == "supported" and inbound.get(n.id) and not supported_in[n.id]:
            out.append(Issue(n.id, "标 supported，但没有任何非 model_only 的入边带 supports 证据"))
    return out


def unanswered_contradictions(graph: Graph | dict, evidence_pack: EvidencePack | dict | None) -> list[Issue]:
    """资料包里的反方片段一条都没被引用 → 非阻断提示（片段可能与所选路径无关）。"""
    if evidence_pack is None:
        return []
    g, pack = parse_graph(graph), parse_pack(evidence_pack)
    cited = {ev.excerpt_id for e in g.edges for ev in e.evidence}
    return [Issue(x.excerpt_id, "资料包里的反方片段没有被回应", blocking=False)
            for x in pack.excerpts if x.stance == "contradicts" and x.excerpt_id not in cited]


# ---- 计划（每个 terminal 一份）-------------------------------------------

def validate_plans(graph: Graph | dict, drafts: list) -> list[Issue]:
    """计划草稿（ProposalDraft，或带同名字段的 TradeProposal）对图的引用：
    - terminal 集合必须恰好等于图上全部 terminal：每个一份，不多不少（阻断）；
    - direction.instrument 必须属于该 terminal 的 instruments（阻断）；
    - 引用的条件和 claim 必须存在，至少一条进场条件（阻断）；
    - 进场条件所在的 claim 应该是该 terminal 的祖先或它自己，否则非阻断提示（条件可以被多份计划共用）。
      离场条件不提示：提示词鼓励互为镜像的条件，对手分支上的信号本来就该当离场条件用（4.6）。"""
    from catalyst.branches import ancestors  # branches 只依赖 schema；放在函数里免得 import 顺序绕圈

    g = parse_graph(graph)
    out: list[Issue] = []
    nodes = {n.id: n for n in g.nodes}
    conds = {c.id: c for c in g.conditions}
    terminals = [n.id for n in g.nodes if n.role == "terminal"]
    seen: list[str] = [d.terminal_id for d in drafts]
    for t in sorted({t for t in seen if seen.count(t) > 1}):
        out.append(Issue(t, f"terminal {t} 有 {seen.count(t)} 份计划：每个 terminal 恰好一份"))
    for t in sorted(set(seen) - set(terminals)):
        what = "不是 terminal 节点" if t in nodes else "不在图里"
        out.append(Issue(t, f"计划的 terminal_id {t} {what}；计划只能挂在这些 terminal 上：{terminals}"))
    for t in terminals:
        if t not in seen:
            out.append(Issue(t, f"terminal {t} 没有计划：图上每个 terminal 都要有一份计划，方向和标的都要写"))
    for d in drafts:
        t = d.terminal_id
        if hasattr(d, "entry_condition_ids"):
            entry, exit_ = list(d.entry_condition_ids), list(d.exit_condition_ids)
        else:
            entry, exit_ = [c.id for c in d.entry_conditions], [c.id for c in d.exit_conditions]
        out += [Issue(i, f"计划 {t} 引用了不存在的条件 {i}") for i in entry + exit_ if i not in conds]
        if not entry:
            out.append(Issue(t, f"计划 {t} 至少要有一条进场条件（空集不会自动通过，但也说明不了还需要什么）"))
        kd = d.key_dependency
        if kd and kd.condition_id and kd.condition_id not in conds:
            out.append(Issue(kd.condition_id, f"计划 {t} 的 key_dependency 引用了不存在的条件"))
        if kd and kd.claim_id and kd.claim_id not in nodes:
            out.append(Issue(kd.claim_id, f"计划 {t} 的 key_dependency 引用了不存在的 claim"))
        if t in nodes and nodes[t].role == "terminal":
            if d.direction.instrument not in nodes[t].instruments:
                out.append(Issue(t, f"计划 {t} 的标的 {d.direction.instrument} 不是这个 terminal 的 instrument："
                                    f"{nodes[t].instruments}"))
            upstream = ancestors(g, t) | {t}
            for i in dict.fromkeys(entry):
                if i in conds and conds[i].claim_id not in upstream:
                    out.append(Issue(i, f"计划 {t} 的进场条件 {i} 挂在 {conds[i].claim_id} 上，它不是 {t} 的上游",
                                     blocking=False))
    return out


def blocking(issues: list[Issue]) -> list[Issue]:
    return [i for i in issues if i.blocking]
