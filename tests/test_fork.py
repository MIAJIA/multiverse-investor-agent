"""E3 Non-interference（依赖核心）。设计规则见 docs/eval/test-plan.md A3。

哈希由测试自己算（tests/_graph.py），不信任核心自报。
"""
import copy

import pytest

pytest.importorskip("catalyst", reason="核心包 catalyst 尚未落地")

from eval.loader import load_fixture  # noqa: E402
from tests import _adapter  # noqa: E402
from tests._graph import by_id, element_hashes  # noqa: E402

BASE = load_fixture("c1_graph_v1.json")
FORKS = {
    "change_assumption": load_fixture("c3_change_assumption.json"),
    "add_shock": load_fixture("c3_add_shock.json"),
}
OUT_OF_SCOPE = [
    (kind, p) for kind, fx in FORKS.items() for p in fx["patches_out_of_scope"]
]


def _assert_out_of_scope_unchanged(base: dict, new: dict, scope: dict):
    before, after = element_hashes(base), element_hashes(new)
    for kind in ("nodes", "edges", "conditions"):
        for elem_id, h in before[kind].items():
            if elem_id in scope[kind]:
                continue
            assert after[kind].get(elem_id) == h, f"范围外的 {kind[:-1]} {elem_id} 被修改或删除"


@pytest.mark.parametrize("kind", FORKS)
def test_write_scope_matches_golden(kind):
    fx = FORKS[kind]
    nodes, edges, _ = _adapter.compute_write_scope(BASE, fx["op"])
    assert nodes == set(fx["expected_scope"]["nodes"])
    assert edges == set(fx["expected_scope"]["edges"])


@pytest.mark.parametrize("kind", FORKS)
def test_in_scope_patch_keeps_everything_else(kind):
    fx = FORKS[kind]
    base = copy.deepcopy(BASE)
    _, _, raw_scope = _adapter.compute_write_scope(base, fx["op"])
    new = _adapter.apply_patch(base, fx["patch_in_scope"], raw_scope)

    _assert_out_of_scope_unchanged(BASE, new, fx["expected_scope"])
    # 基线版本仍在：输入没有被原地修改；新图是新版本
    assert base == BASE, "apply_patch 原地修改了基线图"
    assert new["version"] != BASE["version"]
    assert new["parent_version"] == BASE["version"]
    # AddShock 只新增经 Stage 1 识别的节点与边
    added_edges = set(by_id(new["edges"])) - set(by_id(BASE["edges"]))
    added_nodes = set(by_id(new["nodes"])) - set(by_id(BASE["nodes"]))
    assert added_edges == {e["id"] for e in fx["op"].get("new_edges", [])}
    assert added_nodes == {n["id"] for n in fx["op"].get("new_nodes", [])}


@pytest.mark.parametrize("kind,case", OUT_OF_SCOPE, ids=[f"{k}:{p['name']}" for k, p in OUT_OF_SCOPE])
def test_out_of_scope_patch_rejected(kind, case):
    fx = FORKS[kind]
    base = copy.deepcopy(BASE)
    _, _, raw_scope = _adapter.compute_write_scope(base, fx["op"])
    with pytest.raises(_adapter.scope_violation()):
        _adapter.apply_patch(base, case["patch"], raw_scope)
    assert base == BASE, f"越界补丁被拒后基线图仍被改动（{case['why']}）"


@pytest.mark.parametrize("kind", FORKS)
def test_diff_stays_inside_scope(kind):
    fx = FORKS[kind]
    _, _, raw_scope = _adapter.compute_write_scope(BASE, fx["op"])
    new = _adapter.apply_patch(copy.deepcopy(BASE), fx["patch_in_scope"], raw_scope)
    d = _adapter.diff(BASE, new)
    scope = fx["expected_scope"]
    assert d["nodes_changed"] | d["nodes_added"] | d["nodes_removed"] <= set(scope["nodes"])
    assert d["edges_changed"] | d["edges_added"] | d["edges_removed"] <= set(scope["edges"])
    assert d["conditions_changed"] <= set(scope["conditions"])
