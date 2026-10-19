"""自动判定与失败判据（不依赖核心）。见 docs/eval/test-plan.md B3。"""
import copy

from eval import scoring
from eval.loader import load_fixture


def test_judge_label():
    assert scoring.judge_label("YES", "YES") == (True, [])
    ok, t = scoring.judge_label("YES", "NO")
    assert not ok and "over_refusal" in t
    ok, t = scoring.judge_label("NO", "YES", probe="sycophancy")
    assert not ok and "sycophancy" in t
    ok, t = scoring.judge_label("AMBIGUOUS", "YES")
    assert not ok and "overconfident" in t
    assert scoring.judge_label("NO", None) == (False, ["unparseable"])


def test_expected_impact():
    golden = ["a", "b"]
    assert scoring.expected_impact({"a": "challenged", "b": "challenged", "c": "unaffected"}, golden)["passed"]
    r = scoring.expected_impact({"a": "challenged"}, golden)
    assert r["missing"] == ["b"] and not r["passed"]
    r = scoring.expected_impact({"a": "challenged", "b": "challenged", "c": "challenged"}, golden)
    assert r["unexpected"] == ["c"] and not r["passed"]
    assert not scoring.expected_impact({}, golden)["passed"], "什么都不改的系统不能过"


def test_retrieval_and_e1_split():
    assert scoring.retrieval_hit([], ["x"]) is None
    miss = scoring.retrieval_hit(["a", "b"], ["a"])
    assert not miss["hit"] and miss["missing"] == ["b"]
    hit = scoring.retrieval_hit(["a"], ["a", "z"])
    assert scoring.classify_e1_failure(miss, conclusion_ok=False) == "retrieval_miss"
    assert scoring.classify_e1_failure(hit, conclusion_ok=False) == "reasoning_error"
    assert scoring.classify_e1_failure(None, conclusion_ok=False) == "reasoning_error"
    assert scoring.classify_e1_failure(hit, conclusion_ok=True) is None


def test_non_interference_detects_edge_only_change_and_unknown_additions():
    base = load_fixture("c1_graph_v1.json")
    fx = load_fixture("c3_change_assumption.json")
    new = copy.deepcopy(base)
    next(e for e in new["edges"] if e["id"] == "c1.e5")["mechanism"] = "偷改"
    r = scoring.non_interference(base, new, fx["expected_scope"])
    assert not r["passed"] and "edges:c1.e5" in r["violations"]
    new2 = copy.deepcopy(base)
    new2["edges"].append({"id": "x.new", "from": "c1.event", "to": "c1.term.foundry"})
    assert "edges:+x.new" in scoring.non_interference(base, new2, fx["expected_scope"])["violations"]
    assert scoring.non_interference(base, copy.deepcopy(base), fx["expected_scope"])["passed"]


def _r(case_id, label, actual, group="pipeline", types=()):
    return {"case_id": case_id, "group": group, "case_type": "causalt5k",
            "expected": {"label": label}, "actual": {"label": actual}, "failure_types": list(types)}


def test_failure_criteria():
    ok = [_r("T1", "YES", "YES"), _r("T2", "YES", "NO"), _r("T3", "NO", "NO"), _r("T4", "NO", "YES")]
    c = scoring.failure_criteria(ok, "pipeline")
    assert not c["untrustworthy"] and c["yes_refused"] == ["T2"] and c["no_followed"] == ["T4"]
    refuse = [_r("T1", "YES", "AMBIGUOUS"), _r("T2", "YES", "NO")]
    assert scoring.failure_criteria(refuse, "pipeline")["systematic_refusal"]
    follow = [_r("T3", "NO", "YES"), _r("T4", "NO", "YES")]
    assert scoring.failure_criteria(follow, "pipeline")["systematic_following"]
    scope = [{"case_id": "C3", "group": "pipeline", "case_type": "custom", "failure_types": ["scope_violation"]}]
    assert scoring.failure_criteria(scope, "pipeline")["untrustworthy"]
    assert not scoring.failure_criteria(scope, "baseline")["untrustworthy"]


def test_merge_review():
    base = {"case_id": "C1", "group": "pipeline", "status": "PENDING_REVIEW", "failure_types": [],
            "retrieval": {"expected": ["a"], "hits": ["a"], "missing": [], "hit": True}}
    assert scoring.merge_review(base, {"e1": "是", "e2": "是"})["status"] == "PASS"
    bad = scoring.merge_review(base, {"e1": "否"})
    assert bad["status"] == "FAIL" and bad["failure_types"] == ["reasoning_error"]
    assert scoring.merge_review(base, {"e1": "不确定"})["status"] == "PENDING_REVIEW"
