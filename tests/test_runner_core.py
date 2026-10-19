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
    return _adapter.core_evidence_provider(tmp_path)  # 空目录：没有真实包


@pytest.fixture
def real_evidence():
    return _adapter.core_evidence_provider()  # 仓库 packs/ 下的真实包


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


def test_c4_discover_abstains_synthetic(evidence):
    r = run_case(load_case("C4"), "pipeline", reasoner=ScriptedReasoner(), evidence=evidence,
                 entrypoints=_adapter.core_entrypoints(), pack_source="synthetic")
    assert r["status"] == "PENDING_REVIEW", r
    assert r["actual"]["candidates"] == 0
    assert any("合成占位" in n for n in r["notes"])


def test_c4_discover_abstains_real(real_evidence):
    r = run_case(load_case("C4"), "pipeline", reasoner=ScriptedReasoner(), evidence=real_evidence,
                 entrypoints=_adapter.core_entrypoints())
    assert r["status"] == "PENDING_REVIEW", r
    assert not r["notes"], "真实包齐全时不应有任何回退说明"


@pytest.mark.parametrize("which", ["evidence", "real_evidence"])
def test_c3_fork_against_core(which, request):
    """C3 不管本轮是不是真实包，都只配 golden 图 + c1_evidence_pack。"""
    r = run_case(load_case("C3"), "pipeline", reasoner=ScriptedReasoner(), evidence=request.getfixturevalue(which),
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


def test_real_mode_without_real_packs_does_not_fall_back(evidence):
    packs, notes = prepare_packs(load_case("C2"), evidence, "real")
    assert packs == [] and len(notes) == 2, "real 模式缺包就不带，不拿合成包补"


def test_real_mode_uses_real_packs_only(real_evidence):
    packs, notes = prepare_packs(load_case("C2"), real_evidence, "real")
    assert packs == ["semiconductor"] and any("web" in n for n in notes)
    assert real_evidence.pack("semiconductor").synthetic is False


def test_real_mode_refuses_provider_already_holding_synthetic(real_evidence):
    """同一个 provider 先跑过 synthetic，再跑 real：不能悄悄用到注册进去的占位包。"""
    prepare_packs(load_case("D1"), real_evidence, "synthetic")
    packs, notes = prepare_packs(load_case("D1"), real_evidence, "real")
    assert packs == [] and any("合成包" in n for n in notes)


def test_key_excerpts_exist_in_real_packs(real_evidence):
    """C1、C2、D1 的关键片段都要在真实包里，且不是占位片段。"""
    for case_id in ("C1", "C2", "D1"):
        case = load_case(case_id)
        ids = {x["excerpt_id"] for p in case["input"]["evidence_packs"] if p != "web"
               for x in real_evidence.load_pack(p)}
        missing = set(case["expected"]["key_excerpts"]) - ids
        assert not missing, (case_id, missing)
