"""测试侧的图工具：规范化哈希、按 id 取元素、测试自己的写范围参考实现。不 import catalyst。

哈希由测试自己算，不信任核心自报（E3 Non-interference）。
"""
from __future__ import annotations

import copy

from eval import scoring
from eval.scoring import canonical_hash  # noqa: F401  —— 与 runner 用同一套哈希


def element_hashes(graph: dict, normalize=None) -> dict[str, dict[str, str]]:
    """按 id 算每个节点、边、Condition 的哈希。

    normalize：先把图转成规范形式再哈希（依赖核心的测试传 _adapter.canonical_graph，
    即 parse_graph(d).dump()）。两边必须用同一个 normalize，否则默认字段的有无会被当成改动。
    """
    return scoring.element_hashes(normalize(graph) if normalize else graph)


def by_id(items: list[dict]) -> dict[str, dict]:
    return {item["id"]: item for item in items}


def descendants(graph: dict, start: set[str]) -> set[str]:
    children: dict[str, list[str]] = {}
    for e in graph["edges"]:
        children.setdefault(e["from"], []).append(e["to"])
    seen, stack = set(), list(start)
    while stack:
        n = stack.pop()
        for c in children.get(n, []):
            if c not in seen:
                seen.add(c)
                stack.append(c)
    return seen


def reference_write_scope(graph: dict, op: dict) -> dict[str, set[str]]:
    """eval-plan / INTERFACE.md 决定 D4 的参考实现，只用来复核 golden fixture 自己没算错。"""
    if op["kind"] == "change_assumption":
        roots, new_nodes, new_edges = {op["target"]}, set(), set()
    elif op["kind"] == "add_shock":
        roots = set(op["impacts"])
        new_nodes = {n["id"] for n in op.get("new_nodes", [])}
        new_edges = {e["id"] for e in op.get("new_edges", [])}
    else:
        raise ValueError(op["kind"])
    nodes = roots | descendants(graph, roots)
    edges = {e["id"] for e in graph["edges"] if e["from"] in nodes}
    conditions = {c["id"] for c in graph.get("conditions", []) if c["claim_id"] in nodes}
    return {"nodes": nodes | new_nodes, "edges": edges | new_edges, "conditions": conditions}


def apply_mutation(graph: dict, node_updates=(), edge_updates=()) -> dict:
    """测试侧修改（构造坏图用），不经核心。"""
    g = copy.deepcopy(graph)
    nodes, edges = by_id(g["nodes"]), by_id(g["edges"])
    for u in node_updates:
        nodes[u["id"]].update(copy.deepcopy(u["fields"]))
    for u in edge_updates:
        edges[u["id"]].update(copy.deepcopy(u["fields"]))
    return g


def is_acyclic(graph: dict) -> bool:
    indeg = {n["id"]: 0 for n in graph["nodes"]}
    children: dict[str, list[str]] = {}
    for e in graph["edges"]:
        indeg[e["to"]] += 1
        children.setdefault(e["from"], []).append(e["to"])
    queue = [n for n, d in indeg.items() if d == 0]
    visited = 0
    while queue:
        n = queue.pop()
        visited += 1
        for c in children.get(n, []):
            indeg[c] -= 1
            if indeg[c] == 0:
                queue.append(c)
    return visited == len(indeg)
