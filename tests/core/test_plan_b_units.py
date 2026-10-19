"""方案 B 的三个代码裁决工具，各自单独测：不经过 inspect / fork / sign，不用 Reasoner，直接喂图和对象。

1. branches.derive_branches —— 分支的独有部分、分叉点、kind、trunk、synthetic_evidence
2. validator.validate_plans —— 计划和图的对应关系
3. entrypoints.plan_affected —— 改假设后哪些计划失效（只看写范围）
另附 schema.parse_proposals（新旧提案文件的读取）。
"""
import pytest

from catalyst.branches import (
    ancestors, derive_branches, derive_views, divergence_nodes, hypothetical_inputs, own_node_ids,
)
from catalyst.entrypoints import plan_affected
from catalyst.fork import Scope, compute_write_scope
from catalyst.schema import Graph, ProposalDraft, Scenario, TradeProposal, parse_proposals
from catalyst.validator import validate_plans
from tests.core.test_plan_b import _cond, _edge, _node, _plan


def _graph(nodes, edges, conditions=()):
    return Graph.model_validate({"version": "u-v1", "op": {"kind": "inspect"}, "nodes": nodes, "edges": edges,
                                 "conditions": list(conditions)})


def _base_nodes(event_role="event"):
    return [_node("e", event_role, "起点"), _node("a", "assumption", "旁路假设"),
            _node("x", "intermediate", "分支 x", "supported"), _node("y", "intermediate", "分支 y"),
            _node("tx", "terminal", "结论 x", "supported", ["BZ"]), _node("ty", "terminal", "结论 y", instruments=["CL"])]


def _base_edges():
    return [_edge("e1", "e", "x", "r-1", "s"), _edge("e2", "x", "tx", "r-2", "s"),
            _edge("e3", "e", "y"), _edge("e4", "y", "ty"), _edge("e5", "a", "y")]


G = _graph(_base_nodes(), _base_edges(), [_cond("c.x", "x"), _cond("c.y", "y")])


def _kinds(g, **kw):
    return {b.terminal_id: b.kind for b in derive_branches(g, **kw)}


# ---- 1. derive_branches -------------------------------------------------------------

