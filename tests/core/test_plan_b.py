"""方案 B（docs/changes/2026-10-18-branches-and-plans.md）后端的回归测试：每条决定至少一个。脚本化 Reasoner，不调模型。

图（两条竞争分支，共用起点事件）：

    e.ann ─e1→ b.recover ─e2→ t.down [BZ]        进场 cond.recover
       └──e3→ b.stall ──e4→ t.up [CL]            进场 cond.stall
    a.hedge ─e5→ b.stall                          旁路的根节点，只属于 up 分支

down 分支的边带真实（非合成）资料包的 supports 证据；up 分支全是 model_only。
"""
import copy
import json

import pytest

from catalyst import api, entrypoints as ep
from catalyst.__main__ import main as cli
from catalyst.branches import derive_branches, divergence_nodes, own_node_ids
from catalyst.evidence import EvidenceProvider
from catalyst.schema import Graph, LegacyProposalError, VersionBundle, parse_proposals
from catalyst.store import RunStore
from catalyst.validator import validate_plans
from tests.core.test_harness import Scripted

REAL = {"pack_id": "rp", "synthetic": False, "excerpts": [
    {"source_id": "s-1", "excerpt_id": "rp-1", "source": "portwatch", "date": "2026-10-16", "stance": "supports",
     "text": "宣布开放后第一周日过境量回升到 18 艘。"},
    {"source_id": "s-2", "excerpt_id": "rp-2", "source": "eia", "date": "2026-10-17", "stance": "supports",
     "text": "过境恢复时近月 Brent 通常走弱。"},
]}
CFG = ep.Config(packs=["rp"], today="2026-10-18", run_prefix="b")


def _node(id_, role, label, status="unknown", instruments=()):
    return {"id": id_, "role": role, "statement": label, "label": label, "original_statement": label,
            "evidence_status": status, "time_bucket": None, "instruments": list(instruments)}


def _edge(id_, frm, to, excerpt=None, source=None):
    ev = [{"tier": "T1", "source_id": source, "excerpt_id": excerpt, "stance": "supports", "supports": "全部",
           "rebuttal": None}] if excerpt else []
    return {"id": id_, "from": frm, "to": to, "channel": "supply", "sign": "+", "lag_days": None,
            "mechanism": f"{frm}→{to}", "model_only": not excerpt, "evidence": ev}


def _cond(id_, claim):
    return {"id": id_, "claim_id": claim, "kind": "document", "predicate": "observed_by", "series": None,
            "source": "官方公告", "comparator": None, "threshold": None, "threshold_note": None,
            "anchor": "2026-10-18", "deadline": "2026-11-30",
            "observation_window": {"start": "2026-10-18", "end": "2026-11-30"},
            "rule": "窗口内看到即 met", "verification_status": "verifiable"}


def _plan(t, inst, side, entry, exit_, kd=None, statement="判断"):
    return {"terminal_id": t, "direction": {"instrument": inst, "side": side, "horizon_days": 30, "note": None},
            "entry_condition_ids": entry, "exit_condition_ids": exit_, "exit_logic": "ANY",
            "key_dependency": kd or {"condition_id": None, "claim_id": None, "why": "依据不足"},
            "user_judgment": {"original_statement": "海峡下周重开", "clarified_statement": statement,
                              "criteria": None, "deadline": "2026-11-30", "requires_user_confirmation": False}}


