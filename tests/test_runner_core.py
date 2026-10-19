"""runner 与真实核心入口的契约（依赖核心）。

用 ScriptedReasoner（实现核心的 complete 协议，不调模型）跑 T1–T6、C3、C4 的 pipeline 组：
检查 runner 传的参数（packs、judgment_only、fork 的 op）核心都接受，返回结构 runner 都读得懂。
E3 的哈希比对在这里走的是真实核心的规范形式。
"""
import pytest

pytest.importorskip("catalyst", reason="核心包 catalyst 尚未落地")

from eval.fakes import ScriptedReasoner  # noqa: E402
from eval.loader import load_case  # noqa: E402
from eval.runner import prepare_packs, run_case  # noqa: E402
from tests import _adapter  # noqa: E402


@pytest.fixture
def evidence(tmp_path):
    return _adapter.core_evidence_provider(tmp_path)  # 空目录：强制走合成包回退


@pytest.mark.parametrize("case_id", ["T1", "T2", "T3", "T4", "T5", "T6"])
def test_causalt5k_judgment_only(case_id, evidence):
    r = run_case(load_case(case_id), "pipeline", reasoner=ScriptedReasoner(), evidence=evidence,
                 entrypoints=_adapter.core_entrypoints())
    assert r["status"] == "PENDING_REVIEW", r
    assert r["actual"]["label"] == load_case(case_id)["expected"]["label"]


def test_causalt5k_wrong_label_is_classified(evidence):
    r = run_case(load_case("T4"), "pipeline", reasoner=ScriptedReasoner(labels={"T4": "YES"}), evidence=evidence,
                 entrypoints=_adapter.core_entrypoints())
    assert r["status"] == "FAIL" and "sycophancy" in r["failure_types"]


def test_c4_discover_abstains(evidence):
    r = run_case(load_case("C4"), "pipeline", reasoner=ScriptedReasoner(), evidence=evidence,
                 entrypoints=_adapter.core_entrypoints())
    assert r["status"] == "PENDING_REVIEW", r
    assert r["actual"]["candidates"] == 0
    assert any("合成占位" in n for n in r["notes"]), "资料包还没交付时应该退回合成包并写明"


def test_c3_fork_against_core(evidence):
    r = run_case(load_case("C3"), "pipeline", reasoner=ScriptedReasoner(), evidence=evidence,
                 entrypoints=_adapter.core_entrypoints())
    failed = [c for c in r["checks"] if not c["passed"]]
    assert not failed, failed
    assert r["status"] == "PENDING_REVIEW"


def test_c3_missed_impact_is_reported(evidence):
    reasoner = ScriptedReasoner(fork_assessment={"change_assumption": {"c1.laser_demand": "challenged"}})
    r = run_case(load_case("C3"), "pipeline", reasoner=reasoner, evidence=evidence,
                 entrypoints=_adapter.core_entrypoints())
    assert "missed_impact" in r["failure_types"]
    assert "scope_violation" not in r["failure_types"]


def test_same_packs_for_both_groups(evidence):
    packs, notes = prepare_packs(load_case("C2"), evidence)
    assert packs == ["semiconductor"], "web pack 不存在时两个组都不带它"
    assert any("web" in n for n in notes)
