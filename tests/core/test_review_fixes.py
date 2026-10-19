"""core review 复现过的问题，每条一个回归测试。"""
import copy
import datetime as dt
import json

import pytest

from catalyst import entrypoints as ep
from catalyst.conditions import evaluate
from catalyst.diff import diff
from catalyst.fork import ScopeViolation, apply_patch, compute_write_scope
from catalyst.schema import parse_graph
from catalyst.store import RunStore
from tests.core.test_harness import CFG, PACK, Scripted, _good

OBS = [{"source": "portwatch.hormuz.daily_transits", "coverage": {"start": "2026-10-01", "end": "2026-12-31"},
        "records": [{"date": "2026-10-20", "value": 15, "excerpt_id": None}]}]


@pytest.fixture
def ev():
    from catalyst.evidence import EvidenceProvider
    e = EvidenceProvider("/nonexistent")
    e.register(PACK)
    return e


def _met_cfg():
    return ep.Config(packs=["hz"], today="2026-10-25", run_prefix="d1", observations=OBS)


def test_p0_fork_reevaluates_conditions_and_gate(ev):
    base = ep.inspect("x", reasoner=Scripted([_good(threshold=10)]), evidence=ev, config=_met_cfg())
    assert base["proposals"][0]["gate"] == "READY_FOR_REVIEW" and base["proposals"][0]["status"] == "needs_review"
    patch = {"node_updates": [], "edge_updates": [], "next_checks": [],
             "condition_updates": [{"id": "cond.transits", "threshold": 30}],
             "assessment": [{"claim_id": "h.transits", "status": "challenged", "reason": "门槛提高"},
                            {"claim_id": "h.brent", "status": "unresolved", "reason": "上游未定"}]}
    op = {"kind": "change_assumption", "target": "h.transits", "value": "需要更高的过境量"}
    res = ep.fork(base["graph"], op, reasoner=Scripted([patch]), evidence=ev, config=_met_cfg(), proposals=base["proposals"])
    assert res["ok"]
    assert res["proposals"][0]["entry_conditions"][0]["evaluation_status"] == "unknown"  # 15 < 30，窗口未结束
    assert res["proposals"][0]["gate"] == "WAIT" and res["proposals"][0]["status"] == "draft"


def test_p0_model_cannot_confirm_for_user(ev):
    out = _good()
    out["proposals"][0]["user_judgment"] = {"original_statement": "霍尔木兹海峡下周重开",
                                        "clarified_statement": "2026-11-30 前过境恢复", "criteria": None,
                                        "deadline": "2026-11-30", "requires_user_confirmation": False}
    res = ep.inspect("x", reasoner=Scripted([out]), evidence=ev, config=CFG)
    uj = res["proposals"][0]["user_judgment"]
    assert uj["confirmed"] is False and uj["confirmed_claim_ids"] == [] and uj["probability"] is None
    assert uj["requires_user_confirmation"] is True  # 原话被改写过


def test_p0_model_output_with_confirmation_fields_is_rejected(ev):
    out = _good()
    out["proposals"][0]["user_judgment"].update(confirmed=True, probability=0.7)  # 模型输出 schema 没有这些字段
    res = ep.inspect("x", reasoner=Scripted([out] * 3), evidence=ev, config=CFG)
    assert not res["ok"] and any("confirmed" in e for e in res["errors"])


def test_p0_stance_cannot_be_flipped(ev):
    out = _good()
    out["edges"][0]["evidence"][0]["stance"] = "supports"  # hz-3 在资料包里是 contradicts
    out["nodes"][1]["evidence_status"] = "supported"
    res = ep.inspect("x", reasoner=Scripted([out] * 3), evidence=ev, config=CFG)
    assert not res["ok"] and any("a stance cannot be flipped" in e for e in res["errors"])


def test_p0_fork_without_pack_still_works(ev):
    base = ep.inspect("x", reasoner=Scripted([_good()]), evidence=ev, config=CFG)
    patch = {"node_updates": [{"id": "h.transits", "statement": "推迟到 12 月"}], "edge_updates": [],
             "condition_updates": [], "next_checks": [],
             "assessment": [{"claim_id": "h.transits", "status": "challenged", "reason": "推迟"},
                            {"claim_id": "h.brent", "status": "challenged", "reason": "上游推迟"}]}
    op = {"kind": "change_assumption", "target": "h.transits", "value": "推迟"}
    res = ep.fork(base["graph"], op, reasoner=Scripted([patch]), evidence=None)  # runner 的调用方式
    assert res["ok"], res["errors"]


