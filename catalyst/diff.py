"""两个图版本的结构 diff：按规范化 JSON 的哈希比对节点、边、条件。"""
from __future__ import annotations

import hashlib
import json

from catalyst.schema import Graph, parse_graph


def content_hash(obj: dict) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _index(items) -> dict[str, str]:
    return {x.id: content_hash(x.dump()) for x in items}


def diff(g1: Graph | dict, g2: Graph | dict) -> dict:
    a, b = parse_graph(g1), parse_graph(g2)
    out: dict = {}
    for kind, xa, xb in (("nodes", a.nodes, b.nodes), ("edges", a.edges, b.edges),
                         ("conditions", a.conditions, b.conditions)):
        ha, hb = _index(xa), _index(xb)
        out[f"{kind}_changed"] = sorted(k for k in ha.keys() & hb.keys() if ha[k] != hb[k])
        out[f"{kind}_added"] = sorted(hb.keys() - ha.keys())
        out[f"{kind}_removed"] = sorted(ha.keys() - hb.keys())
    cond_claim = {c.id: c.claim_id for c in a.conditions + b.conditions}
    edge_to = {e.id: e.to for e in a.edges + b.edges}
    out["changed_claim_ids"] = sorted(
        set(out["nodes_changed"]) | set(out["nodes_added"])
        | {edge_to[e] for e in out["edges_changed"] + out["edges_added"] + out["edges_removed"]}
        | {cond_claim[c] for c in out["conditions_changed"] + out["conditions_added"] + out["conditions_removed"]})
    return out
