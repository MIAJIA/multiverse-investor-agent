"""Layer W must run online like the CLI: round-1 retrieval first, then inspect gets the research loop and a store."""
import pytest

pytest.importorskip("catalyst")

from eval import runner  # noqa: E402


def test_online_case_passes_research_and_store_to_inspect(monkeypatch, tmp_path):
    import catalyst.__main__ as cli

    calls = {}
    monkeypatch.setattr(cli, "attach_web", lambda *a, **k: calls.setdefault("attach", k["replay_dir"]) or "WEB")
    monkeypatch.setattr(cli, "research_for", lambda *a, **k: "RESEARCH")
    monkeypatch.setattr(cli, "web_summary", lambda web, research: {"message": "ok"})
    runner.WEB_RUNS.update(dir=tmp_path, replay=False)

    class EP:
        def inspect(self, event, target=None, **kw):
            calls["inspect_kw"] = kw
            return {"ok": True, "graph": None, "no_chain": True, "proposals": [], "errors": [], "observations": []}

    case = {"id": "W9", "type": "custom", "entry": "inspect", "input": {"event": "e", "target": "TLT"},
            "expected": {}, "evals": [], "auto_checks": [], "human_review": []}
    monkeypatch.setattr(runner, "prepare_packs", lambda case, ev, src: ([], []))
    res = runner.run_case(case, "pipeline", reasoner=object(), evidence=object(), entrypoints=EP(), online=True)
    kw = calls["inspect_kw"]
    assert kw["research"] == "RESEARCH" and kw["store"] is not None and kw["config"]["online"] is True
    assert res.get("web") == {"message": "ok"} and calls["attach"] is None   # recording, not replay