def _out(event_role="event", plans=None):
    """完整的 InspectOutput（Scripted 会拆成图和计划两步）。默认的计划草稿故意按 up、down 的顺序给。"""
    return {
        "no_chain": False, "no_chain_reason": None,
        "nodes": [_node("e.ann", event_role, "宣布重开"), _node("a.hedge", "assumption", "船东观望"),
                  _node("b.recover", "intermediate", "过境恢复", "supported"),
                  _node("b.stall", "intermediate", "过境停滞"),
                  _node("t.down", "terminal", "Brent 走弱", "supported", ["BZ"]),
                  _node("t.up", "terminal", "原油走强", instruments=["CL"])],
        "edges": [_edge("e1", "e.ann", "b.recover", "rp-1", "s-1"), _edge("e2", "b.recover", "t.down", "rp-2", "s-2"),
                  _edge("e3", "e.ann", "b.stall"), _edge("e4", "b.stall", "t.up"), _edge("e5", "a.hedge", "b.stall")],
        "conditions": [_cond("cond.recover", "b.recover"), _cond("cond.stall", "b.stall")],
        "proposals": plans if plans is not None else [
            _plan("t.up", "CL", "long", ["cond.stall"], ["cond.recover"],  # 镜像：对手分支的进场条件是这里的离场条件
                  {"condition_id": "cond.stall", "claim_id": None, "why": "停滞是否持续"}),
            _plan("t.down", "BZ", "short", ["cond.recover"], [],
                  {"condition_id": None, "claim_id": "a.hedge", "why": "船东是否观望"}, statement="11 月底前过境恢复")],
    }


def _ev(synthetic=False):
    e = EvidenceProvider("/nonexistent")
    e.register({**REAL, "synthetic": synthetic})
    return e


def _inspect(out=None, store=None, synthetic=False):
    res = ep.inspect("海峡下周重开", reasoner=Scripted([out or _out()]), evidence=_ev(synthetic), config=CFG, store=store)
    assert res["ok"], res["errors"]
    return res


def _fork_out(scope_nodes, status="challenged"):
    return {"node_updates": [], "edge_updates": [], "condition_updates": [], "next_checks": ["查证"],
            "assessment": [{"claim_id": c, "status": status, "reason": "r"} for c in scope_nodes]}


def _fork(res, target, scope_nodes, proposals=None):
    op = {"kind": "change_assumption", "target": target, "value": "改了"}
    out = ep.fork(res["graph"], op, reasoner=Scripted([_fork_out(scope_nodes)]), evidence=_ev(), config=CFG,
                  proposals=proposals if proposals is not None else res["proposals"])
    assert out["ok"], out["errors"]
    assert sorted(out["scope"]["nodes"]) == sorted(scope_nodes)
    return out


def _by_t(res):
    return {p["terminal_id"]: p for p in res["proposals"]}


def _approve(res, terminal, claims=()):
    s = ep.sign(res["graph"], res["proposals"], terminal_id=terminal, confirmed_claim_ids=list(claims), config=CFG)
    assert s["ok"], s["errors"]
    return s


# ---- D-B1 / D-B2：一张图多条分支，每个 terminal 恰好一份计划 ----------------------

def test_one_plan_per_terminal_ordered_by_graph_not_model():
    res = _inspect()
    assert [p["terminal_id"] for p in res["proposals"]] == ["t.down", "t.up"]  # 模型给的是 up、down
    assert [p["meta"]["proposal_version"] for p in res["proposals"]] == ["b-v1.t.down", "b-v1.t.up"]
    assert all(p["user_judgment"]["confirmed"] is False for p in res["proposals"])
    assert [b["terminal_id"] for b in res["branches"]] == ["t.down", "t.up"]


def test_missing_plan_for_a_terminal_is_fed_back_and_rewritten():
    one = _out(plans=[_plan("t.down", "BZ", "short", ["cond.recover"], [])])
    r = Scripted([one, {k: _out()[k] for k in ("conditions", "proposals")}])
    res = ep.inspect("海峡下周重开", reasoner=r, evidence=_ev(), config=CFG)
    assert res["ok"] and r.stages == ["inspect", "inspect.plan", "inspect.plan"]
    assert "[t.up]" in r.prompts[2] and "没有计划" in r.prompts[2]


