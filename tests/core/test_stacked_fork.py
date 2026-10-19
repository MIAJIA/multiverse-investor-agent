"""情景叠加：在一个分叉版本上再分叉，上一层的「受挑战」不能因为这一层没涉及就被抹掉。"""
import pytest

from catalyst import entrypoints as ep
from catalyst.evidence import EvidenceProvider
from catalyst.schema import Scenario
from catalyst.store import RunStore
from tests.core.test_harness import CFG, PACK, Scripted, _good  # noqa: F401

# 图：h.open → h.transits → h.brent；提案的进场条件挂在 h.transits 上。
LAYER1 = {"kind": "change_assumption", "target": "h.transits", "value": "过境恢复推迟到 12 月"}  # 范围 {transits, brent}
LAYER2 = {"kind": "change_assumption", "target": "h.brent", "value": "需求端同时走弱"}  # 范围 {brent}


def _patch(*assessment, node_updates=()):
    return {"node_updates": list(node_updates), "edge_updates": [], "condition_updates": [], "next_checks": ["查证"],
            "assessment": [{"claim_id": c, "status": s, "reason": f"{c}:{s}"} for c, s in assessment]}


def _base():
    """进场条件所在的 h.transits 不带证据上的「受挑战」：反方片段写了 rebuttal、状态是 unknown。
    这样 support_status 只取决于情景 assessment，才能看出叠加有没有丢。"""
    out = _good()
    out["nodes"][1]["evidence_status"] = "unknown"
    out["edges"][0]["evidence"][0]["rebuttal"] = "上次是部分开放，这次是全面开放"
    return out


P1 = _patch(("h.transits", "challenged"), ("h.brent", "unresolved"))
P2 = _patch(("h.brent", "challenged"))


@pytest.fixture
def ev():
    e = EvidenceProvider("/nonexistent")
    e.register(PACK)
    return e


def _two_layers(ev, store=None):
    v1 = ep.inspect("x", reasoner=Scripted([_base()]), evidence=ev, config=CFG, store=store)
    v2 = ep.fork(v1["graph"], LAYER1, reasoner=Scripted([P1]), evidence=ev, config=CFG, proposals=v1["proposals"],
                 store=store)
    v3 = ep.fork(v2["graph"], LAYER2, reasoner=Scripted([P2]), evidence=ev, config=CFG, proposals=v2["proposals"],
                 scenario=None if store else v2["scenario"], store=store)
    return v1, v2, v3


def _challenged(res):
    return sorted(k for k, v in res["scenario"]["assessment"].items() if v == "challenged")


def test_second_layer_keeps_first_layer_challenges(ev):
    v1, v2, v3 = _two_layers(ev)
    assert v3["ok"] and v3["scope"]["nodes"] == ["h.brent"]  # 这一层根本没碰 h.transits
    assert _challenged(v2) == ["h.transits"]
    assert _challenged(v3) == ["h.brent", "h.transits"]
    s = v3["scenario"]
    assert s["base_version"] == "d1-v2" and s["root_version"] == "d1-v1"
    assert [o["kind"] for o in s["ops"]] == ["change_assumption", "change_assumption"]
    assert [o["target"] for o in s["ops"]] == ["h.transits", "h.brent"]
    assert s["assessment"]["h.open"] == "unaffected"
    assert s["assessment_reason"]["h.transits"] == "h.transits:challenged"  # 理由跟着继承

    ref = v3["proposals"][0]["scenario_ref"]
    assert ref["base_version"] == "d1-v2" and ref["root_version"] == "d1-v1"
    assert ref["challenged_claim_ids"] == ["h.brent", "h.transits"]
    # 进场条件挂在 h.transits 上：它是第一层挑战的，第二层没碰，提案仍然是 challenged
    assert v3["proposals"][0]["support_status"] == "challenged"


def test_without_stacking_the_entry_claim_would_look_unchallenged(ev):
    """对照：直接在 v1 上做第二层操作，h.transits 不受挑战，scenario_ref 里只有 h.brent。
    （方案 B 4.4 之后 support_status 也看分支独有的 claim，terminal h.brent 受挑战就已经是 challenged，
    所以这里改成比 challenged_claim_ids。）"""
    v1 = ep.inspect("x", reasoner=Scripted([_base()]), evidence=ev, config=CFG)
    alone = ep.fork(v1["graph"], LAYER2, reasoner=Scripted([P2]), evidence=ev, config=CFG, proposals=v1["proposals"])
    assert _challenged(alone) == ["h.brent"]
    assert alone["proposals"][0]["scenario_ref"]["challenged_claim_ids"] == ["h.brent"]
    assert alone["scenario"]["root_version"] == "d1-v1" and len(alone["scenario"]["ops"]) == 1


def test_parent_scenario_is_read_from_the_store(ev, tmp_path):
    _, _, v3 = _two_layers(ev, store=RunStore(tmp_path))
    assert _challenged(v3) == ["h.brent", "h.transits"]
    assert v3["proposals"][0]["support_status"] == "challenged"


