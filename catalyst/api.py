"""前端用的薄 HTTP 层：只把请求翻译成入口调用，再从 RunStore 读出版本。没有业务逻辑。

  .venv/bin/python -m catalyst.api            # http://localhost:8000
  CATALYST_REPLAY=runs/D1/<ts> ...            # 用录音回放，不调模型（演示 / 无 key 时用）

接口（所有写操作都返回 {ok, errors, version}，前端再 GET 这个版本）：
  POST /api/runs                          {event, target?, packs?}
  GET  /api/runs/{run_id}/versions/{v}    → {graph, proposal, scenario, diff, excerpts}
  POST /api/runs/{run_id}/fork            {base_version, op}
  POST /api/runs/{run_id}/sign            {version, clarified_statement, criteria, deadline,
                                           confirmed_claim_ids, condition_overrides}
"""
from __future__ import annotations

import json
import os
import re
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from catalyst import entrypoints as ep
from catalyst.evidence import EvidenceProvider
from catalyst.reasoner import RecordingReasoner, ReplayReasoner, default_reasoner
from catalyst.store import RunStore

ROOT = Path(__file__).resolve().parent.parent
RUNS = Path(os.environ.get("CATALYST_RUNS_DIR", ROOT / "runs")) / "api"


def _provider(packs: list[str]) -> tuple[EvidenceProvider, list[str], list[str]]:
    from catalyst.__main__ import _provider as cli_provider  # 同一套「真实 pack 优先、合成包兜底」规则

    return cli_provider({"input": {"evidence_packs": packs}}, ROOT / "eval" / "cases", ROOT / "packs")


def _reasoner(store: RunStore):
    if replay := os.environ.get("CATALYST_REPLAY"):
        return ReplayReasoner(Path(replay) / "cassette.jsonl")
    return RecordingReasoner(default_reasoner(), store.cassette)


def _store(run_id: str) -> RunStore:
    if not re.fullmatch(r"[\w.-]+", run_id) or not (RUNS / run_id).is_dir():
        raise KeyError(f"run {run_id} 不存在")
    return RunStore(RUNS / run_id)


def create_run(body: dict) -> dict:
    store = RunStore.new(RUNS, "")
    run_id = store.root.name
    ev, packs, notes = _provider(body.get("packs") or [])
    cfg = ep.Config(packs=packs, run_prefix="r", today=body.get("today") or ep.Config().today)
    (store.root / "case.json").write_text(json.dumps({"case": {"id": run_id, "input": body}, "packs": packs,
                                                      "notes": notes, "today": cfg.today}, ensure_ascii=False))
    reasoner, event, target = _reasoner(store), body["event"], body.get("target")
    disc = None
    candidate = None
    if not target:
        disc = ep.discover(event, reasoner=reasoner, evidence=ev, config=cfg, store=store)
        cands = disc.get("candidates") or []
        if not disc["ok"] or not cands:
            return {"ok": disc["ok"], "errors": disc["errors"], "version": None, "run_id": run_id,
                    "discover": disc, "inspect": None, "notes": notes}
        candidate = next((c for c in cands if c["label"] == "grounded"), cands[0])
    ins = ep.inspect(event, target, candidate=candidate, candidate_id=candidate and candidate["id"],
                     reasoner=reasoner, evidence=ev, config=cfg, store=store)
    version = ins["graph"]["version"] if ins.get("graph") else None
    return {"ok": ins["ok"], "errors": ins["errors"], "version": version, "run_id": run_id,
            "discover": disc, "inspect": ins, "notes": notes}


def fork_run(run_id: str, body: dict) -> dict:
    store = _store(run_id)
    base_v = body["base_version"]
    bundle = store.bundle(base_v)
    meta = json.loads((store.root / "case.json").read_text())
    cfg = ep.Config(packs=meta.get("packs", []), today=meta["today"], run_prefix="r")
    pack = {"pack_id": f"observed:{base_v}", "excerpts": bundle["excerpts"]} if bundle["excerpts"] else None
    res = ep.fork(bundle["graph"], body["op"], reasoner=_reasoner(store), evidence=None, config=cfg, pack=pack,
                  proposal=bundle["proposal"], scenario=bundle["scenario"], store=store)
    return {**res, "version": res["graph"]["version"] if res.get("graph") else None}


def sign_run(run_id: str, body: dict) -> dict:
    store = _store(run_id)
    bundle = store.bundle(body["version"])
    if not bundle["proposal"]:
        return {"ok": False, "errors": [f"[{body['version']}] 这个版本没有提案，不能签字"], "version": None}
    meta = json.loads((store.root / "case.json").read_text())
    return ep.sign(bundle["graph"], bundle["proposal"], clarified_statement=body["clarified_statement"],
                   criteria=body.get("criteria"), deadline=body.get("deadline"),
                   confirmed_claim_ids=body.get("confirmed_claim_ids", []),
                   condition_overrides=body.get("condition_overrides") or {},
                   config=ep.Config(today=meta["today"]), store=store)


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def _route(self, method: str) -> None:
        path = self.path.split("?")[0]
        try:
            if method == "GET" and path == "/api/health":
                return self._send(200, {"ok": True})
            if method == "POST" and path == "/api/runs":
                return self._send(200, create_run(self._body()))
            if m := re.fullmatch(r"/api/runs/([\w.-]+)/versions/([\w.-]+)", path):
                if method == "GET":
                    return self._send(200, _store(m.group(1)).bundle(m.group(2)))
            if m := re.fullmatch(r"/api/runs/([\w.-]+)/(fork|sign)", path):
                if method == "POST":
                    fn = fork_run if m.group(2) == "fork" else sign_run
                    return self._send(200, fn(m.group(1), self._body()))
            return self._send(404, {"ok": False, "errors": [f"没有这个接口：{method} {path}"], "version": None})
        except (KeyError, FileNotFoundError) as e:
            return self._send(404, {"ok": False, "errors": [str(e)], "version": None})
        except Exception as e:  # noqa: BLE001 —— 原样回给前端显示，同时打到服务端日志
            traceback.print_exc()
            return self._send(500, {"ok": False, "errors": [f"{type(e).__name__}: {e}"], "version": None})

    def do_GET(self):  # noqa: N802
        self._route("GET")

    def do_POST(self):  # noqa: N802
        self._route("POST")


def main() -> None:
    port = int(os.environ.get("CATALYST_PORT", "8000"))
    RUNS.mkdir(parents=True, exist_ok=True)
    print(f"Catalyst API on http://localhost:{port}  (runs: {RUNS})")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
