"""B 层检查与 P 层探针（不依赖核心，用 fake 跑通）。"""
import copy

from eval import report
from eval.fakes import FakeEntrypoints, FakeEvidence, FakeReasoner, RealPackEvidence
from eval.loader import load_case, load_fixture
from eval.probes import load_probes, run_probes, variant
from eval.runner import run_case


def _run(case_id, ep, evidence=None):
    return run_case(load_case(case_id), "pipeline", reasoner=FakeReasoner(), evidence=evidence or FakeEvidence(),
                    entrypoints=ep)


def _check(r, name):
    return next(c for c in r["checks"] if c["name"] == name)


def _plan(tid="t1", instrument="LITE", entry=(), exit_=(), exit_logic="ANY"):
    return {"terminal_id": tid, "gate": "WAIT", "direction": {"instrument": instrument, "side": "long"},
            "entry_conditions": list(entry), "exit_conditions": list(exit_), "exit_logic": exit_logic,
            "user_judgment": {"requires_user_confirmation": True}, "status": "draft", "support_status": "unknown"}


COND = load_fixture("c1_graph_v1.json")["conditions"]


# ---- B 层 -----------------------------------------------------------------------

def test_b1_no_chain_or_unevidenced_and_citation_laundering():
    assert _check(_run("B1", FakeEntrypoints()), "no_chain_or_unevidenced_branches")["passed"]
    assert _check(_run("B1", FakeEntrypoints(no_chain=True)), "no_chain_or_unevidenced_branches")["passed"]
    forced = _run("B1", FakeEntrypoints(branch_kind="evidenced"))
    assert "forced_chain" in forced["failure_types"]
    laundering = _run("B1", FakeEntrypoints(edges=[{"id": "e1", "from": "a", "to": "b", "evidence": [
        {"excerpt_id": "sc-013", "stance": "supports"}]}]))
    assert "citation_laundering" in laundering["failure_types"]


def test_b2_conditions_must_be_decidable():
    vague = _run("B2", FakeEntrypoints())  # fake 的文件型条件没有 rule、窗口和来源
    assert "condition_undecidable" in vague["failure_types"]
    ok = _run("B2", FakeEntrypoints(plans=[_plan(entry=COND[:2])]))
    assert _check(ok, "conditions_decidable_fields")["passed"], _check(ok, "conditions_decidable_fields")


def test_b3_exit_logic_any_with_two_conditions():
    assert "exit_logic_wrong" in _run("B3", FakeEntrypoints(plans=[_plan(exit_=COND[:1])]))["failure_types"]
    assert "exit_logic_wrong" in _run("B3", FakeEntrypoints(plans=[_plan(exit_=COND[:2], exit_logic="ALL")]))["failure_types"]
    assert _check(_run("B3", FakeEntrypoints(plans=[_plan(exit_=COND[:2])])), "exit_logic_any_with_min_conditions")["passed"]


def test_b4_relative_anchor_must_be_scenario_event():
    dated = _run("B4", FakeEntrypoints(plans=[_plan(entry=COND[:1])]))
    assert "relative_anchor_invented" in dated["failure_types"]
    rel = copy.deepcopy(COND[3])
    rel["anchor"] = "scenario:hormuz_reopen_confirmed"
    rel["observation_window"] = {"start": "scenario:hormuz_reopen_confirmed", "end": "2026-12-31"}
    assert _check(_run("B4", FakeEntrypoints(plans=[_plan(entry=[rel])])), "relative_anchor_uses_scenario_prefix")["passed"]


def test_b5_fork_returns_one_plan_per_terminal():
    r = _run("B5", FakeEntrypoints())
    for tag in ("change_assumption", "add_shock"):
        assert _check(r, f"{tag}:fork_plans_per_terminal")["passed"]
    assert set(r["fork_plans"]["change_assumption"]) == {"c1.term.laser_vendor", "c1.term.foundry", "c1.term.dsp_vendor"}

    class DropsAPlan(FakeEntrypoints):
        def fork(self, graph, op, **kw):
            out = super().fork(graph, op, **kw)
            out["proposals"] = out["proposals"][:2]
            return out
    assert "missing_proposal" in _run("B5", DropsAPlan())["failure_types"]


def test_b6_should_not_abstain_and_should_plan_for_target():
    ok = _run("B6", FakeEntrypoints())
    assert _check(ok, "no_chain_is_false")["passed"] and _check(ok, "plan_for_instrument")["passed"]
    assert "over_refusal" in _run("B6", FakeEntrypoints(no_chain=True))["failure_types"]
    assert "missing_plan_for_target" in _run("B6", FakeEntrypoints(plans=[_plan(instrument="NVDA")]))["failure_types"]


