"""分支推导（docs/changes/2026-10-18-branches-and-plans.md 4.2）：纯函数，代码裁决，不由模型标注。

一个 terminal 一条分支。store.bundle、promote、web/scripts/make_fixtures.py 都调用 derive_branches，不另写一份。

- 独有部分：own_node_ids = (ancestors(t) ∪ {t}) − ⋃ ancestors(其他 terminal)；own_edge_ids 是终点落在
  own_node_ids 里的边（这样不会漏掉旁路的根节点）。
- 分叉点：几条出边各自能到达的 terminal 集合不一样的节点。一条分支的 divergence_node_ids 是它祖先里的分叉点。
- kind，按优先级：
  1. hypothetical：ancestors(t) ∪ {t}（含共用上游）里有 role=shock 的节点、情景冲击新增的节点，或用户改过的假设
     （本版本情景 ops 的 target；情景是叠加的，ops 已含祖先版本的）。用户改过的假设会让所有依赖它的分支都变成 hypothetical。
  2. evidenced：独有部分至少有一条边，每条边都不是 model_only 且带 supports 证据；独有节点里没有 contradicted；
     独有边没有引用合成占位资料包的片段。
  3. model_only：其余。合成资料包撑起来的分支也落在这里，并标 synthetic_evidence。
- trunk：共用上游 = ancestors(t) − own_node_ids，以及终点落在其中的边，按 evidenced 的同一规则算；
  共用上游没有边时（例如只共用起点事件）算 evidenced。
"""
from __future__ import annotations

from catalyst.schema import Branch, Graph, Mechanism, Scenario, parse_graph


def _adjacency(g: Graph) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    out_adj: dict[str, list[str]] = {n.id: [] for n in g.nodes}
    in_adj: dict[str, list[str]] = {n.id: [] for n in g.nodes}
    for e in g.edges:
        out_adj.setdefault(e.from_, []).append(e.to)
        in_adj.setdefault(e.to, []).append(e.from_)
    return out_adj, in_adj


def _walk(adj: dict[str, list[str]], start: str) -> set[str]:
    """从 start 沿 adj 能走到的全部节点（不含 start 自己，除非有环——图已校验无环）。"""
    seen: set[str] = set()
    todo = list(adj.get(start, []))
    while todo:
        v = todo.pop()
        if v not in seen:
            seen.add(v)
            todo += adj.get(v, [])
    return seen


def terminals(graph: Graph | dict) -> list[str]:
    g = parse_graph(graph)
    return [n.id for n in g.nodes if n.role == "terminal"]


def ancestors(graph: Graph | dict, node_id: str) -> set[str]:
    g = parse_graph(graph)
    return _walk(_adjacency(g)[1], node_id)


def own_node_ids(graph: Graph | dict, terminal_id: str) -> set[str]:
    g = parse_graph(graph)
    _, in_adj = _adjacency(g)
    others = set().union(*(_walk(in_adj, t) for t in terminals(g) if t != terminal_id))
    return (_walk(in_adj, terminal_id) | {terminal_id}) - others


def divergence_nodes(graph: Graph | dict) -> set[str]:
    g = parse_graph(graph)
    out_adj, _ = _adjacency(g)
    terms = set(terminals(g))
    out = set()
    for n, children in out_adj.items():
        reach = {frozenset((_walk(out_adj, c) | {c}) & terms) for c in children}
        if len(reach) > 1:
            out.add(n)
    return out


def hypothetical_inputs(graph: Graph | dict, scenario: Scenario | dict | None) -> set[str]:
    """会让依赖它的分支变成 hypothetical 的节点：role=shock、情景冲击新增的节点、用户改过的假设。"""
    g = parse_graph(graph)
    out = {n.id for n in g.nodes if n.role == "shock"}
    if scenario is not None:
        s = scenario if isinstance(scenario, Scenario) else Scenario.model_validate(scenario)
        for op in s.ops:
            out |= {n.id for n in op.new_nodes}
            if op.kind == "change_assumption" and op.target:
                out.add(op.target)
    return out


def _evidenced(edges: list[Mechanism], node_status: dict[str, str], node_ids: set[str],
               synthetic_ids: set[str]) -> bool:
    return (all(not e.model_only and any(ev.stance == "supports" for ev in e.evidence) for e in edges)
            and not any(node_status.get(n) == "contradicted" for n in node_ids)
            and not any(ev.excerpt_id in synthetic_ids for e in edges for ev in e.evidence))


def derive_branches(graph: Graph | dict, scenario: Scenario | dict | None = None, *,
                    synthetic_excerpt_ids: set[str] | frozenset[str] = frozenset()) -> list[Branch]:
    """synthetic_excerpt_ids：本版本资料里属于合成占位资料包的片段 id（store 由 observations 的 synthetic 字段给出）。
    返回按图里 terminal 的顺序排列。"""
    g = parse_graph(graph)
    _, in_adj = _adjacency(g)
    terms = terminals(g)
    anc = {t: _walk(in_adj, t) for t in terms}
    hypo = hypothetical_inputs(g, scenario)
    div = divergence_nodes(g)
    status = {n.id: n.evidence_status for n in g.nodes}
    synthetic = set(synthetic_excerpt_ids)
    order = {n.id: i for i, n in enumerate(g.nodes)}
    out = []
    for t in terms:
        others = set().union(*(anc[o] for o in terms if o != t))
        own = (anc[t] | {t}) - others
        shared = anc[t] - own
        own_edges = [e for e in g.edges if e.to in own]
        shared_edges = [e for e in g.edges if e.to in shared]
        uses_synthetic = any(ev.excerpt_id in synthetic for e in own_edges for ev in e.evidence)
        if (anc[t] | {t}) & hypo:
            kind = "hypothetical"
        elif own_edges and _evidenced(own_edges, status, own, synthetic):
            kind = "evidenced"
        else:
            kind = "model_only"
        trunk = "evidenced" if _evidenced(shared_edges, status, shared, synthetic) else "model_only"
        out.append(Branch(
            terminal_id=t, divergence_node_ids=sorted(div & anc[t], key=order.get),
            own_node_ids=sorted(own, key=order.get), own_edge_ids=[e.id for e in own_edges],
            kind=kind, trunk=trunk, synthetic_evidence=uses_synthetic))
    return out
