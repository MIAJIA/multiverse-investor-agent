"""Branch derivation (docs/changes/2026-10-18-branches-and-plans.md, section 4.2). Pure functions, decided by code,
never labelled by the model.

One branch per terminal. store.bundle, promote, entrypoints and web/scripts/make_fixtures.py all call derive_views;
nobody keeps a second copy of these rules.

- Own part: own_node_ids = (ancestors(t) ∪ {t}) − ⋃ ancestors(other terminals); own_edge_ids are the edges whose
  target is in own_node_ids (so a side root feeding only this branch is not lost).
- Divergence node: a node whose out-edges reach different sets of terminals. A branch lists the divergence nodes
  among its ancestors.
- kind, by priority:
  1. hypothetical: ancestors(t) ∪ {t} (shared upstream included) contains a role=shock node, a node added by a
     scenario shock, or an assumption the user changed (the target of an op in this version's scenario; scenarios
     stack, so its ops already include the ancestors' ops). A changed assumption makes every branch that depends on
     it hypothetical.
  2. evidenced: the own part has at least one edge; every own edge is not model_only and cites supports evidence;
     no own node is contradicted; no own edge cites an excerpt from a synthetic placeholder pack.
  3. model_only: everything else. Branches backed by a synthetic pack land here and carry synthetic_evidence.
- trunk: the shared upstream = ancestors(t) − own_node_ids plus the edges ending in it, scored with the evidenced
  rule above. A shared upstream with no edges (e.g. only the starting event) counts as evidenced.
- node_kinds / edge_kinds (lookup tables for the UI):
  - hypothetical inputs (shock nodes, scenario-added nodes, changed assumptions) → hypothetical;
  - a node in some branch's own part → that branch's kind;
  - a node on the shared trunk → the weakest trunk among the branches that contain it (model_only < evidenced);
  - an edge takes the kind of its target node.
"""
from __future__ import annotations

from catalyst.schema import Branch, Graph, Mechanism, Scenario, parse_graph

_STRENGTH = {"model_only": 0, "evidenced": 1}


def _adjacency(g: Graph) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    out_adj: dict[str, list[str]] = {n.id: [] for n in g.nodes}
    in_adj: dict[str, list[str]] = {n.id: [] for n in g.nodes}
    for e in g.edges:
        out_adj.setdefault(e.from_, []).append(e.to)
        in_adj.setdefault(e.to, []).append(e.from_)
    return out_adj, in_adj


def _walk(adj: dict[str, list[str]], start: str) -> set[str]:
    """Every node reachable from start along adj, start itself excluded (the graph is validated acyclic)."""
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
    """Nodes that make every branch depending on them hypothetical: role=shock, nodes added by a scenario shock,
    and assumptions the user changed."""
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


def derive_views(graph: Graph | dict, scenario: Scenario | dict | None = None, *,
                 synthetic_excerpt_ids: set[str] | frozenset[str] = frozenset()) -> dict:
    """Everything the version bundle needs from this module, computed in one pass:
    {"branches": [Branch], "node_kinds": {node_id: kind}, "edge_kinds": {edge_id: kind}}.

    synthetic_excerpt_ids: the excerpts of this version that come from a synthetic placeholder pack (the store
    derives them from the `synthetic` flag of the observations file). Branches follow the graph's terminal order."""
    g = parse_graph(graph)
    _, in_adj = _adjacency(g)
    terms = terminals(g)
    anc = {t: _walk(in_adj, t) for t in terms}
    hypo = hypothetical_inputs(g, scenario)
    div = divergence_nodes(g)
    status = {n.id: n.evidence_status for n in g.nodes}
    synthetic = set(synthetic_excerpt_ids)
    order = {n.id: i for i, n in enumerate(g.nodes)}
    branches: list[Branch] = []
    own_kind: dict[str, str] = {}
    trunk_kinds: dict[str, list[str]] = {}
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
        branches.append(Branch(
            terminal_id=t, divergence_node_ids=sorted(div & anc[t], key=order.get),
            own_node_ids=sorted(own, key=order.get), own_edge_ids=[e.id for e in own_edges],
            kind=kind, trunk=trunk, synthetic_evidence=uses_synthetic))
        own_kind.update({n: kind for n in own})
        for n in shared:
            trunk_kinds.setdefault(n, []).append(trunk)

    node_kinds: dict[str, str] = {}
    for n in g.nodes:
        if n.id in hypo:
            node_kinds[n.id] = "hypothetical"
        elif n.id in own_kind:
            node_kinds[n.id] = own_kind[n.id]
        elif n.id in trunk_kinds:
            node_kinds[n.id] = min(trunk_kinds[n.id], key=_STRENGTH.get)
        else:  # not upstream of any terminal; the validator rejects such graphs, this is only a safe default
            node_kinds[n.id] = "model_only"
    edge_kinds = {e.id: node_kinds.get(e.to, "model_only") for e in g.edges}
    return {"branches": branches, "node_kinds": node_kinds, "edge_kinds": edge_kinds}


def derive_branches(graph: Graph | dict, scenario: Scenario | dict | None = None, *,
                    synthetic_excerpt_ids: set[str] | frozenset[str] = frozenset()) -> list[Branch]:
    """Only the branches of derive_views (in graph terminal order)."""
    return derive_views(graph, scenario, synthetic_excerpt_ids=synthetic_excerpt_ids)["branches"]


def dump_views(graph: Graph | dict, scenario: Scenario | dict | None = None, *,
               synthetic_excerpt_ids: set[str] | frozenset[str] = frozenset()) -> dict:
    """derive_views in canonical JSON form, ready to merge into a version bundle or an entrypoint result."""
    v = derive_views(graph, scenario, synthetic_excerpt_ids=synthetic_excerpt_ids)
    return {"branches": [b.dump() for b in v["branches"]], "node_kinds": v["node_kinds"], "edge_kinds": v["edge_kinds"]}
