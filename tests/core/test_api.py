"""HTTP 层：脚本化 Reasoner，走一遍 创建 → 读版本 → 批准（sign）→ 分叉，以及一次真实的 HTTP 往返。"""
import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from catalyst import api
from tests.core.test_harness import PACK, Scripted, _good

FORK_OUT = {"node_updates": [{"id": "h.transits", "statement": "过境恢复推迟到 12 月"}], "edge_updates": [],
            "condition_updates": [], "next_checks": ["12 月 PortWatch 日过境量"],
            "assessment": [{"claim_id": "h.transits", "status": "challenged", "reason": "时间推迟"},
                           {"claim_id": "h.brent", "status": "challenged", "reason": "上游推迟"}]}


@pytest.fixture
def scripted(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "RUNS", tmp_path / "api")
    r = Scripted([_good(), FORK_OUT])
    monkeypatch.setattr(api, "_reasoner", lambda store: r)

    def provider(packs):
        from catalyst.evidence import EvidenceProvider
        ev = EvidenceProvider("/nonexistent")
        ev.register(PACK)
        return ev, ["hz"], []
    monkeypatch.setattr(api, "_provider", provider)
    return r


def test_create_sign_fork_flow(scripted):
    created = api.create_run({"event": "霍尔木兹海峡下周重开", "target": "BZ", "today": "2026-10-18"})
    assert created["ok"] and created["version"] == "r-v1"
    run = created["run_id"]
    b1 = api._store(run).bundle("r-v1")
    assert b1["proposals"][0]["gate"] == "WAIT" and [x["excerpt_id"] for x in b1["excerpts"]] == ["hz-1", "hz-3"]

    signed = api.sign_run(run, {"version": "r-v1", "terminal_id": "h.brent", "clarified_statement": "11 月 30 日前日过境 ≥ 20 艘",
                                "criteria": "PortWatch 日过境", "deadline": "2026-11-30",
                                "confirmed_claim_ids": ["h.transits"],
                                "condition_overrides": {"cond.transits": {"threshold": 20, "deadline": "2026-11-20"}}})
    assert signed["ok"], signed["errors"]
    b2 = api._store(run).bundle(signed["version"])
    cond = b2["graph"]["conditions"][0]
    assert cond["threshold"] == 20 and cond["observation_window"]["end"] == "2026-11-20"
    assert b2["proposals"][0]["user_judgment"]["confirmed"] is True
    assert b2["diff"]["conditions_changed"] == ["cond.transits"] and b2["excerpts"]

    op = {"kind": "change_assumption", "target": "h.transits", "value": "推迟到 12 月"}
    forked = api.fork_run(run, {"base_version": signed["version"], "op": op})
    assert forked["ok"], forked["errors"]
    b3 = api._store(run).bundle(forked["version"])
    assert b3["scenario"]["base_version"] == signed["version"]
    # 4.3：改的是 h.transits，写范围 {h.transits, h.brent} 含这份计划的 terminal 和进场条件 → 批准撤销、要重新批准；
    # 写范围内的已确认前提被剔除（方案 B 之前这里断言「签字不会在分叉时丢失」，现在反过来）
    p3 = b3["proposals"][0]
    assert p3["user_judgment"]["confirmed"] is False and p3["user_judgment"]["confirmed_claim_ids"] == []
    assert p3["approval_reset"] is True and p3["rival_changed"] is False
    assert b3["graph"]["conditions"][0]["threshold"] == 20
    assert b3["proposals"][0]["scenario_ref"]["next_checks"] == ["12 月 PortWatch 日过境量"]


def test_sign_rejects_bad_overrides(scripted):
    run = api.create_run({"event": "x", "target": "BZ", "today": "2026-10-18"})["run_id"]
    res = api.sign_run(run, {"version": "r-v1", "terminal_id": "h.brent", "clarified_statement": "s", "confirmed_claim_ids": ["nope"],
                             "condition_overrides": {"cond.transits": {"rule": "改规则"}}})
    assert not res["ok"] and any("nope" in e for e in res["errors"]) and any("rule" in e for e in res["errors"])


def test_http_roundtrip(scripted):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        req = urllib.request.Request(base + "/api/runs", method="POST",
                                     data=json.dumps({"event": "x", "target": "BZ", "today": "2026-10-18"}).encode())
        created = json.loads(urllib.request.urlopen(req).read())
        got = json.loads(urllib.request.urlopen(f"{base}/api/runs/{created['run_id']}/versions/r-v1").read())
        assert got["graph"]["version"] == "r-v1" and set(got) == {"graph", "proposals", "branches", "scenario", "diff", "excerpts"}
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(f"{base}/api/runs/nope/versions/r-v1")
        assert e.value.code == 404
    finally:
        srv.shutdown()
