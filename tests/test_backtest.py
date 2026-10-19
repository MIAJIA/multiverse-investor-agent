"""R 层回测：时点资料包、强制离线、泄漏、污染、按事后真相回判。

模型一侧用 fake；事后回判用核心真实的条件判定（经 _adapter），核心不在时跳过回判相关用例。
"""
import copy

import pytest

from eval import report, scoring
from eval.backtest import BacktestOnlineError, point_in_time_packs
from eval.fakes import FakeEntrypoints, FakeReasoner, RealPackEvidence
from eval.loader import load_case
from eval.runner import run_case
from tests import _adapter


def _cond(cid, kind, predicate, series=None, source=None, comparator=None, threshold=None, start="2026-06-21",
          end="2026-07-08", deadline=None, note=None):
    return {"id": cid, "claim_id": "x", "kind": kind, "predicate": predicate, "series": series, "source": source,
            "comparator": comparator, "threshold": threshold, "threshold_note": note or "test",
            "anchor": start, "deadline": deadline or end, "observation_window": {"start": start, "end": end},
            "rule": "test", "verification_status": "verifiable", "evaluation_status": "unknown"}


def _plan(entry, exit_=(), tid="t.brent"):
    return {"terminal_id": tid, "gate": "WAIT", "direction": {"instrument": "BZ", "side": "short"},
            "entry_conditions": list(entry), "exit_conditions": list(exit_), "exit_logic": "ANY",
            "user_judgment": {"requires_user_confirmation": True}, "status": "draft", "support_status": "unknown"}


TRANSITS = "portwatch.hormuz.daily_transits"
CLOSURE = "hormuz.closure_or_attack"


def _run(case_id, ep, reasoner=None, online=False, evaluate=None):
    return run_case(load_case(case_id), "pipeline", reasoner=reasoner or FakeReasoner(), evidence=RealPackEvidence(),
                    entrypoints=ep, online=online, evaluate_condition=evaluate)


def test_backtest_refuses_online():
    r = _run("R2", FakeEntrypoints(), online=True)
    assert r["status"] == "ERROR" and "offline" in r["actual"]["error"]
    with pytest.raises(BacktestOnlineError):
        from eval.backtest import refuse_online
        refuse_online(load_case("R3"), True)


def test_point_in_time_pack_holds_exactly_the_allowed_excerpts():
    ev = RealPackEvidence()
    for cid in ("R2", "R3"):
        case = load_case(cid)
        packs, placed = point_in_time_packs(case, ev)
        assert placed == set(case["allowed_excerpts"])
        assert {x["excerpt_id"] for p in packs for x in ev.load_pack(p)} == set(case["allowed_excerpts"])
        assert not placed & set(case["outcome"]["excerpt_ids"])


def test_backtest_passes_today_and_offline_to_the_core():
    ep = FakeEntrypoints(plans=[_plan([])])
    _run("R2", ep)
    kw = ep.seen_kw[-1]
    assert kw["config"] == {"online": False, "today": "2026-06-21"}
    assert kw["packs"] == ["hormuz@asof-2026-06-21"]


def test_leak_is_detected_and_triggers_the_failure_criterion():
    clean = _run("R2", FakeEntrypoints(plans=[_plan([])], edges=[{"id": "e", "from": "a", "to": "b", "evidence": [
        {"excerpt_id": "hz-010", "stance": "contradicts"}]}]))
    assert all(c["passed"] for c in clean["checks"] if c["failure_type"] == "leak")
    leaky = _run("R2", FakeEntrypoints(plans=[_plan([])], edges=[{"id": "e", "from": "a", "to": "b", "evidence": [
        {"excerpt_id": "hz-012", "stance": "contradicts"}]}]))
    assert "leak" in leaky["failure_types"]
    assert scoring.failure_criteria([leaky], "pipeline")["untrustworthy"]
    assert "R2" in report.render_report([leaky])


def test_contamination_probe_flags_recalled_outcomes():
    recalls = FakeReasoner(responses={"July 2026": "The IRGC closed it again on July 12 and Brent went back to $105."})
    r = _run("R2", FakeEntrypoints(plans=[_plan([])]), reasoner=recalls)
    assert r["contamination"]["contaminated"] and "July 12" in r["contamination"]["markers_hit"]
    clean = _run("R2", FakeEntrypoints(plans=[_plan([])]), reasoner=FakeReasoner(default="I do not know."))
    assert clean["contamination"]["ran"] and not clean["contamination"]["contaminated"]
    assert "Not contaminated: R2" in report.render_report([clean])


# ---- 按事后真相回判（用核心的条件判定）--------------------------------------------

@pytest.fixture
def evaluate():
    return _adapter.core_condition_evaluator()