class TestDeriveBranches:
    def test_structure(self):
        bx, by = derive_branches(G)
        assert (bx.own_node_ids, bx.own_edge_ids) == (["x", "tx"], ["e1", "e2"])
        assert (by.own_node_ids, by.own_edge_ids) == (["a", "y", "ty"], ["e3", "e4", "e5"])
        assert bx.divergence_node_ids == by.divergence_node_ids == ["e"]
        assert ancestors(G, "ty") == {"e", "a", "y"} and own_node_ids(G, "tx") == {"x", "tx"}

    def test_divergence_requires_different_terminal_sets(self):
        # e 的两条出边汇聚到同一个 terminal：不是分叉点
        g = _graph([_node("e", "event", "e"), _node("p", "intermediate", "p"), _node("q", "intermediate", "q"),
                    _node("t", "terminal", "t", instruments=["BZ"])],
                   [_edge("1", "e", "p"), _edge("2", "e", "q"), _edge("3", "p", "t"), _edge("4", "q", "t")])
        assert divergence_nodes(g) == set()
        assert divergence_nodes(G) == {"e"}

    def test_kind_evidenced_and_model_only(self):
        assert _kinds(G) == {"tx": "evidenced", "ty": "model_only"}

    def test_hypothetical_from_shock_role_anywhere_upstream(self):
        assert _kinds(_graph(_base_nodes("shock"), _base_edges())) == {"tx": "hypothetical", "ty": "hypothetical"}

    def test_hypothetical_from_scenario_ops(self):
        def sc(*ops):
            return Scenario(version="u-v2", base_version="u-v1", assessment={}, ops=list(ops))
        changed = sc({"kind": "change_assumption", "target": "a"})
        assert _kinds(G, scenario=changed) == {"tx": "evidenced", "ty": "hypothetical"}
        on_terminal = sc({"kind": "change_assumption", "target": "tx"})
        assert _kinds(G, scenario=on_terminal)["tx"] == "hypothetical"  # terminal 本身也算
        shock = sc({"kind": "add_shock", "impacts": ["x"], "new_nodes": [_node("s", "intermediate", "冲击")]})
        g = _graph(_base_nodes() + [_node("s", "intermediate", "冲击")], _base_edges() + [_edge("es", "s", "x")])
        assert hypothetical_inputs(g, shock) == {"s"}  # 情景冲击新增的节点，role 不是 shock 也算
        assert _kinds(g, scenario=shock)["tx"] == "hypothetical"

    def test_contradicted_own_node_is_not_evidenced(self):
        nodes = _base_nodes()
        nodes[4]["evidence_status"] = "contradicted"
        assert _kinds(_graph(nodes, _base_edges()))["tx"] == "model_only"

    def test_edge_without_supports_evidence_is_not_evidenced(self):
        edges = _base_edges()
        edges[1]["evidence"][0]["stance"] = "neutral"  # 只有背景片段，不算支持
        assert _kinds(_graph(_base_nodes(), edges))["tx"] == "model_only"

    def test_synthetic_evidence_downgrades_and_flags(self):
        bx, by = derive_branches(G, synthetic_excerpt_ids={"r-2"})
        assert (bx.kind, bx.synthetic_evidence) == ("model_only", True)
        assert by.synthetic_evidence is False  # up 分支没引用合成片段
        hypo = derive_branches(_graph(_base_nodes("shock"), _base_edges()), synthetic_excerpt_ids={"r-1"})
        assert (hypo[0].kind, hypo[0].synthetic_evidence) == ("hypothetical", True)  # 标记与 kind 独立

    def test_no_own_edges_is_not_evidenced(self):
        b, = derive_branches(_graph([_node("t", "terminal", "孤立", instruments=["BZ"])], []))
        assert (b.own_edge_ids, b.kind) == ([], "model_only")

    def test_trunk(self):
        assert [b.trunk for b in derive_branches(G)] == ["evidenced", "evidenced"]  # 共用的只有起点，没有边
        g = _graph([_node("r", "event", "根")] + _base_nodes(), [_edge("e0", "r", "e")] + _base_edges())
        assert [b.trunk for b in derive_branches(g)] == ["model_only", "model_only"]
        g2 = _graph([_node("r", "event", "根")] + _base_nodes(), [_edge("e0", "r", "e", "r-0", "s")] + _base_edges())
        assert [b.trunk for b in derive_branches(g2)] == ["evidenced", "evidenced"]
        assert [b.trunk for b in derive_branches(g2, synthetic_excerpt_ids={"r-0"})] == ["model_only", "model_only"]

    def test_pure_and_ordered_by_graph(self):
        g = _graph(list(reversed(_base_nodes())), _base_edges())
        assert [b.terminal_id for b in derive_branches(g)] == ["ty", "tx"]
        assert derive_branches(G) == derive_branches(G.dump())  # dict 与对象同结果，不改输入


# ---- 2. validate_plans --------------------------------------------------------------

def _drafts(*plans):
    return [ProposalDraft.model_validate(p) for p in plans]


PX = _plan("tx", "BZ", "short", ["c.x"], ["c.y"])
PY = _plan("ty", "CL", "long", ["c.y"], ["c.x"])


