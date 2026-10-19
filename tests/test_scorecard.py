"""记分卡：六项指标、百分制、红线、README 表格（不依赖核心）。"""
from pathlib import Path

from eval import scorecard


def _r(case, layer, checks=(), group="pipeline", status="PENDING_REVIEW", **extra):
    return {"case_id": case, "layer": layer, "group": group, "status": status, "case_type": "custom",
            "checks": [{"name": n, "passed": p, "eval": "x", "failure_type": None if p else "x", "detail": ""}
                       for n, p in checks], "failure_types": [], "actual": extra.pop("actual", {}), **extra}


RESULTS = [
    _r("C1", "A", [("gate_per_plan", True)],
       actual={"plans": [{"terminal_id": "t", "gate": "WAIT", "conditions": 4, "decidable_conditions": 3}],
               "edges": 4, "model_only_edges": 1}),
    _r("C3", "A", [("change_assumption:out_of_scope_hash_unchanged", True), ("change_assumption:challenged_matches_golden", False)]),
    _r("C4", "A", [("abstained_or_only_not_recommended", True)]),
    _r("T1", "T", [("label_matches_gold", True)]),
    _r("T2", "T", [("label_matches_gold", False)], status="FAIL"),
    _r("R2", "R", [("gate_per_plan", True), ("only_allowed_excerpts_cited", True)],
       backtest={"plans": [{"outcome": "pass"}]}, contamination={"ran": True, "contaminated": False}),
    _r("K3", "R", [("gate_per_plan", True)], backtest={"plans": [{"outcome": "pass"}]},
       contamination={"ran": True, "contaminated": True}),
    _r("W1", "W", [("gate_per_plan", True)],
       research={"round1": {"model_only_edges": 5, "null_threshold_conditions": 2},
                 "final": {"model_only_edges": 3, "null_threshold_conditions": 3}}),
    _r("T1", "T", [("label_matches_gold", True)], group="baseline"),
    _r("T2", "T", [("label_matches_gold", True)], group="baseline"),
]


def _metric(card, key):
    return next(m for m in card["metrics"] if m["key"] == key)


def test_units_and_exclusions():
    card = scorecard.build(RESULTS, name="t", prompt="p7")
    assert (_metric(card, "discipline")["passed"], _metric(card, "discipline")["total"]) == (5, 5)
    assert any("K3" in e and "contaminated" in e for e in _metric(card, "discipline")["excluded"])
    assert (_metric(card, "refusal")["passed"], _metric(card, "refusal")["total"]) == (2, 3)
    assert (_metric(card, "decidable")["passed"], _metric(card, "decidable")["total"]) == (3, 4)
    assert (_metric(card, "grounding")["passed"], _metric(card, "grounding")["total"]) == (4, 5)
    assert (_metric(card, "fork")["passed"], _metric(card, "fork")["total"]) == (1, 2)
    assert (_metric(card, "research")["passed"], _metric(card, "research")["total"]) == (1, 1)
    expected = (20 * 1 + 20 * 2 / 3 + 20 * 3 / 4 + 15 * 4 / 5 + 15 * 1 / 2 + 10 * 1) / 100 * 100
    assert card["score"] == round(expected, 1) and card["trusted"]
    assert card["baseline_refusal"] == {"baseline": "2/2", "pipeline_same_units": "1/2"}


def test_missing_metrics_are_left_out_and_red_line_marks_untrusted():
    only_t = [r for r in RESULTS if r["case_id"] in ("T1", "T2") and r["group"] == "pipeline"]
    card = scorecard.build(only_t, name="t")
    assert card["weights_counted"] == 20 and card["score"] == 50.0
    leaky = RESULTS + [_r("R3", "R", [("only_allowed_excerpts_cited", False)], failure_types=["leak"])]
    leaky[-1]["failure_types"] = ["leak"]
    card = scorecard.build(leaky, name="t")
    assert not card["trusted"] and "backtest leak" in card["red_line"]
    assert "UNTRUSTED" in scorecard.render(card) and "%" not in scorecard.render(card)


def test_human_review_answers_count_once_given():
    reviewed = [dict(r) for r in RESULTS]
    reviewed[0] = dict(reviewed[0], review={"e1": "yes", "e2": "no", "e4": "yes"})
    card = scorecard.build(reviewed, name="t")
    assert _metric(card, "grounding")["total"] == 6 and _metric(card, "decidable")["total"] == 5


def test_readme_block_is_replaced_in_place(tmp_path: Path):
    readme = tmp_path / "README.md"
    readme.write_text("# Title\n\n" + scorecard.README_START + "\nold\n" + scorecard.README_END + "\n\ntail\n")
    card = scorecard.build(RESULTS, name="run-a", prompt="p7")
    scorecard.update_readme(readme, [card])
    scorecard.update_readme(readme, [card])
    text = readme.read_text()
    assert text.count(scorecard.README_START) == 1 and "old" not in text and "| run-a |" in text and text.endswith("tail\n")