def test_validate_plans_rules():
    g = _inspect()["graph"]
    good = [ep.ProposalDraft.model_validate(p) for p in _out()["proposals"]]
    assert not [i for i in validate_plans(g, good) if i.blocking]
    dup = good + [good[0]]
    assert any(i.ref == "t.up" and "2 份计划" in i.message for i in validate_plans(g, dup))
    stray = [*good, ep.ProposalDraft.model_validate(_plan("b.stall", "CL", "long", ["cond.stall"], []))]
    assert any(i.ref == "b.stall" and i.blocking and "不是 terminal" in i.message for i in validate_plans(g, stray))
    wrong_inst = [good[0], ep.ProposalDraft.model_validate(_plan("t.down", "CL", "short", ["cond.recover"], []))]
    assert any(i.ref == "t.down" and i.blocking and "CL" in i.message for i in validate_plans(g, wrong_inst))
    # 条件挂在别的分支上：非阻断提示（cond.stall 不在 t.down 上游）
    off = [good[0], ep.ProposalDraft.model_validate(_plan("t.down", "BZ", "short", ["cond.recover", "cond.stall"], []))]
    warn = [i for i in validate_plans(g, off) if i.ref == "cond.stall"]
    assert warn and not warn[0].blocking


def test_instrument_of_other_terminal_is_rejected_in_inspect():
    bad = _out(plans=[_plan("t.down", "CL", "short", ["cond.recover"], []),
                      _plan("t.up", "BZ", "long", ["cond.stall"], [])])
    res = ep.inspect("x", reasoner=Scripted([bad, bad, bad]), evidence=_ev(), config=CFG)
    assert not res["ok"] and any("[t.down]" in e and "CL" in e for e in res["errors"])


# ---- 4.4：support_status 纳入分支独有的 claim -----------------------------------

def test_support_status_includes_branch_own_claims():
    plans = [_plan("t.down", "BZ", "short", ["cond.recover"], []), _plan("t.up", "CL", "long", ["cond.stall"], [])]
    res = _inspect(_out(plans=plans))
    g = Graph.model_validate(res["graph"])
    down = ep._draft_of(ep.TradeProposal.model_validate(_by_t(res)["t.down"]))
    assert ep.derive_proposal(down, g, model="m").support_status == "supported"  # b.recover、t.down 都 supported
    g2 = g.model_copy(update={"nodes": [n.model_copy(update={"evidence_status": "contradicted"}) if n.id == "t.down"
                                        else n for n in g.nodes]})
    # 进场条件和 key_dependency 都不在 t.down 上，只有分支独有的 terminal 被反驳
    assert ep.derive_proposal(down, g2, model="m").support_status == "challenged"


# ---- D-B9 / 4.2：分支类别由代码推导 --------------------------------------------

def test_branch_parts_and_kinds():
    res = _inspect()
    down, up = res["branches"]
    assert down["own_node_ids"] == ["b.recover", "t.down"] and down["own_edge_ids"] == ["e1", "e2"]
    assert up["own_node_ids"] == ["a.hedge", "b.stall", "t.up"]  # 旁路根节点 a.hedge 没有漏
    assert up["own_edge_ids"] == ["e3", "e4", "e5"]
    assert down["divergence_node_ids"] == ["e.ann"] == up["divergence_node_ids"]
    assert (down["kind"], up["kind"]) == ("evidenced", "model_only")
    assert down["trunk"] == "evidenced"  # 共用的只有起点事件，没有边
    assert not down["synthetic_evidence"] and not up["synthetic_evidence"]


def test_not_yet_happened_event_makes_every_branch_hypothetical():
    res = _inspect(_out(event_role="shock"))
    assert [b["kind"] for b in res["branches"]] == ["hypothetical", "hypothetical"]


def test_synthetic_pack_cannot_be_evidenced():
    res = _inspect(synthetic=True)
    down = res["branches"][0]
    assert down["kind"] == "model_only" and down["synthetic_evidence"] is True


def test_branch_without_own_edges_is_not_evidenced():
    """独有部分一条边都没有（terminal 自己就是根）：没有资料可言，不能因为「每条边都合格」空真成立就算 evidenced。"""
    g = Graph.model_validate({"version": "x-v1", "op": {"kind": "inspect"}, "edges": [], "conditions": [],
                              "nodes": [_node("t.solo", "terminal", "孤立结论", instruments=["BZ"])]})
    b, = derive_branches(g)
    assert b.own_node_ids == ["t.solo"] and b.own_edge_ids == [] and b.kind == "model_only"


