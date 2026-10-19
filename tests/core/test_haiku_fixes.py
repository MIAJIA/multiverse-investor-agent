"""Haiku 真实运行（eval/out/haiku-full）暴露的 5 个问题，每个一组回归测试。全部离线，不调模型。"""
import copy
import json
from types import SimpleNamespace

import anthropic
import httpx2 as httpx
import pytest

from catalyst import entrypoints as ep
from catalyst import prompts
from catalyst.evidence import EvidenceProvider
from catalyst.fork import ScopeViolation, apply_patch, compute_write_scope
from catalyst.reasoner import AnthropicReasoner, strict_schema
from catalyst.schema import Claim, InspectGraphOutput, InspectPlanOutput, Patch, parse_graph
from tests.core.test_harness import CFG, PACK, Scripted, _good


@pytest.fixture
def ev():
    e = EvidenceProvider("/nonexistent")
    e.register(PACK)
    return e


def _unions(schema) -> int:
    n = 0
    if isinstance(schema, dict):
        n += isinstance(schema.get("type"), list) or "anyOf" in schema
        n += sum(_unions(v) for v in schema.values())
    elif isinstance(schema, list):
        n += sum(_unions(v) for v in schema)
    return n


# ---- 1. Inspect 的结构化输出 ------------------------------------------------

