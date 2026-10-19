"""harness 的离线测试：脚本化 Reasoner，不调模型。"""
import json

import pytest

from catalyst import entrypoints as ep
from catalyst.evidence import EvidenceProvider
from catalyst.reasoner import CassetteMiss, Completion, RecordingReasoner, ReplayReasoner, strict_schema
from catalyst.schema import InspectOutput
from catalyst.store import RunStore

PACK = {"pack_id": "hz", "synthetic": True, "excerpts": [
    {"source_id": "s-a", "excerpt_id": "hz-1", "source": "wire", "date": "2026-10-16", "stance": "supports",
     "text": "官方表示海峡下周对商船重新开放。"},
    {"source_id": "s-c", "excerpt_id": "hz-3", "source": "wire", "date": "2026-04-20", "stance": "contradicts",
     "text": "上次宣布开放之后过境量并未恢复。"},
]}


def _good(threshold=None, note="资料包没有过境恢复基准，阈值由用户确认"):
    return {
        "no_chain": False, "no_chain_reason": None,
        "nodes": [
            {"id": "h.open", "role": "event", "statement": "霍尔木兹海峡宣布对商船重新开放", "original_statement": "霍尔木兹海峡下周重开",
             "evidence_status": "unknown", "time_bucket": "2026-10", "instruments": []},
            {"id": "h.transits", "role": "intermediate", "statement": "日过境量恢复", "original_statement": "日过境量恢复",
             "evidence_status": "contradicted", "time_bucket": "2026-11", "instruments": []},
            {"id": "h.brent", "role": "terminal", "statement": "Brent 近月走弱", "original_statement": "Brent 近月走弱",
             "evidence_status": "unknown", "time_bucket": "2026-11", "instruments": ["BZ"]},
        ],
        "edges": [
            {"id": "h.e1", "from": "h.open", "to": "h.transits", "channel": "logistics", "sign": "+", "lag_days": 7,
             "mechanism": "开放后船东恢复通行", "model_only": False,
             "evidence": [{"tier": "T2", "source_id": "s-c", "excerpt_id": "hz-3", "stance": "contradicts",
                           "supports": "宣布开放 ≠ 过境恢复", "rebuttal": None}]},
            {"id": "h.e2", "from": "h.transits", "to": "h.brent", "channel": "supply", "sign": "-", "lag_days": 3,
             "mechanism": "供给恢复压低近月", "model_only": True, "evidence": []},
        ],
        "conditions": [
            {"id": "cond.transits", "claim_id": "h.transits", "kind": "numeric", "predicate": "observed_by",
             "series": "portwatch.hormuz.daily_transits", "source": None, "comparator": ">=", "threshold": threshold,
             "threshold_note": note, "anchor": "2026-10-18", "deadline": "2026-11-30",
             "observation_window": {"start": "2026-10-18", "end": "2026-11-30"},
             "rule": "窗口内日过境量达到阈值即 met", "verification_status": "unverified"},
        ],
        "proposal": {
            "direction": {"instrument": "BZ", "side": "short", "horizon_days": 30, "note": None},
            "entry_condition_ids": ["cond.transits"], "exit_condition_ids": [], "exit_logic": "ANY",
            "key_dependency": {"condition_id": "cond.transits", "claim_id": "h.transits", "why": "真通航而非宣布开放"},
            "user_judgment": {"original_statement": "霍尔木兹海峡下周重开", "clarified_statement": "2026-11-30 前过境恢复",
                              "criteria": None, "deadline": "2026-11-30", "requires_user_confirmation": True}},
    }


class Scripted:
    name = "scripted"

    def __init__(self, outputs):
        self.outputs, self.prompts = list(outputs), []

    def complete(self, *, stage, system, user, schema):
        self.prompts.append(user)
        return Completion(json.dumps(self.outputs.pop(0), ensure_ascii=False), {"model": "scripted"})


@pytest.fixture
def ev():
    e = EvidenceProvider("/nonexistent")
    e.register(PACK)
    return e


CFG = ep.Config(packs=["hz"], today="2026-10-18", run_prefix="d1")


def test_retry_feeds_back_errors_then_succeeds(ev, tmp_path):
    bad = _good(note="")  # null 阈值没写说明 → 校验失败
    r = Scripted([bad, _good()])
    res = ep.inspect("霍尔木兹海峡下周重开", reasoner=r, evidence=ev, config=CFG, store=RunStore(tmp_path))
    assert res["ok"] and res["attempts"] == 2
    assert "cond.transits" in r.prompts[1] and "threshold_note" in r.prompts[1]
    p = res["proposal"]
    assert p["gate"] == "WAIT" and p["status"] == "draft" and p["meta"]["approval_required"] is True
    assert p["entry_conditions"][0]["evaluation_status"] == "unknown"
    trace = (tmp_path / "trace.jsonl").read_text().splitlines()
    assert [json.loads(l)["ok"] for l in trace] == [False, True]
    assert (tmp_path / "snapshots" / "d1-v1.json").exists()