class TestValidatePlans:
    def _refs(self, *plans, blocking=True):
        return {(i.ref, i.message.split("：")[0]) for i in validate_plans(G, _drafts(*plans)) if i.blocking == blocking}

    def test_exact_cover_passes(self):
        assert validate_plans(G, _drafts(PX, PY)) == []

    def test_missing_duplicate_and_unknown_terminal(self):
        assert any(r == "ty" for r, _ in self._refs(PX))
        assert any(r == "tx" and "has 2 plans" in m for r, m in self._refs(PX, PX, PY))
        assert any(r == "nope" and "is not in the graph" in m for r, m in self._refs(PX, PY, {**PY, "terminal_id": "nope"}))
        assert any(r == "x" and "is not a terminal" in m for r, m in self._refs(PX, PY, {**PY, "terminal_id": "x"}))

    def test_instrument_must_belong_to_its_terminal(self):
        assert any(r == "tx" and "CL" in m for r, m in self._refs({**PX, "direction": {**PX["direction"], "instrument": "CL"}}, PY))

    def test_references(self):
        bad = {**PX, "entry_condition_ids": ["c.nope"],
               "key_dependency": {"condition_id": "c.gone", "claim_id": "n.gone", "why": "w"}}
        refs = {r for r, _ in self._refs(bad, PY)}
        assert {"c.nope", "c.gone", "n.gone"} <= refs
        assert any(r == "tx" and "entry condition" in m for r, m in self._refs({**PX, "entry_condition_ids": []}, PY))

    def test_condition_off_branch_is_only_a_warning(self):
        off = {**PX, "entry_condition_ids": ["c.x", "c.y"]}
        issues = validate_plans(G, _drafts(off, PY))
        assert [(i.ref, i.blocking) for i in issues] == [("c.y", False)]
        # 离场条件挂在对手分支上（镜像）不提示：PX 的离场 c.y 不在 tx 上游，PY 的离场 c.x 不在 ty 上游
        assert validate_plans(G, _drafts(PX, PY)) == []

    def test_accepts_trade_proposals_too(self):
        tp = TradeProposal.model_validate({
            "terminal_id": "tx", "gate": "WAIT", "direction": PX["direction"], "entry_conditions": [], "exit_conditions": [],
            "exit_logic": "ANY", "user_judgment": {"original_statement": "o", "clarified_statement": "o"},
            "support_status": "unknown", "graph_version": "u-v1",
            "meta": {"proposal_version": "u-v1.tx", "prompt_version": "p5", "model": "m"}})
        assert any(i.ref == "tx" and "entry condition" in i.message for i in validate_plans(G, [tp]))


# ---- 3. plan_affected ---------------------------------------------------------------

def _tp(plan):
    conds = {c.id: c for c in G.conditions}
    return TradeProposal.model_validate({
        "terminal_id": plan["terminal_id"], "gate": "WAIT", "direction": plan["direction"],
        "entry_conditions": [conds[i].dump() for i in plan["entry_condition_ids"]],
        "exit_conditions": [conds[i].dump() for i in plan["exit_condition_ids"]], "exit_logic": "ANY",
        "key_dependency": plan["key_dependency"],
        "user_judgment": {"original_statement": "o", "clarified_statement": "o", "confirmed": True},
        "support_status": "unknown", "graph_version": "u-v1",
        "meta": {"proposal_version": f"u-v1.{plan['terminal_id']}", "prompt_version": "p5", "model": "m"}})


def _scope(target):
    return compute_write_scope(G, {"kind": "change_assumption", "target": target})


class TestPlanAffected:
    def test_rule1_terminal_in_scope(self):
        assert plan_affected(_tp(_plan("tx", "BZ", "short", ["c.y"], [])), _scope("tx"))

    def test_rule2_entry_or_exit_condition_in_scope(self):
        entry_only = _plan("ty", "CL", "long", ["c.x"], [])
        exit_only = _plan("ty", "CL", "long", ["c.y"], ["c.x"])
        assert plan_affected(_tp(entry_only), _scope("x"))  # ty 不在范围 {x, tx}
        assert plan_affected(_tp(exit_only), _scope("x"))

    @pytest.mark.parametrize("kd", [{"condition_id": "c.x", "claim_id": None, "why": "w"},
                                    {"condition_id": None, "claim_id": "x", "why": "w"}])
    def test_rule3_key_dependency_in_scope(self, kd):
        assert plan_affected(_tp(_plan("ty", "CL", "long", ["c.y"], [], kd)), _scope("x"))

    def test_untouched_plan_is_not_affected(self):
        assert not plan_affected(_tp(PY), _scope("tx"))  # PY 的离场 c.x 挂在 x 上，范围 {tx} 不含 x
        assert not plan_affected(_tp(_plan("ty", "CL", "long", ["c.y"], [])), _scope("x"))

    def test_uses_only_the_code_scope(self):
        """判定只看写范围，不看 assessment：哪怕模型把 y 标了 challenged，范围外就不算受影响。"""
        s = Scope(nodes=frozenset({"tx"}), edges=frozenset(), conditions=frozenset())
        assert not plan_affected(_tp(_plan("ty", "CL", "long", ["c.y"], [])), s)