def test_trunk_strength_follows_shared_edges():
    out = _out()
    out["nodes"].insert(0, _node("e.root", "event", "封锁"))
    out["edges"].append(_edge("e0", "e.root", "e.ann"))  # 共用上游里一条 model_only 边
    res = _inspect(out)
    assert [b["trunk"] for b in res["branches"]] == ["model_only", "model_only"]
    assert res["branches"][0]["kind"] == "evidenced"  # 主干是推断，不影响独有部分本身的类别


def test_changed_assumption_and_added_shock_make_dependants_hypothetical():
    res = _inspect()
    forked = _fork(res, "b.recover", ["b.recover", "t.down"])
    assert [b["kind"] for b in forked["branches"]] == ["hypothetical", "model_only"]
    # 改共用上游：所有依赖它的分支都变成 hypothetical
    forked = _fork(res, "e.ann", ["e.ann", "b.recover", "b.stall", "t.down", "t.up"])
    assert [b["kind"] for b in forked["branches"]] == ["hypothetical", "hypothetical"]
    shock = {"kind": "add_shock", "impacts": ["b.stall"],
             "new_nodes": [_node("s.mine", "shock", "水雷")], "new_edges": [_edge("es", "s.mine", "b.stall")]}
    out = ep.fork(res["graph"], shock, reasoner=Scripted([_fork_out(["s.mine", "b.stall", "t.up"])]),
                  evidence=_ev(), config=CFG, proposals=res["proposals"])
    assert out["ok"], out["errors"]
    assert [b["kind"] for b in out["branches"]] == ["evidenced", "hypothetical"]


def test_divergence_nodes_need_different_terminal_sets():
    g = Graph.model_validate({**_inspect()["graph"]})
    assert divergence_nodes(g) == {"e.ann"}  # a.hedge 只有一条出边，b.* 只通向一个 terminal
    assert own_node_ids(g, "t.up") == {"a.hedge", "b.stall", "t.up"}


# ---- D-B5 / 4.3：改假设只让受影响的计划失效 -------------------------------------

def test_fork_resets_only_plans_hit_by_write_scope():
    res = _approve(_inspect(), "t.down", ["e.ann", "a.hedge"])  # down 已批准
    forked = _fork(res, "t.up", ["t.up"])  # 只碰 up 的 terminal
    p = _by_t(forked)
    assert p["t.down"]["user_judgment"]["confirmed"] is True  # 批准原样保留
    assert p["t.down"]["user_judgment"]["confirmed_claim_ids"] == ["e.ann", "a.hedge"]
    assert p["t.down"]["approval_reset"] is False and p["t.down"]["rival_changed"] is True
    assert p["t.up"]["approval_reset"] is False  # 受影响，但它本来就没被批准
    assert p["t.up"]["rival_changed"] is False


def test_rule2_mirror_exit_condition_in_scope():
    res = _approve(_inspect(), "t.up", ["e.ann", "b.recover"])
    forked = _fork(res, "b.recover", ["b.recover", "t.down"])  # t.up 不在范围，但它的离场条件挂在 b.recover 上
    up = _by_t(forked)["t.up"]
    assert up["user_judgment"]["confirmed"] is False and up["approval_reset"] is True
    assert up["user_judgment"]["confirmed_claim_ids"] == ["e.ann"]  # 剔除写范围内的 claim


@pytest.mark.parametrize("kd", [{"condition_id": None, "claim_id": "a.hedge", "why": "w"},
                                {"condition_id": "cond.stall", "claim_id": None, "why": "w"}])