def test_p0_invalid_deadline_does_not_crash(ev):
    out = _good()
    c = out["conditions"][0]
    c.update(predicate="at_deadline", deadline="scenario:open+72h")
    res = ep.inspect("x", reasoner=Scripted([out] * 3), evidence=ev, config=CFG)
    assert not res["ok"] and any("deadline" in e for e in res["errors"])


def test_p0_inspect_accepts_packs_kwarg(ev):
    res = ep.inspect("x", reasoner=Scripted([_good()]), evidence=ev, packs=["hz"])
    assert res["ok"] and res["observations"] == ["hz-1", "hz-3"]


def test_p1_validation_errors_point_at_fields(ev):
    out = _good()
    out["nodes"][0]["role"] = "banana"
    r = Scripted([out, _good()])
    ep.inspect("x", reasoner=r, evidence=ev, config=CFG)
    assert "[nodes.0.role]" in r.prompts[1]


def test_p1_at_deadline_ignores_valueless_record_and_window_end():
    cond = {**_good(threshold=10)["conditions"][0], "predicate": "at_deadline", "evaluation_status": "unknown",
            "observation_window": {"start": "2026-10-18", "end": "2026-11-10"}}
    obs = [{"source": "portwatch.hormuz.daily_transits", "coverage": {"start": "2026-10-01", "end": "2026-12-31"},
            "records": [{"date": "2026-11-05", "value": 15}, {"date": "2026-11-25", "value": 5}]}]
    assert evaluate(cond, obs, dt.date(2026, 12, 1)) == "not_met"  # 截止日前最近一条是 5，不是窗口内的 15
    obs[0]["records"].append({"date": "2026-11-29", "value": None})
    assert evaluate(cond, obs, dt.date(2026, 12, 1)) == "unknown"


def test_p1_root_cannot_be_supported(ev):
    out = _good()
    out["nodes"][0]["evidence_status"] = "supported"
    res = ep.inspect("x", reasoner=Scripted([out] * 3), evidence=ev, config=CFG)
    assert not res["ok"] and any("h.open" in e for e in res["errors"])


def test_p1_two_forks_in_one_store_get_distinct_versions(ev, tmp_path):
    store = RunStore(tmp_path)
    base = ep.inspect("x", reasoner=Scripted([_good()]), evidence=ev, config=CFG, store=store)
    patch = {"node_updates": [], "edge_updates": [], "condition_updates": [], "next_checks": [],
             "assessment": [{"claim_id": "h.transits", "status": "unresolved", "reason": "-"},
                            {"claim_id": "h.brent", "status": "unaffected", "reason": "-"}]}
    op = {"kind": "change_assumption", "target": "h.transits", "value": "a"}
    v = [ep.fork(base["graph"], op, reasoner=Scripted([patch]), evidence=ev, config=CFG, store=store)["graph"]["version"]
         for _ in range(2)]
    assert v == ["d1-v2", "d1-v3"]


def test_p1_stage1_new_edge_must_start_at_new_node():
    g = parse_graph(_good_graph())
    op = {"kind": "add_shock", "impacts": ["h.brent"],
          "new_nodes": [{"id": "s.x", "role": "shock", "statement": "s", "original_statement": "s", "evidence_status": "unknown"}],
          "new_edges": [{"id": "s.e1", "from": "h.open", "to": "h.brent", "channel": "supply", "sign": "-",
                         "mechanism": "m", "model_only": True}]}
    with pytest.raises(ScopeViolation):
        compute_write_scope(g, op)


def test_p1_scope_error_is_structured(ev):
    base = ep.inspect("x", reasoner=Scripted([_good()]), evidence=ev, config=CFG)
    res = ep.fork(base["graph"], {"kind": "change_assumption", "target": "nope"}, reasoner=Scripted([]), evidence=ev)
    assert not res["ok"] and "nope" in res["errors"][0]


def test_p2_edge_only_change_is_visible_in_changed_claims():
    a = parse_graph(_good_graph())
    b = a.model_copy(deep=True)
    b.edges[1].mechanism = "偷改的机制"
    assert diff(a, b)["changed_claim_ids"] == ["h.brent"]


def _good_graph():
    out = _good()
    conds = [{**c, "evaluation_status": "unknown"} for c in out["conditions"]]
    return {"version": "d1-v1", "parent_version": None, "op": {"kind": "inspect"}, "nodes": out["nodes"],
            "edges": out["edges"], "conditions": conds}
