"""LLM judge：整体质量打分、替代待复核、人工复核优先、记分卡单列（不依赖核心，用假模型）。"""
import json

from eval import judge, scorecard


class FakeJudge:
    """按案例给分：prompt 里出现 'Case T2' 就判 poor 并标严重问题。"""

    def __init__(self):
        self.prompts = []

    def complete(self, *, stage, system, user, schema):
        self.prompts.append(user)
        poor = "Case T2" in user
        v = {"overall": 3 if poor else 8, "verdict": "poor" if poor else "good",
             "strengths": [] if poor else ["grounded"], "problems": ["refused a supported claim"] if poor else [],
             "critical_issue": "abstained against clear evidence" if poor else None, "summary": "fake"}

        class C:
            text = json.dumps(v)
        return C()


def _r(case, layer, status="PENDING_REVIEW", **extra):
    return {"case_id": case, "group": "pipeline", "layer": layer, "status": status, "case_type": "custom",
            "checks": extra.pop("checks", []), "failure_types": [], **extra}


RESULTS = [
    _r("T1", "T", actual={"label": "YES", "rationale": "natural experiment"}),
    _r("T2", "T", actual={"label": "AMBIGUOUS", "rationale": "unclear"}),
    _r("C1", "A", actual={}, output={"nodes": [], "edges": [], "plans": []},
       checks=[{"name": "gate_per_plan", "passed": True, "eval": "E2", "failure_type": None, "detail": ""}]),
    _r("P1", "P", actual={}),
    _r("C4", "A", status="ERROR", actual={"error": "x"}),
]


def test_judges_cases_holistically_and_skips_probes_and_errors():
    fake = FakeJudge()
    verdicts = judge.judge_all(RESULTS, fake, model="fake-judge")
    assert [v["case_id"] for v in verdicts] == ["T1", "T2", "C1"]
    assert "Reference rationale" in fake.prompts[0] and "What a good answer does" in fake.prompts[2]
    s = judge.summary(verdicts)
    assert s["average"] == round((8 + 3 + 8) / 3, 1) and s["verdicts"] == {"good": 2, "acceptable": 0, "poor": 1}
    assert s["critical"] == [{"case_id": "T2", "issue": "abstained against clear evidence"}]
    md = judge.render(verdicts, "fake-judge")
    assert "Average quality" in md and "%" not in md


def test_verdicts_replace_pending_review_but_not_a_human_review():
    verdicts = judge.judge_all(RESULTS, FakeJudge(), model="fake-judge")
    human = dict(RESULTS[0], review={"source": "human", "e1": "no"})
    merged = {r["case_id"]: r for r in judge.apply([human] + RESULTS[1:], verdicts)}
    assert "judge" not in merged["T1"] and merged["T1"]["status"] == "PENDING_REVIEW"
    assert merged["T2"]["status"] == "FAIL" and "judge_poor" in merged["T2"]["failure_types"]
    assert merged["C1"]["status"] == "PASS"


def test_scorecard_reports_judge_next_to_the_score():
    verdicts = judge.judge_all(RESULTS, FakeJudge(), model="fake-judge")
    card = scorecard.build(judge.apply(RESULTS, verdicts), name="t", prompt="p7")
    assert card["judge"]["average"] == 6.3 and card["judge"]["poor"] == ["T2"] and card["judge"]["model"] == "fake-judge"
    assert "LLM judge (overall quality, fake-judge): 6.3 / 10" in scorecard.render(card)
    assert card["total"] == round(card["score"] * 0.5 + 63 * 0.5, 1)
    assert f"| **{card['total']}** | {card['score']} | 6.3 |" in scorecard.readme_block([card])
