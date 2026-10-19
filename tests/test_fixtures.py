"""golden fixture 自洽（不依赖核心）。见 docs/eval/test-plan.md B1。"""
import datetime as dt

import pytest

from eval.loader import load_fixture
from tests._graph import apply_mutation, by_id, descendants, is_acyclic, reference_write_scope

GRAPH = load_fixture("c1_graph_v1.json")
PACK = load_fixture("c1_evidence_pack.json")
FORKS = [load_fixture("c3_change_assumption.json"), load_fixture("c3_add_shock.json")]
D1 = load_fixture("d1_hormuz.json")
KINDS = {"numeric", "document", "event"}
PREDICATES = {"observed_by", "not_observed_by", "at_deadline"}


def test_graph_acyclic_and_every_node_reaches_a_terminal():
    assert is_acyclic(GRAPH)
    terminals = {n["id"] for n in GRAPH["nodes"] if n["role"] == "terminal"}
    for n in GRAPH["nodes"]:
        if n["id"] in terminals:
            assert n["instruments"], f"终点 {n['id']} 没有标的"
            continue
        assert descendants(GRAPH, {n["id"]}) & terminals, f"{n['id']} 不在通往任何终点的路径上"


def test_edges_have_evidence_or_explicit_model_only():
    for e in GRAPH["edges"]:
        assert bool(e.get("evidence")) != bool(e.get("model_only")), e["id"]
    assert any(e.get("model_only") for e in GRAPH["edges"]), "至少一条 model_only 边"


def test_every_reference_exists_and_pack_has_counter_evidence():
    excerpt_ids = {x["excerpt_id"] for x in PACK["excerpts"]}
    for e in GRAPH["edges"]:
        for ev in e.get("evidence", []):
            assert ev["excerpt_id"] in excerpt_ids, (e["id"], ev["excerpt_id"])
            assert ev["stance"] in {"supports", "contradicts"}
    assert any(x["stance"] == "contradicts" for x in PACK["excerpts"])
    assert any(x["stance"] == "contradicts" for x in D1["evidence_pack"]["excerpts"])


@pytest.mark.parametrize("fx", FORKS, ids=lambda f: f["op"]["kind"])
def test_expected_scope_matches_reference(fx):
    ref = reference_write_scope(GRAPH, fx["op"])
    for kind in ("nodes", "edges", "conditions"):
        assert set(fx["expected_scope"][kind]) == ref[kind], kind


@pytest.mark.parametrize("fx", FORKS, ids=lambda f: f["op"]["kind"])
def test_golden_challenged_sets(fx):
    scope = set(fx["expected_scope"]["nodes"])
    challenged, unaffected = set(fx["expected_challenged"]), set(fx["expected_unaffected"])
    assert challenged <= scope
    assert not (unaffected & scope)
    target = {fx["op"]["target"]}
    all_claims = {n["id"] for n in GRAPH["nodes"]}
    assert challenged | unaffected == all_claims - target
    assert challenged, "golden 不能是空集，否则什么都不改的系统也能过 E3"
    assert unaffected, "必须有不受影响的路径，检验「一条路径受挑战不等于论点失效」"


@pytest.mark.parametrize("fx", FORKS, ids=lambda f: f["op"]["kind"])
def test_patches_touch_what_they_claim(fx):
    scope = {k: set(v) for k, v in fx["expected_scope"].items()}
    p = fx["patch_in_scope"]
    assert {u["id"] for u in p["node_updates"]} | {n["id"] for n in p["node_adds"]} <= scope["nodes"]
    assert {u["id"] for u in p["edge_updates"]} | {e["id"] for e in p["edge_adds"]} <= scope["edges"]
    assert {u["id"] for u in p["condition_updates"]} <= scope["conditions"]
    assert set(p["assessment"]) <= scope["nodes"]
    for case in fx["patches_out_of_scope"]:
        for kind, ids in case["touches"].items():
            assert not (set(ids) & scope[kind]), case["name"]


def _date(s):
    try:
        return dt.date.fromisoformat(s)
    except (TypeError, ValueError):
        return None


@pytest.mark.parametrize("cond", GRAPH["conditions"] + D1["entry_conditions"], ids=lambda c: c["id"])
def test_condition_shape(cond):
    assert cond["kind"] in KINDS and cond["predicate"] in PREDICATES
    assert cond["anchor"] and cond["deadline"]
    a, d = _date(cond["anchor"]), _date(cond["deadline"])
    if a and d:
        assert d >= a, "deadline 不早于 anchor"
    if cond["kind"] == "numeric" and cond["threshold"] is None:
        assert cond["threshold_note"], "null 阈值必须带说明"
    assert cond["evaluation_status"] in {"met", "not_met", "unknown"}
    assert cond["verification_status"] in {"verifiable", "unverified"}


def test_d1_null_threshold_and_wait():
    conds = by_id(D1["entry_conditions"])
    for cid in D1["expected"]["null_threshold_condition_ids"]:
        assert conds[cid]["threshold"] is None and conds[cid]["threshold_note"]
    for c in D1["entry_conditions"]:
        if c["series"] in D1["expected"]["must_not_contain_numeric_threshold_for"]:
            assert c["threshold"] is None
    assert D1["expected"]["gate"] == "WAIT"
    assert D1["user_judgment"]["requires_user_confirmation"] is True


def test_reference_cases_mutate_known_ids():
    for case in load_fixture("reference_cases.json")["cases"]:
        apply_mutation(GRAPH, case["node_updates"], case["edge_updates"])  # KeyError 即 fixture 写错 id
