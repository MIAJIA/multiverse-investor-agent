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


# ---- B 层与 R 层（第 2 版 test set）-----------------------------------------------
import datetime as _dt
import json as _json
from pathlib import Path as _Path

from eval.loader import B_IDS, R_IDS

_PACKS = {p.stem: {x["excerpt_id"]: x for x in _json.loads(p.read_text(encoding="utf-8"))["excerpts"]}
          for p in (_Path(__file__).resolve().parents[1] / "packs").glob("*.json")}


def _excerpt(case, eid):
    for pid in case["input"]["evidence_packs"]:
        if eid in _PACKS.get(pid, {}):
            return _PACKS[pid][eid]
    raise AssertionError(f"{case['id']}: {eid} 不在 {case['input']['evidence_packs']} 的真实包里")


def test_b_cases_are_complete_and_cite_real_excerpts():
    for case_id in B_IDS:
        c = load_case(case_id)
        assert c["layer"] == "B" and c["entry"] in {"inspect", "fork"}, case_id
        assert c["expected"]["behavior"] and c["human_review"], case_id
        for pid in c["input"].get("evidence_packs", []):
            assert pid in _PACKS, (case_id, pid)
        for eid in c["expected"].get("key_excerpts", []) + c["expected"].get("must_not_cite_as_support", []):
            _excerpt(c, eid)


def test_backtests_are_offline_and_do_not_leak():
    for case_id in R_IDS:
        c = load_case(case_id)
        as_of = _dt.date.fromisoformat(c["as_of"])
        assert c["online"] is False and c["online_locked"] is True, case_id
        allowed = set(c["allowed_excerpts"])
        outcome = set(c["outcome"]["excerpt_ids"])
        assert not allowed & outcome, (case_id, allowed & outcome)
        assert not allowed & set(c["excluded"]), case_id
        for eid in allowed:
            x = _excerpt(c, eid)
            if _dt.date.fromisoformat(x["date"]) > as_of:
                assert c["allowed_exceptions"].get(eid), f"{case_id}: {eid} 日期 {x['date']} 晚于决策时点，必须写明为什么当时可见"
        for eid in outcome:
            assert _dt.date.fromisoformat(_excerpt(c, eid)["date"]) > as_of, (case_id, eid)
        for eid in c["expected"]["backtest"]["counter_excerpts_to_address"]:
            assert eid in allowed, f"{case_id}: 要求回应的反方片段 {eid} 不在时点资料包里"
        for obs in c["outcome"]["observations"]:
            assert _dt.date.fromisoformat(obs["coverage"]["end"]) > as_of, case_id
            for r in obs["records"]:
                assert obs["coverage"]["start"] <= r["date"] <= obs["coverage"]["end"], (case_id, r)
        assert c["contamination_probe"] and "only_allowed_excerpts_cited" in c["auto_checks"]


def test_backtest_packs_only_drop_excerpts_for_a_reason():
    """时点资料包外的片段，要么在 excluded 里写了原因，要么日期本来就晚于决策时点之外的其他情况不存在。"""
    for case_id in R_IDS:
        c = load_case(case_id)
        as_of = _dt.date.fromisoformat(c["as_of"])
        allowed = set(c["allowed_excerpts"])
        for pid in c["input"]["evidence_packs"]:
            for eid, x in _PACKS[pid].items():
                if eid in allowed or eid in c["excluded"]:
                    continue
                assert _dt.date.fromisoformat(x["date"]) > as_of, \
                    f"{case_id}: {eid}（{x['date']}）在决策时点前就有，既没放进资料包也没写排除原因"