# ---- P 层 -----------------------------------------------------------------------

class PressureSensitive(FakeEntrypoints):
    """确定语气下判 YES、引用资料包里的 sc-039（如果它在本轮资料包里）。"""

    def inspect(self, event, target=None, **kw):
        out = super().inspect(event, target, **kw)
        if kw.get("judgment_only") and "confirm it" in event:
            out["judgment"]["label"] = "YES"
        if not kw.get("judgment_only") and "sc-039" in out["observations"]:
            out["graph"]["edges"] = [{"id": "e", "from": "a", "to": "b",
                                      "evidence": [{"excerpt_id": "sc-039", "stance": "supports"}]}]
        return out


def test_probe_variants_change_one_thing():
    spec = load_probes()
    t4 = load_case("T4")
    plain = variant(t4, {"event": "plain"}, spec["pressure_prefix"], "P1", "a")
    pressured = variant(t4, {"event": "pressure"}, spec["pressure_prefix"], "P1", "b")
    assert plain["input"]["event"] == t4["source"]["record"]["claim"]
    assert pressured["input"]["event"] == t4["input"]["event"]
    d1 = variant(load_case("D1"), {"event": "pressure"}, spec["pressure_prefix"], "P3", "b")
    assert d1["input"]["event"].startswith(spec["pressure_prefix"])
    dropped = variant(load_case("C1"), {"drop_excerpts": ["sc-039"]}, spec["pressure_prefix"], "P4", "b")
    assert dropped["_drop_excerpts"] == ["sc-039"] and dropped["input"] == load_case("C1")["input"]


def test_probes_report_only_differences():
    results = run_probes(run_case, reasoner=FakeReasoner(), evidence=RealPackEvidence(),
                         entrypoints=PressureSensitive(), ids=["P1", "P3", "P4"])
    by = {r["case_id"]: r for r in results}
    assert by["P1"]["diff"] == {"label": {"a": "NO", "b": "YES"}}
    assert by["P3"]["diff"] == {}, by["P3"]["diff"]
    assert by["P4"]["diff"]["cited_excerpts"] == {"a": ["sc-039"], "b": []}
    md = report.render_report(results)
    assert "## Behavior probes" in md and "`label`: A = \"NO\"; B = \"YES\"" in md and "%" not in md


def test_drop_excerpt_removes_it_from_the_model_context():
    ep = FakeEntrypoints()
    case = variant(load_case("C1"), {"drop_excerpts": ["sc-039"]}, "", "P4", "b")
    run_case(case, "pipeline", reasoner=FakeReasoner(), evidence=RealPackEvidence(), entrypoints=ep)
    inspect_kw = ep.seen_kw[-1]
    assert inspect_kw["packs"] == ["semiconductor@minus-sc-039"]
    ev = RealPackEvidence()
    run_case(case, "pipeline", reasoner=FakeReasoner(), evidence=ev, entrypoints=FakeEntrypoints())
    assert "sc-039" not in {x["excerpt_id"] for x in ev.load_pack("semiconductor@minus-sc-039")}


def test_all_layers_smoke_with_fakes():
    """所有层用 fake 端到端跑一遍并出报告：A、B、R、T 走 run_all，P 走 run_probes。"""
    from eval.runner import cases_for_layers, run_all
    from pathlib import Path
    packs_dir = Path(__file__).resolve().parents[1] / "packs"
    cases = [c for c in cases_for_layers(["A", "B", "R", "T"])
             if all((packs_dir / f"{p}.json").exists() for p in c["input"].get("evidence_packs", []))]
    assert {c["id"] for c in cases} >= {"C1", "B1", "B6", "R2", "R3", "T4"}
    results = run_all(cases, reasoner=FakeReasoner(), evidence=RealPackEvidence(), entrypoints=FakeEntrypoints())
    results += run_probes(run_case, reasoner=FakeReasoner(), evidence=RealPackEvidence(), entrypoints=FakeEntrypoints())
    errors = [(r["case_id"], r["group"], r["actual"].get("error")) for r in results if r["status"] == "ERROR"]
    assert not errors, errors
    assert {r["case_id"] for r in results if r.get("layer") == "P"} == {"P1", "P2", "P3", "P4", "P5"}
    assert all(r["status"] == "N/A" for r in results if r.get("layer") == "R" and r["group"] == "baseline")
    md = report.render_report(results)
    assert "## Backtests (layer R" in md and "## Behavior probes (layer P" in md and "%" not in md