# ---- parse_proposals ----------------------------------------------------------------

def test_parse_proposals_shapes():
    tp = _tp(PX)
    assert parse_proposals(None, G) == []
    assert parse_proposals([tp.dump()], G) == [tp]
    legacy = {k: v for k, v in tp.dump().items() if k not in ("terminal_id", "approval_reset", "rival_changed")}
    assert parse_proposals(legacy, G)[0].terminal_id == "tx"  # 按 BZ 找到唯一的 terminal


# ---- 1b. node_kinds / edge_kinds (derive_views) -----------------------------------------

class TestKindTables:
    def test_own_parts_take_their_branch_kind_and_edges_follow_targets(self):
        v = derive_views(G)
        assert v["node_kinds"] == {"e": "evidenced", "a": "model_only", "x": "evidenced", "y": "model_only",
                                   "tx": "evidenced", "ty": "model_only"}
        assert v["edge_kinds"] == {"e1": "evidenced", "e2": "evidenced", "e3": "model_only", "e4": "model_only",
                                   "e5": "model_only"}

    def test_hypothetical_inputs_and_hypothetical_branches(self):
        v = derive_views(_graph(_base_nodes("shock"), _base_edges()))
        assert set(v["node_kinds"].values()) == {"hypothetical"}  # the shock itself + every own part downstream
        changed = Scenario(version="u-v2", base_version="u-v1", assessment={},
                           ops=[{"kind": "change_assumption", "target": "a"}])
        v = derive_views(G, changed)
        assert v["node_kinds"]["a"] == "hypothetical" and v["node_kinds"]["x"] == "evidenced"
        assert v["edge_kinds"]["e5"] == "hypothetical"  # target y is in the hypothetical branch

    def test_shared_node_takes_the_weakest_trunk(self):
        # r feeds t1/t2 through m (one supported and one model_only in-edge on m), and feeds t3 directly.
        # t3's trunk is just {r} with no edges -> evidenced; t1/t2's trunk {r, q, m} -> model_only.
        g = _graph([_node("r", "event", "r"), _node("q", "assumption", "q"), _node("m", "intermediate", "m"),
                    _node("t1", "terminal", "t1", instruments=["A"]), _node("t2", "terminal", "t2", instruments=["B"]),
                    _node("t3", "terminal", "t3", instruments=["C"])],
                   [_edge("rm", "r", "m", "r-1", "s"), _edge("qm", "q", "m"), _edge("m1", "m", "t1"),
                    _edge("m2", "m", "t2"), _edge("r3", "r", "t3")])
        v = derive_views(g)
        assert [b.trunk for b in v["branches"]] == ["model_only", "model_only", "evidenced"]
        assert v["node_kinds"]["r"] == "model_only"  # weakest of model_only, model_only, evidenced
        assert v["edge_kinds"]["rm"] == v["node_kinds"]["m"] == "model_only"

    def test_derive_branches_is_the_same_derivation(self):
        assert derive_branches(G) == derive_views(G)["branches"]


# ---- 4. one reading of the user's words per version (validate_plans) ---------------------

def test_plans_must_share_original_and_clarified_statement():
    other = {**PY, "user_judgment": {**PY["user_judgment"], "clarified_statement": "something else"}}
    issues = [i for i in validate_plans(G, _drafts(PX, other)) if i.ref == "proposals"]
    assert len(issues) == 1 and issues[0].blocking and "clarified_statement" in issues[0].message
    other = {**PY, "user_judgment": {**PY["user_judgment"], "original_statement": "different words"}}
    assert any("original_statement" in i.message for i in validate_plans(G, _drafts(PX, other)))
