"""fake reasoner 跑 runner、假结果跑报告（不依赖核心）。见 docs/eval/test-plan.md B4。"""
import json

from eval import report
from eval.fakes import FakeEntrypoints, FakeEvidence, FakeReasoner, sample_baseline_reasoner, write_sample_results
from eval.loader import EVAL_DIR, load_all_cases, load_case
from eval.runner import run_all, run_case

CASES = load_all_cases()


def _by(results, case_id, group):
    return next(r for r in results if r["case_id"] == case_id and r["group"] == group)


def test_both_groups_produce_one_result_per_case():
    ep, reasoner = FakeEntrypoints(), FakeReasoner()
    results = run_all(CASES, reasoner=reasoner, evidence=FakeEvidence(), entrypoints=ep)
    assert len(results) == 2 * len(CASES)
    assert ep.calls, "pipeline 组应该调用核心入口"
    # baseline：每个非 fork 案例恰好一次单次 prompt
    assert len(reasoner.calls) == sum(1 for c in CASES if c["entry"] != "fork")
    t1 = _by(results, "T1", "pipeline")
    assert t1["status"] == "PENDING_REVIEW" and not t1["failure_types"]
    assert _by(results, "C3", "pipeline")["status"] == "PENDING_REVIEW"
    assert _by(results, "C3", "baseline")["status"] == "N/A"
    assert _by(results, "C4", "pipeline")["status"] == "PENDING_REVIEW"


def test_pipeline_failures_are_classified():
    ep = FakeEntrypoints(labels={"T1": "NO", "T4": "YES"}, leak_edge="c1.e5", observations=["sc-033"])
    results = run_all(CASES, ("pipeline",), reasoner=FakeReasoner(), evidence=FakeEvidence(), entrypoints=ep)
    assert "over_refusal" in _by(results, "T1", "pipeline")["failure_types"]
    assert "sycophancy" in _by(results, "T4", "pipeline")["failure_types"]
    assert "scope_violation" in _by(results, "C3", "pipeline")["failure_types"]
    c1 = _by(results, "C1", "pipeline")
    assert c1["status"] == "FAIL" and "retrieval_miss" in c1["failure_types"]
    assert c1["retrieval"]["missing"] == [x for x in load_case("C1")["expected"]["key_excerpts"] if x != "sc-033"]


def test_baseline_unparseable_and_fabricated_threshold():
    results = run_all(CASES, ("baseline",), reasoner=sample_baseline_reasoner(), evidence=FakeEvidence())
    c2 = _by(results, "C2", "baseline")
    assert c2["status"] == "FAIL" and c2["failure_types"] == ["unparseable"]
    assert "fabricated_threshold" in _by(results, "D1", "baseline")["failure_types"]
    assert "no_abstain" in _by(results, "C4", "baseline")["failure_types"]


def test_baseline_prompt_carries_the_same_material():
    reasoner = FakeReasoner()
    run_case(load_case("T3"), "baseline", reasoner=reasoner)
    assert load_case("T3")["input"]["material"] in reasoner.calls[0]
    run_case(load_case("D1"), "baseline", reasoner=reasoner, evidence=FakeEvidence())
    assert "hz-003" in reasoner.calls[1]


def test_entrypoint_exception_is_isolated():
    ep = FakeEntrypoints(raise_on={"光子芯片"})
    results = run_all(CASES, ("pipeline",), reasoner=FakeReasoner(), evidence=FakeEvidence(), entrypoints=ep)
    assert _by(results, "C1", "pipeline")["status"] == "ERROR"
    assert _by(results, "D1", "pipeline")["status"] != "ERROR"


def test_report_from_sample_results(tmp_path):
    out = tmp_path / "sample.json"
    results = write_sample_results(str(out))
    md = report.render_report(json.loads(out.read_text(encoding="utf-8")))
    header = "| " + " | ".join(report.COLUMNS) + " |"
    assert header in md
    assert "%" not in md, "不报百分比"
    assert "n/a（scenario 全文给定）" in md
    assert "当前流程不可信" in md  # sample 里 C3 有越界写入
    for r in results:
        assert f"| {r['case_id']} |" in md


def test_committed_sample_results_render():
    path = EVAL_DIR / "sample_results.json"
    md = report.render_report(json.loads(path.read_text(encoding="utf-8")))
    assert "## pipeline 组" in md and "## baseline 组" in md and "## 两组对照" in md


def test_abstain_before_inspect_is_not_silently_pending():
    """D1 期望走完 Discover → Inspect；Discover 弃权时要明确记下没跑到提案，而不是只剩「待复核」。"""
    class AbstainAll(FakeEntrypoints):
        def discover(self, event, target=None, **kw):
            return {"candidates": [], "abstained": True, "abstain_reason": "fake", "observations": []}
    r = run_case(load_case("D1"), "pipeline", reasoner=FakeReasoner(), evidence=FakeEvidence(), entrypoints=AbstainAll())
    assert r["status"] == "FAIL" and "missing_proposal" in r["failure_types"]
    reasoner = FakeReasoner(default=json.dumps({"abstained": True, "candidates": []}))
    b = run_case(load_case("D1"), "baseline", reasoner=reasoner, evidence=FakeEvidence())
    assert b["status"] == "FAIL" and "missing_proposal" in b["failure_types"]


def test_baseline_no_chain_skips_condition_checks_like_pipeline():
    reasoner = FakeReasoner(default=json.dumps({"no_chain": True, "chain": [], "conditions": []}))
    r = run_case(load_case("C2"), "baseline", reasoner=reasoner, evidence=FakeEvidence())
    assert r["status"] == "PENDING_REVIEW", r["checks"]


def test_c3_fork_gets_fixture_pack_only():
    """golden 图引用占位片段 id，fork 只能配 c1_evidence_pack，不能带真实包（同号不同义）。"""
    seen = {}

    class Spy(FakeEntrypoints):
        def fork(self, graph, op, **kw):
            seen[op["kind"]] = (kw.get("packs"), (kw.get("pack") or {}).get("pack_id"),
                                (kw.get("pack") or {}).get("synthetic"))
            return super().fork(graph, op, **kw)
    run_case(load_case("C3"), "pipeline", reasoner=FakeReasoner(), evidence=FakeEvidence(), entrypoints=Spy())
    assert seen == {"change_assumption": ([], "semiconductor", True), "add_shock": ([], "semiconductor", True)}


def test_synthetic_run_skips_retrieval_and_says_why():
    results = run_all([load_case("C1")], ("pipeline",), reasoner=FakeReasoner(), evidence=FakeEvidence(),
                      entrypoints=FakeEntrypoints(observations=[]), pack_source="synthetic")
    r = results[0]
    assert r["retrieval"] is None and "retrieval_miss" not in r["failure_types"]
    assert "撞号" in report.render_report(results)
