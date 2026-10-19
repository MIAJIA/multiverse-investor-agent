"""Gap detection after plan B: only model_only branches are researched; hypothetical branches are skipped."""
from catalyst.research import find_gaps, find_gaps_by_branch


def _node(i, role, status="unknown", inst=()):
    return {"id": i, "role": role, "statement": i, "original_statement": i, "evidence_status": status,
            "time_bucket": None, "instruments": list(inst), "label": None}


def _edge(i, a, b, model_only, ev=()):
    return {"id": i, "from": a, "to": b, "channel": "supply", "sign": "+", "lag_days": None, "mechanism": "m",
            "evidence": list(ev), "model_only": model_only}


SUP = {"tier": "T1", "source_id": "s", "excerpt_id": "x1", "stance": "supports", "supports": "p", "rebuttal": None}


def _graph():
    nodes = [_node("ev", "event"), _node("a", "intermediate", "supported"), _node("b", "intermediate"),
             _node("shock", "shock"), _node("ta", "terminal", "supported", ["AAA"]), _node("tb", "terminal", inst=["BBB"]),
             _node("tc", "terminal", inst=["CCC"])]
    edges = [_edge("e1", "ev", "a", False, [SUP]), _edge("e2", "a", "ta", False, [SUP]),
             _edge("e3", "ev", "b", True), _edge("e4", "b", "tb", True),
             _edge("e5", "shock", "tc", True)]
    return {"version": "g-v1", "parent_version": None, "op": {"kind": "inspect"}, "nodes": nodes, "edges": edges,
            "conditions": []}


def test_only_model_only_branches_are_researched():
    gaps = find_gaps_by_branch({"graph": _graph()})
    assert {g["id"] for g in gaps} == {"e3", "e4"}          # evidenced branch ta and hypothetical tc are skipped
    assert {g["id"] for g in find_gaps({"graph": _graph()})} == {"e3", "e4", "e5"}   # old rule would research tc


def test_no_graph_no_gaps():
    assert find_gaps_by_branch({"graph": None}) == []