def test_rule3_key_dependency_in_scope(kd):
    plans = [_plan("t.down", "BZ", "short", ["cond.recover"], [], kd),
             _plan("t.up", "CL", "long", ["cond.stall"], [])]
    res = _approve(_inspect(_out(plans=plans)), "t.down")
    forked = _fork(res, "a.hedge", ["a.hedge", "b.stall", "t.up"])  # down 只经 key_dependency 受影响
    down = _by_t(forked)["t.down"]
    assert down["user_judgment"]["confirmed"] is False and down["approval_reset"] is True


def test_reset_flags_are_recomputed_not_inherited():
    res = _approve(_inspect(), "t.down")
    v2 = _fork(res, "t.up", ["t.up"])
    assert _by_t(v2)["t.down"]["rival_changed"] is True
    v3 = _approve(v2, "t.down")  # 批准产出新版本：两个标记一律 false
    assert not any(p["approval_reset"] or p["rival_changed"] for p in v3["proposals"])
    v4 = _fork(v2, "b.recover", ["b.recover", "t.down"])  # 在 v2 上再分叉：按这一层重新算
    p = _by_t(v4)
    assert p["t.down"]["approval_reset"] is True and p["t.down"]["rival_changed"] is False
    assert p["t.up"]["rival_changed"] is False  # up 的离场条件在范围里，它自己也受影响


# ---- D-B3 / D-B4 / 4.5：批准 -----------------------------------------------------

def test_approve_one_plan_revokes_the_others_in_the_version():
    v1 = _inspect()
    v2 = _approve(v1, "t.down", ["e.ann"])
    v3 = _approve(v2, "t.up", ["b.stall"])
    p = _by_t(v3)
    assert p["t.up"]["user_judgment"]["confirmed"] is True
    assert p["t.down"]["user_judgment"]["confirmed"] is False
    assert p["t.down"]["user_judgment"]["confirmed_claim_ids"] == ["e.ann"]  # 用户勾过的前提保留
    assert sum(q["user_judgment"]["confirmed"] for q in v3["proposals"]) == 1
    assert v3["graph"]["op"]["value"]["terminal_id"] == "t.up"


def test_approve_without_statement_fields_keeps_plan_values():
    v1 = _inspect()
    v2 = _approve(v1, "t.down")
    uj = _by_t(v2)["t.down"]["user_judgment"]
    assert (uj["clarified_statement"], uj["deadline"], uj["confirmed"]) == ("11 月底前过境恢复", "2026-11-30", True)
    v3 = ep.sign(v1["graph"], v1["proposals"], terminal_id="t.down", criteria="PortWatch", config=CFG)
    assert _by_t(v3)["t.down"]["user_judgment"]["criteria"] == "PortWatch"


def test_approve_unknown_terminal_is_rejected():
    v1 = _inspect()
    res = ep.sign(v1["graph"], v1["proposals"], terminal_id="b.stall", config=CFG)
    assert not res["ok"] and "[b.stall]" in res["errors"][0] and res["graph"] is None


def test_rewritten_statement_requires_confirmation_per_plan():
    """D-B7：模型改写过原话，这份计划就一定要用户确认，即使模型写了 false。"""
    p = _by_t(_inspect())
    assert p["t.down"]["user_judgment"]["requires_user_confirmation"] is True  # 「海峡下周重开」→「11 月底前过境恢复」
    assert p["t.up"]["user_judgment"]["requires_user_confirmation"] is True  # 「判断」也是改写


# ---- API：sign 的请求体、版本包形状 ----------------------------------------------

@pytest.fixture
def api_run(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "RUNS", tmp_path / "api")
    r = Scripted([_out(), _fork_out(["t.up"])])
    monkeypatch.setattr(api, "_reasoner", lambda store: r)
    monkeypatch.setattr(api, "_provider", lambda packs: (_ev(), ["rp"], []))
    created = api.create_run({"event": "海峡下周重开", "target": "BZ", "today": "2026-10-18"})
    assert created["ok"], created["errors"]
    return created["run_id"]