def test_stacked_prompt_shows_the_inherited_assessment(ev):
    v1 = ep.inspect("x", reasoner=Scripted([_base()]), evidence=ev, config=CFG)
    v2 = ep.fork(v1["graph"], LAYER1, reasoner=Scripted([P1]), evidence=ev, config=CFG)
    r = Scripted([P2])
    ep.fork(v2["graph"], LAYER2, reasoner=r, evidence=ev, config=CFG, scenario=v2["scenario"])
    assert "叠加" in r.prompts[0] and '"h.transits": "challenged"' in r.prompts[0]


def test_in_scope_downgrade_uses_the_model_value_but_warns(ev):
    v1 = ep.inspect("x", reasoner=Scripted([_base()]), evidence=ev, config=CFG)
    v2 = ep.fork(v1["graph"], LAYER1, reasoner=Scripted([P1]), evidence=ev, config=CFG)
    again = _patch(("h.transits", "unaffected"), ("h.brent", "unresolved"))  # 同一个范围，模型明确改了 h.transits
    v3 = ep.fork(v2["graph"], LAYER1, reasoner=Scripted([again]), evidence=ev, config=CFG, scenario=v2["scenario"])
    assert v3["ok"] and v3["scenario"]["assessment"]["h.transits"] == "unaffected"
    assert any("[h.transits]" in w and "回到更早的版本" in w for w in v3["warnings"])


def test_scenario_of_another_version_is_rejected(ev):
    v1 = ep.inspect("x", reasoner=Scripted([_base()]), evidence=ev, config=CFG)
    v2 = ep.fork(v1["graph"], LAYER1, reasoner=Scripted([P1]), evidence=ev, config=CFG)
    res = ep.fork(v1["graph"], LAYER2, reasoner=Scripted([P2]), evidence=ev, config=CFG, scenario=v2["scenario"])
    assert not res["ok"] and res["graph"] is None and "d1-v2" in res["errors"][0]


def test_sign_carries_the_scenario_so_forking_after_sign_still_stacks(ev, tmp_path):
    store = RunStore(tmp_path)
    v1 = ep.inspect("x", reasoner=Scripted([_base()]), evidence=ev, config=CFG, store=store)
    v2 = ep.fork(v1["graph"], LAYER1, reasoner=Scripted([P1]), evidence=ev, config=CFG, proposals=v1["proposals"],
                 store=store)
    signed = ep.sign(v2["graph"], v2["proposals"], terminal_id="h.brent", clarified_statement="12 月前过境恢复", criteria=None,
                     deadline="2026-11-30", confirmed_claim_ids=["h.transits"], config=CFG, store=store)
    assert signed["ok"] and store.bundle(signed["version"])["scenario"]["base_version"] == "d1-v2"
    v4 = ep.fork(signed["graph"], LAYER2, reasoner=Scripted([P2]), evidence=ev, config=CFG,
                 proposals=signed["proposals"], store=store)
    assert _challenged(v4) == ["h.brent", "h.transits"] and v4["scenario"]["root_version"] == "d1-v1"
    assert [o["kind"] for o in v4["scenario"]["ops"]] == ["change_assumption", "change_assumption"]


def test_old_scenarios_without_root_version_still_parse():
    old = {"version": "c1-v2", "base_version": "c1-v1", "ops": [{"kind": "change_assumption", "target": "a"}],
           "assessment": {"a": "challenged"}}
    s = Scenario.model_validate(old)
    assert s.root_version is None


def test_api_fork_on_a_fork_stacks(tmp_path, monkeypatch):
    """前端走的路径：POST /fork 以 v2 为基线，bundle 里的情景被带进去。"""
    from catalyst import api
    monkeypatch.setattr(api, "RUNS", tmp_path / "api")
    r = Scripted([_base(), P1, P2])
    monkeypatch.setattr(api, "_reasoner", lambda store: r)

    def provider(packs):
        e = EvidenceProvider("/nonexistent")
        e.register(PACK)
        return e, ["hz"], []
    monkeypatch.setattr(api, "_provider", provider)

    run = api.create_run({"event": "x", "target": "BZ", "today": "2026-10-18"})["run_id"]
    v2 = api.fork_run(run, {"base_version": "r-v1", "op": LAYER1})
    v3 = api.fork_run(run, {"base_version": v2["version"], "op": LAYER2})
    assert v3["ok"], v3["errors"]
    b3 = api._store(run).bundle(v3["version"])
    assert b3["scenario"]["root_version"] == "r-v1" and len(b3["scenario"]["ops"]) == 2
    assert b3["proposals"][0]["scenario_ref"]["challenged_claim_ids"] == ["h.brent", "h.transits"]
    assert b3["proposals"][0]["support_status"] == "challenged"
