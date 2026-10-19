"""The user's own belief is not a source of "hypothetical"; other not-yet-happened events still are."""
from catalyst.branches import derive_views, user_event_nodes


def _n(i, role, orig, inst=()):
    return {"id": i, "role": role, "statement": orig, "original_statement": orig, "evidence_status": "unknown",
            "time_bucket": None, "instruments": list(inst), "label": i}


def _e(i, a, b):
    return {"id": i, "from": a, "to": b, "channel": "supply", "sign": "+", "lag_days": None, "mechanism": "m",
            "evidence": [], "model_only": True}


EVENT = "I think the Strait of Hormuz is going to open up next week"


def _graph(user_event=EVENT):
    nodes = [_n("open", "shock", EVENT), _n("transits", "intermediate", "transits recover"),
             _n("pipeline", "shock", "Saudi pipeline is attacked again"),
             _n("a", "terminal", "Brent falls", ["BZ"]), _n("b", "terminal", "Brent stays high", ["BZ"])]
    edges = [_e("e1", "open", "transits"), _e("e2", "transits", "a"), _e("e3", "open", "pipeline"), _e("e4", "pipeline", "b")]
    return {"version": "d1-v1", "op": {"kind": "inspect", "value": user_event}, "nodes": nodes, "edges": edges,
            "conditions": [], "user_event": user_event}


def test_user_event_does_not_paint_the_graph_hypothetical():
    kinds = {b.terminal_id: b.kind for b in derive_views(_graph())["branches"]}
    assert kinds == {"a": "model_only", "b": "hypothetical"}   # only the extra pipeline attack is hypothetical
    assert user_event_nodes(_graph()) == {"open"}


def test_without_user_event_old_behaviour_holds():
    kinds = {b.terminal_id: b.kind for b in derive_views(_graph(user_event=None))["branches"]}
    assert kinds == {"a": "hypothetical", "b": "hypothetical"}


def test_matching_ignores_case_whitespace_and_final_punctuation():
    g = _graph(user_event="  i think the strait of hormuz is going to open up   next week. ")
    assert user_event_nodes(g) == {"open"}


def test_changing_the_user_event_in_a_fork_still_makes_it_hypothetical():
    scenario = {"version": "d1-v2", "base_version": "d1-v1", "assessment": {},
                "ops": [{"kind": "change_assumption", "target": "open", "value": "it opens next year"}]}
    kinds = {b.terminal_id: b.kind for b in derive_views(_graph(), scenario)["branches"]}
    assert kinds == {"a": "hypothetical", "b": "hypothetical"}