def test_api_sign_requires_terminal_id_without_key_error(api_run):
    res = api.sign_run(api_run, {"version": "r-v1"})
    assert res == {"ok": False, "errors": ["[terminal_id] 必填"], "version": None}
    ok = api.sign_run(api_run, {"version": "r-v1", "terminal_id": "t.up"})  # 没有 clarified_statement 也不报 KeyError
    assert ok["ok"], ok["errors"]
    b = api._store(api_run).bundle(ok["version"])
    assert [p["user_judgment"]["confirmed"] for p in b["proposals"]] == [False, True]


def test_bundle_is_a_version_bundle_and_fork_keeps_unaffected_approval(api_run):
    signed = api.sign_run(api_run, {"version": "r-v1", "terminal_id": "t.down"})
    forked = api.fork_run(api_run, {"base_version": signed["version"],
                                    "op": {"kind": "change_assumption", "target": "t.up", "value": "x"}})
    assert forked["ok"], forked["errors"]
    b = api._store(api_run).bundle(forked["version"])
    VersionBundle.model_validate(b)
    assert "proposal" not in b
    p = {q["terminal_id"]: q for q in b["proposals"]}
    assert p["t.down"]["user_judgment"]["confirmed"] is True and p["t.down"]["rival_changed"] is True
    assert [x["kind"] for x in b["branches"]] == ["evidenced", "hypothetical"]


def test_api_fork_carries_synthetic_flag(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "RUNS", tmp_path / "api")
    monkeypatch.setattr(api, "_reasoner", lambda store: Scripted([_out(), _fork_out(["t.up"])]))
    monkeypatch.setattr(api, "_provider", lambda packs: (_ev(synthetic=True), ["rp"], []))
    run = api.create_run({"event": "x", "target": "BZ", "today": "2026-10-18"})["run_id"]
    forked = api.fork_run(run, {"base_version": "r-v1", "op": {"kind": "change_assumption", "target": "t.up"}})
    b = api._store(run).bundle(forked["version"])
    assert b["branches"][0]["synthetic_evidence"] is True and b["branches"][0]["kind"] == "model_only"


# ---- store：旧文件 ----------------------------------------------------------------

def test_legacy_single_proposal_file_reads_as_one_item_list(tmp_path):
    store = RunStore(tmp_path)
    res = _inspect(store=store)
    legacy = copy.deepcopy(_by_t(res)["t.up"])
    del legacy["terminal_id"], legacy["approval_reset"], legacy["rival_changed"]
    (tmp_path / "proposals" / "b-v1.json").write_text(json.dumps(legacy, ensure_ascii=False))
    obs = tmp_path / "observations" / "b-v1.json"
    obs.write_text(json.dumps({k: v for k, v in json.loads(obs.read_text()).items() if k != "synthetic"}))
    b = store.bundle("b-v1")
    assert [p["terminal_id"] for p in b["proposals"]] == ["t.up"]  # 按 CL 找到唯一的 terminal
    assert b["branches"][0]["kind"] == "evidenced"  # 旧 observations 没有 synthetic，按 false 读
    VersionBundle.model_validate(b)


def test_legacy_proposal_with_ambiguous_instrument_is_an_error():
    g = _inspect()["graph"]
    for n in g["nodes"]:
        if n["id"] == "t.up":
            n["instruments"] = ["CL", "BZ"]
    legacy = {k: v for k, v in _by_t(_inspect())["t.down"].items() if k != "terminal_id"}
    with pytest.raises(LegacyProposalError, match="2 个 terminal"):
        parse_proposals(legacy, g)


def test_promote_writes_proposals_and_branches(tmp_path):
    run = tmp_path / "run"
    store = RunStore(run)
    _inspect(store=store)
    (run / "case.json").write_text(json.dumps({"case": {"id": "B"}, "packs": ["rp"], "notes": []}))
    cli(["promote", str(run), "b", "--fixtures-dir", str(tmp_path / "fx")])
    fx = json.loads((tmp_path / "fx" / "b.json").read_text())
    v = fx["versions"]["b-v1"]
    VersionBundle.model_validate(v)
    assert [b["kind"] for b in v["branches"]] == ["evidenced", "model_only"] and len(v["proposals"]) == 2
