"""分叉：写范围在改图之前由代码确定，模型只能在范围内提交补丁。

ChangeAssumption：目标节点 + 它的全部后代 + 这些节点的出边 + 挂在这些节点上的条件。
指向后代、但起点在范围外的入边不在范围内（它描述的是范围外节点的机制）。
AddShock：Stage 1 声明的新节点与新边 + impacts 及其后代 + 这些节点的出边。

越界写入抛 ScopeViolation，不留半截结果；基线图不被原地修改。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from catalyst.schema import Graph, Op, Patch, Scenario, parse_graph
from catalyst.validator import blocking, validate_graph

NODE_FIELDS = {"statement", "label", "time_bucket", "instruments"}  # evidence_status 不由情景推进
EDGE_FIELDS = {"mechanism", "sign", "lag_days", "channel"}
CONDITION_FIELDS = {"comparator", "threshold", "threshold_note", "anchor", "deadline", "observation_window", "rule"}


class ScopeViolation(Exception):
    pass


class PatchInvalid(Exception):
    pass


@dataclass(frozen=True)
class Scope:
    nodes: frozenset[str]
    edges: frozenset[str]
    conditions: frozenset[str]
    new_nodes: frozenset[str] = field(default_factory=frozenset)
    new_edges: frozenset[str] = field(default_factory=frozenset)
    impacts: frozenset[str] = field(default_factory=frozenset)

    def to_dict(self) -> dict:
        return {k: sorted(getattr(self, k)) for k in ("nodes", "edges", "conditions", "new_nodes", "new_edges", "impacts")}


def _descendants(graph: Graph, roots: set[str]) -> set[str]:
    out_adj: dict[str, list[str]] = {}
    for e in graph.edges:
        out_adj.setdefault(e.from_, []).append(e.to)
    seen, todo = set(roots), list(roots)
    while todo:
        for v in out_adj.get(todo.pop(), []):
            if v not in seen:
                seen.add(v)
                todo.append(v)
    return seen


def compute_write_scope(graph: Graph | dict, op: Op | dict) -> Scope:
    g = parse_graph(graph)
    o = op if isinstance(op, Op) else Op.model_validate(op)
    node_ids = {n.id for n in g.nodes}
    if o.kind == "change_assumption":
        if o.target not in node_ids:
            raise ScopeViolation(f"[{o.target}] the change_assumption target is not in the graph")
        nodes = _descendants(g, {o.target})
        new_nodes, new_edges = set(), set()
    elif o.kind == "add_shock":
        missing = [i for i in o.impacts if i not in node_ids]
        if missing:
            raise ScopeViolation(f"[{missing[0]}] an add_shock impact is not in the graph")
        new_nodes = {n.id for n in o.new_nodes}
        new_edges = {e.id for e in o.new_edges}
        if clash := (new_nodes & node_ids) | (new_edges & {e.id for e in g.edges}):
            raise ScopeViolation(f"[{sorted(clash)[0]}] an id added by add_shock clashes with an existing object")
        for e in o.new_edges:  # Stage 1 结构检查：冲击只能从新节点连到声明的 impacts
            if e.from_ not in new_nodes or e.to not in set(o.impacts) | new_nodes:
                raise ScopeViolation(f"[{e.id}] a Stage 1 edge must go from a new node to the impacts: {e.from_} → {e.to}")
        nodes = _descendants(g, set(o.impacts)) | new_nodes
    else:
        raise ScopeViolation(f"[{o.kind}] is not a fork operation")
    edges = {e.id for e in g.edges if e.from_ in nodes} | new_edges
    conditions = {c.id for c in g.conditions if c.claim_id in nodes}
    return Scope(frozenset(nodes), frozenset(edges), frozenset(conditions), frozenset(new_nodes), frozenset(new_edges),
                 frozenset(o.impacts))


def _as_scope(scope) -> Scope:
    if isinstance(scope, Scope):
        return scope
    if isinstance(scope, dict):
        return Scope(*(frozenset(scope.get(k, [])) for k in ("nodes", "edges", "conditions", "new_nodes", "new_edges", "impacts")))
    nodes, edges = scope[0], scope[1]
    return Scope(frozenset(nodes), frozenset(edges), frozenset())


def assessment_issues(graph: Graph, scope: Scope, claim_ids) -> list[str]:
    """assessment 只能写写范围内的 claim（节点）id。一次列出全部错误，并说清楚错在哪、该写哪些，
    这样重写一次就能改对；非法条目不会被代码静默丢掉。"""
    allowed = sorted(scope.nodes)
    edges, conds = {e.id for e in graph.edges} | set(scope.new_edges), {c.id for c in graph.conditions}
    nodes = {n.id for n in graph.nodes}
    out = []
    for cid in dict.fromkeys(claim_ids):  # 去重、保序
        if cid in scope.nodes:
            continue
        if cid in edges:
            what = f"{cid} is an edge, not a claim"
        elif cid in conds:
            what = f"{cid} is a condition, not a claim"
        elif cid in nodes:
            what = f"{cid} is a claim outside the write scope (code writes unaffected for everything outside it)"
        else:
            what = f"{cid} is not a claim in the graph"
        out.append(f"[{cid}] {what}; assessment takes only these claims: {allowed}")
    return out


def next_version(version: str) -> str:
    m = re.fullmatch(r"(.*-v)(\d+)", version)
    return f"{m.group(1)}{int(m.group(2)) + 1}" if m else f"{version}-v2"


def apply_patch(graph: Graph | dict, patch: Patch | dict, scope, *, op: Op | dict | None = None,
                new_version: str | None = None) -> Graph:
    """返回新版本图。注意：条件的 evaluation_status 原样保留——改了阈值或日期的条件要由调用方重新判定
    （entrypoints.fork 会做）。"""
    base = parse_graph(graph)
    p = patch if isinstance(patch, Patch) else Patch.model_validate(patch)
    s = _as_scope(scope)
    data = base.dump()  # 深拷贝：基线对象不动

    if p.base_version != base.version:
        raise ScopeViolation(f"[{p.base_version}] the patch is based on a different version than the current graph {base.version}")

    def update(items: list[dict], updates, allowed_ids, allowed_fields, kind):
        by_id = {x["id"]: x for x in items}
        for u in updates:
            if u.id not in allowed_ids:
                raise ScopeViolation(f"[{u.id}] {kind} is outside the write scope")
            if u.id not in by_id:
                raise ScopeViolation(f"[{u.id}] {kind} does not exist")
            if bad := set(u.fields) - allowed_fields:
                raise ScopeViolation(f"[{u.id}] these {kind} fields cannot be changed: {sorted(bad)}")
            by_id[u.id].update(u.fields)

    for n in p.node_adds:
        if n.id not in s.new_nodes:
            raise ScopeViolation(f"[{n.id}] new node was not declared in Stage 1")
        data["nodes"].append(n.dump())
    for e in p.edge_adds:
        if e.id not in s.new_edges:
            raise ScopeViolation(f"[{e.id}] new edge was not declared in Stage 1")
        if s.impacts and (e.from_ not in s.new_nodes or e.to not in s.impacts | s.new_nodes):
            raise ScopeViolation(f"[{e.id}] a new edge must go from a new node to the impacts: {e.from_} → {e.to}")
        data["edges"].append(e.dump())
    update(data["nodes"], p.node_updates, s.nodes, NODE_FIELDS, "node")
    update(data["edges"], p.edge_updates, s.edges, EDGE_FIELDS, "edge")
    update(data["conditions"], p.condition_updates, s.conditions, CONDITION_FIELDS, "condition")
    if errs := assessment_issues(base, s, list(p.assessment) + list(p.assessment_reason)):
        raise ScopeViolation("; ".join(errs))

    data["version"] = new_version or next_version(base.version)
    data["parent_version"] = base.version
    if op is not None:
        data["op"] = (op if isinstance(op, Op) else Op.model_validate(op)).dump()
    new = Graph.model_validate(data)
    if errs := blocking(validate_graph(new)):
        raise PatchInvalid("; ".join(map(str, errs)))
    return new


def build_scenario(base: Graph, new: Graph, op: Op, patch: Patch, parent: Scenario | None = None) -> Scenario:
    """范围外的 claim 由代码写，不由模型写：基线本身是情景版本（parent）时继承它的值，否则是 unaffected。
    范围内的 claim 用模型这一次给的值。ops 叠加在父情景之后，root_version 指向最初的非情景基线。"""
    assessment = {n.id: "unaffected" for n in new.nodes}
    reasons: dict[str, str] = {}
    if parent:
        assessment.update({k: v for k, v in parent.assessment.items() if k in assessment})
        reasons.update({k: v for k, v in parent.assessment_reason.items() if k in assessment})
    assessment.update(patch.assessment)
    reasons.update(patch.assessment_reason)
    root = (parent.root_version or parent.base_version) if parent else base.version
    return Scenario(version=new.version, base_version=base.version, ops=(list(parent.ops) if parent else []) + [op],
                    assessment=assessment, assessment_reason=reasons, root_version=root)