def test_r2_high_threshold_avoids_the_reversal(evaluate):
    plan = _plan([_cond("c.transits", "numeric", "observed_by", series=TRANSITS, comparator=">=", threshold=60)])
    r = _run("R2", FakeEntrypoints(plans=[plan]), evaluate=evaluate)
    assert next(c for c in r["checks"] if c["name"] == "backtest_outcome")["passed"], r["backtest"]
    assert r["backtest"]["plans"][0]["decidable"]


def test_r2_low_threshold_needs_an_exit_on_july_12(evaluate):
    entry = [_cond("c.transits", "numeric", "observed_by", series=TRANSITS, comparator=">=", threshold=40)]
    exit_ = [_cond("c.closure", "event", "observed_by", source=CLOSURE, start="2026-06-21", end="2026-07-31")]
    no_exit = _run("R2", FakeEntrypoints(plans=[_plan(entry)]), evaluate=evaluate)
    assert "backtest_wrong_call" in no_exit["failure_types"], no_exit["backtest"]
    with_exit = _run("R2", FakeEntrypoints(plans=[_plan(entry, exit_)]), evaluate=evaluate)
    assert "backtest_wrong_call" not in with_exit["failure_types"], with_exit["backtest"]


def test_conditions_that_match_no_outcome_data_are_undecidable(evaluate):
    plan = _plan([_cond("c.vague", "event", "observed_by", source="news.general")])
    r = _run("R2", FakeEntrypoints(plans=[plan]), evaluate=evaluate)
    assert "condition_undecidable" in r["failure_types"]


def test_r3_document_condition_not_met_by_may_20(evaluate):
    doc = _cond("c.rev", "document", "observed_by", source="NVIDIA 10-Q", start="2026-01-16", end="2026-05-20")
    r = _run("R3", FakeEntrypoints(plans=[_plan([doc], tid="t.nvda")]), evaluate=evaluate)
    assert next(c for c in r["checks"] if c["name"] == "backtest_outcome")["passed"], r["backtest"]
    assert r["backtest"]["plans"][0]["decidable"]


# ---- K3（经典案例，资料包在 evidence 分支）--------------------------------------------

def _k3_or_skip():
    from pathlib import Path
    if not (Path(__file__).resolve().parents[1] / "packs" / "opec2022.json").exists():
        pytest.skip("packs/opec2022.json 还没合并进来（evidence 分支 2553a9f）")


def _k3_plan(entry, exit_=()):
    return _plan(entry, exit_, tid="t.brent.long")


def test_k3_waiting_for_the_production_survey_holds_off(evaluate):
    _k3_or_skip()
    entry = [_cond("c.cut", "numeric", "observed_by", series="Reuters OPEC survey", comparator=">=", threshold=1.0,
                   start="2022-10-05", end="2022-12-09")]
    r = _run("K3", FakeEntrypoints(plans=[_k3_plan(entry)]), evaluate=evaluate)
    assert next(c for c in r["checks"] if c["name"] == "backtest_outcome")["passed"], r["backtest"]
    assert r["backtest"]["plans"][0]["decidable"]
    assert not any(c["failure_type"] == "leak" and not c["passed"] for c in r["checks"])


def test_k3_entering_on_price_needs_an_exit_when_the_survey_disappoints(evaluate):
    _k3_or_skip()
    entry = [_cond("c.price", "numeric", "observed_by", series="Brent spot", comparator=">=", threshold=95,
                   start="2022-10-05", end="2022-12-09")]
    exit_ = [_cond("c.short", "numeric", "observed_by", series="opec.actual_output_cut_mbd", comparator="<", threshold=1.0,
                   start="2022-10-05", end="2022-12-09")]
    no_exit = _run("K3", FakeEntrypoints(plans=[_k3_plan(entry)]), evaluate=evaluate)
    assert "backtest_wrong_call" in no_exit["failure_types"], no_exit["backtest"]
    with_exit = _run("K3", FakeEntrypoints(plans=[_k3_plan(entry, exit_)]), evaluate=evaluate)
    assert "backtest_wrong_call" not in with_exit["failure_types"], with_exit["backtest"]


def test_k3_point_in_time_pack_excludes_the_outcome():
    _k3_or_skip()
    case = load_case("K3")
    ev = RealPackEvidence()
    packs, placed = point_in_time_packs(case, ev)
    assert placed == {f"op-00{i}" for i in range(1, 10)}
    dates = {x["excerpt_id"]: x["date"] for x in ev.load_pack("opec2022")}
    assert all(dates[e] <= case["as_of"] for e in placed)
    assert all(dates[e] > case["as_of"] for e in case["outcome"]["excerpt_ids"])
