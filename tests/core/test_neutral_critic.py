"""A：证据立场 neutral（背景信息）；B：Critic 占位（本期不启用、不调模型）。"""
import copy

import pytest

from catalyst import entrypoints as ep
from catalyst import prompts
from catalyst.evidence import EvidenceProvider
from catalyst.schema import TradeProposal, parse_graph
from catalyst.validator import unanswered_contradictions, validate_references
from tests.core.test_harness import CFG, PACK, Scripted, _good

NEUTRAL = {"source_id": "s-b", "excerpt_id": "hz-2", "source": "PortWatch", "date": "2026-10-10", "stance": "neutral",
           "text": "PortWatch 的过境数据每周才更新一次。"}
PACK_N = {**PACK, "excerpts": PACK["excerpts"] + [NEUTRAL]}


def _ref(x, stance=None, rebuttal=None):
    return {"tier": "T2", "source_id": x["source_id"], "excerpt_id": x["excerpt_id"], "stance": stance or x["stance"],
            "supports": "背景", "rebuttal": rebuttal}


def _graph(evidence, status="supported"):
    """h.open → h.transits，边上挂 evidence；h.transits 的 evidence_status 由参数给。"""
    g = _good()
    nodes = [g["nodes"][0], {**g["nodes"][1], "evidence_status": status}]
    edge = {**g["edges"][0], "evidence": evidence, "model_only": False}
    return parse_graph({"version": "t-v1", "op": {"kind": "inspect"}, "nodes": nodes, "edges": [edge], "conditions": []})


def _msgs(issues):
    return [str(i) for i in issues]


@pytest.fixture
def ev():
    e = EvidenceProvider("/nonexistent")
    e.register(PACK_N)
    return e


# ---- A. neutral --------------------------------------------------------

def test_neutral_inbound_alone_cannot_make_a_claim_supported():
    errs = _msgs(validate_references(_graph([_ref(NEUTRAL)]), PACK_N))
    assert any("[h.transits] marked supported, but no non-model_only incoming edge carries supports evidence" in e for e in errs)
    assert not validate_references(_graph([_ref(NEUTRAL)], status="unknown"), PACK_N)


def test_neutral_needs_no_rebuttal_and_is_not_an_unanswered_contradiction():
    supports = {**NEUTRAL, "excerpt_id": "hz-4", "source_id": "s-d", "stance": "supports", "text": "官方确认已有商船通过。"}
    pack = {**PACK_N, "excerpts": PACK_N["excerpts"] + [supports]}
    g = _graph([_ref(supports), _ref(NEUTRAL)])  # supported 的 claim 挂着没有 rebuttal 的 neutral
    assert validate_references(g, pack) == []
    warned = {i.ref for i in unanswered_contradictions(g, pack)}
    assert warned == {"hz-3"}  # 只有真正的反方片段会被提示；没被引用的 neutral 不算


@pytest.mark.parametrize("pack_stance, cited_as", [("neutral", "supports"), ("neutral", "contradicts"),
                                                   ("supports", "neutral"), ("contradicts", "neutral")])
def test_neutral_cannot_be_flipped_either_way(pack_stance, cited_as):
    x = {**NEUTRAL, "stance": pack_stance}
    pack = {**PACK, "excerpts": [x]}
    errs = _msgs(validate_references(_graph([_ref(x, stance=cited_as)], status="unknown"), pack))
    assert any(f"cites the {pack_stance} excerpt hz-2 as {cited_as}: a stance cannot be flipped" in e for e in errs)


def test_inspect_accepts_a_neutral_citation(ev):
    out = _good()
    out["edges"][0]["evidence"].append(_ref(NEUTRAL))
    res = ep.inspect("x", reasoner=Scripted([out]), evidence=ev, config=CFG)
    assert res["ok"] and res["graph"]["edges"][0]["evidence"][1]["stance"] == "neutral"


def test_prompt_explains_neutral():
    assert prompts.PROMPT_VERSION == "p6"
    assert "neutral (background" in prompts.BASE and "A neutral excerpt is not counter-evidence and needs no rebuttal" in prompts.BASE
    assert "neutral evidence does not count as support" in prompts.BASE


# ---- B. Critic 占位 ----------------------------------------------------

class NoModel:
    name = "no-model"

    def complete(self, **_):
        raise AssertionError("Critic 本期不应调用模型")


def test_proposal_always_carries_disabled_critic_without_model_calls(ev):
    r = Scripted([_good()])
    res = ep.inspect("x", reasoner=r, evidence=ev, config=CFG)
    assert res["proposals"][0]["critic"] == {"status": "disabled", "reason": "未启用：不在本期范围", "items": []}
    assert r.stages == ["inspect", "inspect.plan"]  # 没有多出 critic 那一步

    report = ep.critic(res["graph"], res["proposals"][0], reasoner=NoModel(), config=CFG)
    assert report.status == "disabled" and report.items == []


def test_old_proposal_without_critic_still_parses_and_forks(ev):
    base = ep.inspect("x", reasoner=Scripted([_good()]), evidence=ev, config=CFG)
    old = copy.deepcopy(base["proposals"][0])
    old.pop("critic")
    assert TradeProposal.model_validate(old).critic.status == "disabled"

    patch = {"node_updates": [], "edge_updates": [], "condition_updates": [], "next_checks": [],
             "assessment": [{"claim_id": "h.transits", "status": "unresolved", "reason": "r"},
                            {"claim_id": "h.brent", "status": "challenged", "reason": "r"}]}
    op = {"kind": "change_assumption", "target": "h.transits", "value": "推迟"}
    res = ep.fork(base["graph"], op, reasoner=Scripted([patch]), evidence=ev, config=CFG, proposals=[old])
    assert res["ok"] and res["proposals"][0]["critic"]["status"] == "disabled"