def _bad_request(message: str) -> anthropic.BadRequestError:
    body = {"type": "error", "error": {"type": "invalid_request_error", "message": message}}
    resp = httpx.Response(400, json=body, request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"))
    return anthropic.BadRequestError(message, response=resp, body=body)


def _reasoner(error: Exception):
    r = object.__new__(AnthropicReasoner)  # 不建 client，_stream 换成假的
    r.calls = []

    def stream(system, user, output_format):
        r.calls.append(output_format)
        if output_format is not None:
            raise error
        return SimpleNamespace(content=[SimpleNamespace(type="text", text="{}")], model="m", stop_reason="end_turn",
                               usage=None)
    r._stream = stream
    return r


def test_schema_fallback_records_the_api_reason():
    msg = "The compiled grammar is too large, which would cause performance issues."
    r = _reasoner(_bad_request(msg))
    out = r.complete(stage="inspect", system="s", user="u", schema={"type": "object"})
    assert out.meta["mode"] == "prompt_json" and out.meta["schema_fallback_reason"] == msg
    assert r.calls[0] is not None and r.calls[1] is None  # 先试 json_schema，再退回提示词约束


def test_non_schema_bad_request_is_not_swallowed():
    r = _reasoner(_bad_request("max_tokens: must be positive"))
    with pytest.raises(anthropic.BadRequestError):
        r.complete(stage="inspect", system="s", user="u", schema={"type": "object"})


def test_inspect_runs_two_stages_with_schemas_under_the_union_limit(ev):
    seen = {}

    class Spy(Scripted):
        def complete(self, *, stage, system, user, schema):
            seen[stage] = schema
            return super().complete(stage=stage, system=system, user=user, schema=schema)

    res = ep.inspect("x", reasoner=Spy([_good()]), evidence=ev, config=CFG)
    assert res["ok"] and list(seen) == ["inspect", "inspect.plan"]
    assert seen["inspect"] == InspectGraphOutput.model_json_schema(by_alias=True)
    assert seen["inspect.plan"] == InspectPlanOutput.model_json_schema(by_alias=True)
    for schema in seen.values():  # API 的硬上限是 16 个 union 参数
        assert _unions(strict_schema(schema)) <= 16


def test_plan_stage_sees_the_validated_graph_and_graph_errors_skip_it(ev):
    r = Scripted([_good()])
    ep.inspect("x", reasoner=r, evidence=ev, config=CFG)
    assert '"h.transits"' in r.prompts[1] and "Step 2" in r.prompts[1]

    bad = _good()
    bad["edges"][0]["evidence"][0]["excerpt_id"] = "hz-999"
    r = Scripted([bad] * 3)
    res = ep.inspect("x", reasoner=r, evidence=ev, config=CFG)
    assert not res["ok"] and r.stages == ["inspect"] * 3  # 图不过，就不出条件和提案


def test_no_chain_stops_after_graph_stage(ev):
    r = Scripted([{"no_chain": True, "no_chain_reason": "资料包与事件无关", "nodes": [], "edges": []}])
    res = ep.inspect("x", reasoner=r, evidence=ev, config=CFG)
    assert res["ok"] and res["no_chain"] and res["proposals"] == [] and r.stages == ["inspect"]


# ---- 2. 条件的 anchor -------------------------------------------------------

def test_rule5_anchors_absolute_windows_on_dates():
    assert prompts.PROMPT_VERSION != "p2"
    assert "anchor and observation_window.start are today's date" in prompts.BASE
    assert "it is not a starting point: do not turn it into a scenario anchor" in prompts.BASE


def test_all_scenario_anchors_warn_but_do_not_block(ev):
    out = _good()
    c = out["conditions"][0]
    c.update(anchor="scenario:开放", observation_window={"start": "scenario:开放", "end": "2026-11-30"})
    res = ep.inspect("x", reasoner=Scripted([out]), evidence=ev, config=CFG)
    assert res["ok"] and any("every condition is anchored on scenario" in w for w in res["warnings"])

    res = ep.inspect("x", reasoner=Scripted([_good()]), evidence=ev, config=CFG)
    assert not any("every condition is anchored on scenario" in w for w in res["warnings"])


# ---- 3. 分叉的 assessment 只写 claim ----------------------------------------

OP = {"kind": "change_assumption", "target": "h.transits", "value": "过境恢复推迟到 12 月"}


def _fork_out(assessment):
    return {"node_updates": [], "edge_updates": [], "condition_updates": [], "next_checks": [],
            "assessment": [{"claim_id": c, "status": s, "reason": "r"} for c, s in assessment]}


def test_fork_prompt_lists_claims_and_errors_name_edges_and_conditions(ev):
    base = ep.inspect("x", reasoner=Scripted([_good()]), evidence=ev, config=CFG)
    bad = _fork_out([("h.transits", "unresolved"), ("h.brent", "challenged"),
                     ("h.e2", "challenged"), ("cond.transits", "unresolved")])
    good = _fork_out([("h.transits", "unresolved"), ("h.brent", "challenged")])
    r = Scripted([bad, good])
    res = ep.fork(base["graph"], OP, reasoner=r, evidence=ev, config=CFG)
    assert res["ok"] and res["attempts"] == 2
    assert 'Claim ids that need an assessment' in r.prompts[0] and '["h.brent", "h.transits"]' in r.prompts[0]
    retry = r.prompts[1]  # 两条错误一次给全，并说清楚该写哪些
    assert "h.e2 is an edge, not a claim; assessment takes only these claims: ['h.brent', 'h.transits']" in retry
    assert "cond.transits is a condition, not a claim" in retry


def test_illegal_assessment_entries_are_rejected_not_dropped(ev):
    base = ep.inspect("x", reasoner=Scripted([_good()]), evidence=ev, config=CFG)
    bad = _fork_out([("h.transits", "unresolved"), ("h.brent", "challenged"), ("h.e2", "challenged")])
    res = ep.fork(base["graph"], OP, reasoner=Scripted([bad] * 3), evidence=ev, config=CFG)
    assert not res["ok"] and res["graph"] is None and any("h.e2 is an edge" in e for e in res["errors"])

    out_of_scope = _fork_out([("h.transits", "unresolved"), ("h.brent", "challenged"), ("h.open", "unaffected")])
    res = ep.fork(base["graph"], OP, reasoner=Scripted([out_of_scope] * 3), evidence=ev, config=CFG)
    assert not res["ok"] and any("h.open is a claim outside the write scope" in e for e in res["errors"])


def test_apply_patch_reports_every_bad_assessment_entry(ev):
    g = parse_graph(ep.inspect("x", reasoner=Scripted([_good()]), evidence=ev, config=CFG)["graph"])
    scope = compute_write_scope(g, OP)
    patch = Patch(base_version=g.version, assessment={"h.brent": "challenged", "h.e2": "challenged", "nope": "unresolved"})
    with pytest.raises(ScopeViolation) as e:
        apply_patch(g, patch, scope)
    assert "h.e2 is an edge" in str(e.value) and "nope is not a claim in the graph" in str(e.value)


def test_fork_prompt_says_inputs_are_not_challenged():
    assert "assessment takes claim (node) ids only" in prompts.FORK
    assert "inputs of the scenario, not things the scenario challenges" in prompts.FORK


# ---- 4. Discover 的弃权边界 -------------------------------------------------

def test_discover_prompt_separates_hypothesis_from_abstain():
    d = prompts.DISCOVER
    assert "only when no plausible mechanism connects the event" in d
    for not_a_reason in ("The pack has no supporting excerpt: label it hypothesis", "not a reason to abstain in Discover", "needs the user's confirmation"):
        assert not_a_reason in d


def test_hypothesis_candidate_without_excerpts_is_valid(ev):
    out = {"abstained": False, "abstain_reason": None, "candidates": [
        {"id": "d.tankers", "direction": "油轮运价回落", "instruments": ["FRO"], "label": "hypothesis",
         "rationale": "机制合理，资料包里还没有运价片段", "excerpt_ids": []}]}
    res = ep.discover("x", reasoner=Scripted([out]), evidence=ev, config=CFG)
    assert res["ok"] and res["candidates"][0]["label"] == "hypothesis"


# ---- 5. 节点短标题 label ----------------------------------------------------

def test_old_claims_without_label_still_parse():
    old = {"id": "a", "role": "event", "statement": "s", "original_statement": "s", "evidence_status": "unknown",
           "time_bucket": None, "instruments": []}
    assert Claim.model_validate(old).label is None
    g = _good()
    for n in g["nodes"]:
        n.pop("label")
    graph = {"version": "v1", "op": {"kind": "inspect"}, "nodes": g["nodes"], "edges": g["edges"], "conditions": []}
    assert all(n.label is None for n in parse_graph(graph).nodes)


def test_inspect_requires_label_and_warns_when_too_long(ev):
    missing = _good()
    missing["nodes"][0]["label"] = None
    r = Scripted([missing, _good()])
    res = ep.inspect("x", reasoner=r, evidence=ev, config=CFG)
    assert res["ok"] and r.stages[:2] == ["inspect", "inspect"] and "[h.open] every node needs a label" in r.prompts[1]
    assert res["graph"]["nodes"][0]["label"] == "宣布重新开放"

    long = _good()
    long["nodes"][0]["label"] = "霍尔木兹海峡官方宣布对商船重新开放"
    long["nodes"][2]["label"] = "Brent front month weakens sharply"
    res = ep.inspect("x", reasoner=Scripted([long]), evidence=ev, config=CFG)
    assert res["ok"] and res["graph"]["nodes"][0]["label"] == long["nodes"][0]["label"]  # 不由代码截断
    warned = [w for w in res["warnings"] if "label" in w]
    assert len(warned) == 2 and "[h.open]" in warned[0] and "[h.brent]" in warned[1]


def test_fork_patch_can_update_label(ev):
    base = ep.inspect("x", reasoner=Scripted([_good()]), evidence=ev, config=CFG)
    out = _fork_out([("h.transits", "unresolved"), ("h.brent", "challenged")])
    out["node_updates"] = [{"id": "h.transits", "statement": "过境恢复推迟到 12 月", "label": "过境推迟"}]
    res = ep.fork(base["graph"], OP, reasoner=Scripted([out]), evidence=ev, config=CFG)
    assert res["ok"] and res["diff"]["nodes_changed"] == ["h.transits"]
    assert next(n for n in res["graph"]["nodes"] if n["id"] == "h.transits")["label"] == "过境推迟"
