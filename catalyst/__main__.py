"""Harness CLI：用题目里的案例跑真实流程，录下来，之后确定性回放，再把录制结果提升成共享 fixture。

  python -m catalyst run D1 --live                 # 实时调用模型，录音 + 快照落到 runs/D1/<时间戳>/
  python -m catalyst run D1 --replay runs/D1/<ts>  # 用录音回放：零成本、确定性，prompt 变了会报错
  python -m catalyst run C3 --live --base runs/C1/<ts>   # 在录制的 C1 图上分叉
  python -m catalyst promote runs/D1/<ts> d1       # 生成 fixtures/d1.json：UI 与测试共用这一份
  python -m catalyst show runs/D1/<ts>             # 打印摘要

案例文件（eval/cases/*.json，eval 线维护）是唯一的案例来源；fixture 不再手写，而是从录制结果提升。
期望（哪些 claim 应受挑战、gate 应是什么）仍由人写在案例文件里——期望不能来自模型自己的输出。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
from pathlib import Path

from catalyst import entrypoints as ep
from catalyst.evidence import EvidenceProvider
from catalyst.reasoner import RecordingReasoner, ReplayReasoner, default_reasoner
from catalyst.store import RunStore

ROOT = Path(__file__).resolve().parent.parent


def _load_case(ref: str, cases_dir: Path) -> dict:
    path = Path(ref) if ref.endswith(".json") else next(
        (p for p in [cases_dir / f"{ref}.json", cases_dir / "causalt5k" / f"{ref}.json"] if p.exists()), None)
    if path is None or not path.exists():
        sys.exit(f"找不到案例 {ref}（在 {cases_dir} 下）")
    return json.loads(path.read_text())


def _fixture_packs(fixtures_dir: Path) -> dict[str, tuple[str, dict]]:
    """eval/fixtures 下所有合成资料包：顶层就是 pack 的文件，或带 evidence_pack 字段的 golden 文件。"""
    found: dict[str, tuple[str, dict]] = {}
    for f in sorted(fixtures_dir.glob("*.json")) if fixtures_dir.exists() else []:
        data = json.loads(f.read_text())
        for pack in (data, data.get("evidence_pack")):
            if isinstance(pack, dict) and "pack_id" in pack and "excerpts" in pack:
                found.setdefault(pack["pack_id"], (f.name, pack))
    return found


def _provider(case: dict, cases_dir: Path, packs_dir: Path) -> tuple[EvidenceProvider, list[str], list[str]]:
    """真实 pack 优先；还没交付时退回 eval fixture 里的合成资料包，并明确告警。"""
    ev, notes, packs = EvidenceProvider(packs_dir), [], []
    synthetic = _fixture_packs(cases_dir.parent / "fixtures")
    for pid in case.get("input", {}).get("evidence_packs", []):
        if (packs_dir / f"{pid}.json").exists():
            packs.append(pid)
        elif pid in synthetic:
            name, pack = synthetic[pid]
            ev.register(pack)
            packs.append(pid)
            notes.append(f"资料包 {pid} 还没交付，用 {name} 里的合成占位片段代替（只验证流程，不验证推理）")
        else:
            notes.append(f"资料包 {pid} 不存在，本轮不带它运行")
    return ev, packs, notes


def _summary(res: dict) -> list[str]:
    lines = [f"ok={res.get('ok')} attempts={res.get('attempts')}"]
    if res.get("errors"):
        lines += ["errors:"] + [f"  - {e}" for e in res["errors"]]
    if res.get("warnings"):
        lines += ["warnings:"] + [f"  - {w}" for w in res["warnings"]]
    if res.get("judgment"):
        lines.append(f"judgment: {res['judgment']['label']} — {res['judgment']['rationale'][:160]}")
    if "candidates" in res:
        lines.append(f"abstained={res.get('abstained')} candidates=" + ", ".join(
            f"{c['id']}[{c['label']}]" for c in res["candidates"]))
    if res.get("no_chain"):
        lines.append(f"no_chain: {res.get('no_chain_reason')}")
    if g := res.get("graph"):
        mo = sum(e["model_only"] for e in g["edges"])
        lines.append(f"graph {g['version']}: {len(g['nodes'])} nodes, {len(g['edges'])} edges ({mo} model_only), "
                     f"{len(g['conditions'])} conditions")
    if p := res.get("proposal"):
        nulls = [c["id"] for c in p["entry_conditions"] + p["exit_conditions"] if c["kind"] == "numeric" and c["threshold"] is None]
        lines.append(f"proposal: {p['direction']['side']} {p['direction']['instrument']} gate={p['gate']} "
                     f"status={p['status']} support={p['support_status']} null_thresholds={nulls} "
                     f"confirm={p['user_judgment']['requires_user_confirmation']}")
    if d := res.get("diff"):
        lines.append("diff: " + json.dumps({k: v for k, v in d.items() if v}, ensure_ascii=False))
    if s := res.get("scenario"):
        lines.append("challenged: " + str(sorted(k for k, v in s["assessment"].items() if v == "challenged")))
    return lines


def cmd_run(a) -> None:
    cases_dir = Path(a.cases_dir)
    case = _load_case(a.case, cases_dir)
    cid, inp = case["id"], case.get("input", {})
    recorded_today = None
    if a.replay:
        rec = Path(a.replay)
        recorded_today = json.loads((rec / "case.json").read_text()).get("today")  # 回放必须用录制当天的日期
        store = RunStore(rec.parent / f"{rec.name}.replay-{_dt.datetime.now():%H%M%S}")
        reasoner = ReplayReasoner(rec / "cassette.jsonl")
    else:
        store = RunStore.new(a.runs_dir, cid)
        reasoner = RecordingReasoner(default_reasoner(), store.cassette)
    ev, packs, notes = _provider(case, cases_dir, Path(a.packs_dir))
    cfg = ep.Config(packs=packs, today=a.today or recorded_today or inp.get("today") or ep.Config().today,
                    run_prefix=cid.lower())
    (store.root / "case.json").write_text(json.dumps({"case": case, "packs": packs, "notes": notes,
                                                      "today": cfg.today}, ensure_ascii=False, indent=2))
    for n in notes:
        print(f"! {n}")

    if case.get("type") == "causalt5k":
        res = ep.inspect(inp["event"], inp.get("target"), material=inp["material"], judgment_only=True,
                         reasoner=reasoner, evidence=ev, config=cfg, store=store)
    elif case.get("entry") == "fork":
        res = _run_forks(case, cases_dir, a, reasoner, ev, cfg, store)
    elif case.get("entry") == "discover":
        res = ep.discover(inp["event"], reasoner=reasoner, evidence=ev, config=cfg, store=store)
        print("\n".join(_summary(res)))
        cands = res.get("candidates") or []
        if case.get("then") == "inspect" and cands:
            pick = next((c for c in cands if c["label"] == "grounded"), cands[0])
            print(f"→ inspect 候选 {pick['id']}")
            res = ep.inspect(inp["event"], None, candidate_id=pick["id"], candidate=pick, reasoner=reasoner,
                             evidence=ev, config=cfg, store=store)
        else:
            res = None
    else:
        res = ep.inspect(inp["event"], inp.get("target"), reasoner=reasoner, evidence=ev, config=cfg, store=store)
    if res is not None:
        print("\n".join(_summary(res)))
    print(f"\nrun: {store.root}")


def _run_forks(case, cases_dir, a, reasoner, ev, cfg, store):
    """C3：在基线图上依次执行案例列出的每个分叉。基线默认用案例指定的 golden 图（Expected Impact
    只能对 golden 图自动比对）；--base 给出录制目录时改用录制的图。每个分叉都从同一基线出发。"""
    fx_dir = cases_dir.parent / "fixtures"
    proposal, pack = None, None
    if a.base:
        rec = RunStore(a.base)
        version = rec.latest_version()
        base_graph, proposal = rec.get_snapshot(version), rec.get_proposal(version)
        obs = rec.root / "observations" / f"{version}.json"
        if obs.exists():
            pack = {"pack_id": f"recorded:{version}", "excerpts": json.loads(obs.read_text())["excerpts"]}
    else:
        base_graph = json.loads((fx_dir / case["input"]["base_graph_fixture"]).read_text())
        cited = {ev_["excerpt_id"] for e in base_graph["edges"] for ev_ in e.get("evidence", [])}
        pack = next((p for _, p in _fixture_packs(fx_dir).values()
                     if cited & {x["excerpt_id"] for x in p["excerpts"]}), None)
    res = None
    for name in case["input"]["forks"]:
        fx = json.loads((fx_dir / name).read_text())
        print(f"→ fork {name}: {fx['op']['kind']} {fx['op'].get('target') or fx['op'].get('impacts')}")
        res = ep.fork(base_graph, fx["op"], reasoner=reasoner, evidence=ev, config=cfg, pack=pack,
                      proposal=proposal, store=store)
        print("\n".join(_summary(res)))
        if res.get("scope") and "expected_scope" in fx:
            ok = all(set(res["scope"][k]) == set(fx["expected_scope"][k]) for k in ("nodes", "edges"))
            print(f"  write_scope_matches_golden: {'PASS' if ok else 'FAIL'}")
        if res.get("scenario") and "expected_challenged" in fx and not a.base:
            got = {k for k, v in res["scenario"]["assessment"].items() if v == "challenged"}
            want = set(fx["expected_challenged"])
            print(f"  challenged_matches_golden: {'PASS' if got == want else 'FAIL'}"
                  + ("" if got == want else f"（多 {sorted(got - want)}，少 {sorted(want - got)}）"))
    return None


def cmd_promote(a) -> None:
    store = RunStore(a.run)
    version = store.latest_version()
    if not version:
        sys.exit("这次运行没有产出图快照，不能提升成 fixture")
    case = json.loads((store.root / "case.json").read_text())
    fixture = {"_source": {"run": str(store.root), "case": case["case"]["id"], "packs": case["packs"],
                           "notes": case["notes"], "cassette": "cassette.jsonl"},
               "versions": {}}
    for snap in sorted((store.root / "snapshots").glob("*.json")):
        v = snap.stem
        fixture["versions"][v] = {"graph": json.loads(snap.read_text()), "proposal": store.get_proposal(v)}
        if (sc := store.root / "scenarios" / f"{v}.json").exists():
            fixture["versions"][v]["scenario"] = json.loads(sc.read_text())
    fixture["latest"] = version
    out = Path(a.fixtures_dir) / f"{a.name}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(fixture, ensure_ascii=False, indent=2))
    print(f"fixture: {out}（版本 {list(fixture['versions'])}）")


def cmd_show(a) -> None:
    root = Path(a.run)
    for f in sorted(root.glob("*.result.json")):
        print(f"== {f.name}")
        print("\n".join(_summary(json.loads(f.read_text()))))


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="python -m catalyst")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("case")
    mode = r.add_mutually_exclusive_group(required=True)
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--replay", metavar="RUN_DIR")
    r.add_argument("--base", metavar="RUN_DIR")
    r.add_argument("--today")
    r.add_argument("--cases-dir", default=os.environ.get("CATALYST_CASES_DIR", str(ROOT / "eval" / "cases")))
    r.add_argument("--packs-dir", default=str(ROOT / "packs"))
    r.add_argument("--runs-dir", default=str(ROOT / "runs"))
    r.set_defaults(fn=cmd_run)
    pr = sub.add_parser("promote")
    pr.add_argument("run")
    pr.add_argument("name")
    pr.add_argument("--fixtures-dir", default=str(ROOT / "fixtures"))
    pr.set_defaults(fn=cmd_promote)
    s = sub.add_parser("show")
    s.add_argument("run")
    s.set_defaults(fn=cmd_show)
    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
