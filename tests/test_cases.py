"""案例文件与 CausalT5k 选例规则（不依赖核心）。见 docs/eval/test-plan.md B2。"""
import re
from collections import Counter

from eval.loader import CAUSALT5K_IDS, CUSTOM_IDS, load_case

T = [load_case(i) for i in CAUSALT5K_IDS]
C = [load_case(i) for i in CUSTOM_IDS]


def test_label_balance_and_l3():
    assert Counter(c["expected"]["label"] for c in T) == {"YES": 2, "NO": 2, "AMBIGUOUS": 2}
    assert any(c["source"]["record"]["pearl_level"] == "L3" for c in T)


def test_two_no_cases_use_different_traps():
    traps = [c["expected"]["trap"] for c in T if c["expected"]["label"] == "NO"]
    assert len(traps) == 2 and all(traps) and traps[0] != traps[1]


def test_probes():
    probes = {c["probe"]: c for c in T if c["probe"]}
    assert set(probes) == {"skepticism_trap", "sycophancy"}
    assert probes["skepticism_trap"]["expected"]["label"] == "YES"
    assert probes["sycophancy"]["expected"]["label"] == "NO"
    syc = probes["sycophancy"]
    assert syc["input"]["event"] != syc["source"]["record"]["claim"]
    assert syc["input"]["event"].endswith(syc["source"]["record"]["claim"])
    assert syc["input"]["material"] == syc["source"]["record"]["scenario"]


def test_provenance_and_judgment_only():
    for c in T:
        s = c["source"]
        assert re.fullmatch(r"[0-9a-f]{40}", s["commit"])
        assert s["repo"].startswith("https://github.com/") and s["commit"] in s["url"]
        assert s["clean_id"] and s["original_id"]
        assert s["record"]["label"] == c["expected"]["label"]
        assert c["entry"] == "inspect" and c["input"]["judgment_only"] is True
        assert c["expected"]["produce_proposal"] is False


def test_custom_cases_are_complete():
    for c in C:
        assert c["entry"] in {"discover", "inspect", "fork"}, c["id"]
        assert c["input"] and c["expected"]["behavior"] and c["evals"], c["id"]
    by = {c["id"]: c for c in C}
    assert by["C4"]["expected"]["abstain"] is True
    assert "E3" in by["C3"]["evals"]
    assert by["D1"]["expected"]["gate"] == "WAIT"


def test_online_cases_are_declared_not_hardcoded():
    """联网由 --online 控制：evidence_packs 里不再出现旧占位名 web；W 层案例标了 run_variants。"""
    for case_id in CUSTOM_IDS + ["W1"]:
        assert "web" not in load_case(case_id)["input"].get("evidence_packs", []), case_id
    w1 = load_case("W1")
    assert w1["entry"] == "inspect" and w1["run_variants"] == ["online"]
    assert w1["input"]["evidence_packs"] == [] and w1["recording"]["path"]
    for case_id in ("C2", "D1"):
        assert load_case(case_id)["run_variants"] == ["offline", "online"]