def test_failed_output_never_reaches_snapshot(ev, tmp_path):
    bad = _good(note="")
    res = ep.inspect("x", reasoner=Scripted([bad, bad, bad]), evidence=ev, config=CFG, store=RunStore(tmp_path))
    assert not res["ok"] and res["graph"] is None and res["attempts"] == 3
    assert not (tmp_path / "snapshots").exists()


def test_unknown_excerpt_is_rejected(ev):
    out = _good()
    out["edges"][0]["evidence"][0]["excerpt_id"] = "hz-999"
    res = ep.inspect("x", reasoner=Scripted([out] * 3), evidence=ev, config=CFG)
    assert not res["ok"] and any("hz-999" in e for e in res["errors"])


def test_record_then_replay_is_deterministic(ev, tmp_path):
    rec = RecordingReasoner(Scripted([_good()]), tmp_path / "cassette.jsonl")
    first = ep.inspect("霍尔木兹海峡下周重开", reasoner=rec, evidence=ev, config=CFG)
    again = ep.inspect("霍尔木兹海峡下周重开", reasoner=ReplayReasoner(tmp_path / "cassette.jsonl"), evidence=ev, config=CFG)
    assert again["graph"] == first["graph"] and again["proposal"] == first["proposal"]
    with pytest.raises(CassetteMiss):  # 输入变了，旧录音不能冒充
        ep.inspect("别的事件", reasoner=ReplayReasoner(tmp_path / "cassette.jsonl"), evidence=ev, config=CFG)


def test_fork_scope_enforced_through_entrypoint(ev):
    base = ep.inspect("霍尔木兹海峡下周重开", reasoner=Scripted([_good()]), evidence=ev, config=CFG)
    op = {"kind": "change_assumption", "target": "h.transits", "value": "过境恢复推迟到 12 月"}
    outside = {"node_updates": [{"id": "h.open", "statement": "改了范围外"}], "edge_updates": [], "condition_updates": [],
               "assessment": [], "next_checks": []}
    inside = {"node_updates": [{"id": "h.transits", "statement": "过境恢复推迟到 12 月"}], "edge_updates": [],
              "condition_updates": [], "next_checks": ["12 月 PortWatch 日过境量"],
              "assessment": [{"claim_id": "h.transits", "status": "challenged", "reason": "时间推迟"},
                             {"claim_id": "h.brent", "status": "challenged", "reason": "上游推迟"}]}
    r = Scripted([outside, inside])
    res = ep.fork(base["graph"], op, reasoner=r, evidence=ev, config=CFG, proposal=base["proposal"])
    assert res["ok"] and res["attempts"] == 2 and "h.open" in r.prompts[1]
    assert res["scenario"]["assessment"]["h.open"] == "unaffected"
    assert res["diff"]["nodes_changed"] == ["h.transits"]
    assert res["proposal"]["support_status"] == "challenged"
    assert res["proposal"]["scenario_ref"]["base_version"] == "d1-v1"
    assert res["base_graph"] == base["graph"]


def test_strict_schema_closes_every_object():
    s = strict_schema(InspectOutput.model_json_schema(by_alias=True))

    def objects(n):
        if isinstance(n, dict):
            if n.get("type") == "object" and "properties" in n:
                yield n
            for v in n.values():
                yield from objects(v)
        elif isinstance(n, list):
            for v in n:
                yield from objects(v)

    objs = list(objects(s))
    assert objs and all(o["additionalProperties"] is False and set(o["required"]) == set(o["properties"]) for o in objs)


def test_baseline_single_prompt_is_recorded_and_replayed(tmp_path):
    class Plain:
        name = "plain"

        def single_prompt(self, prompt):
            return "baseline answer for " + prompt

    rec = RecordingReasoner(Plain(), tmp_path / "cassette.jsonl")
    assert rec.single_prompt("q1") == "baseline answer for q1"
    assert ReplayReasoner(tmp_path / "cassette.jsonl").single_prompt("q1") == "baseline answer for q1"
    with pytest.raises(CassetteMiss):
        ReplayReasoner(tmp_path / "cassette.jsonl").single_prompt("q2")
