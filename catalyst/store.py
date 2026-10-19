"""Immutable Graph Snapshots + Operation Log，落地成一次运行一个目录：

runs/<case>/<run_id>/
  snapshots/<version>.json    图快照（写入后不可覆盖）
  proposals/<version>.json    plans derived for the version: a list, one per terminal (pre-plan-B files: a single dict)
  scenarios/<version>.json    分叉的情景与 assessment
  observations/<version>.json 该版本推理时进入上下文的全部片段; synthetic = a synthetic placeholder pack was used (missing → false)
  oplog.jsonl                 每次操作一行：谁做的、输入版本、输出版本、prompt 版本
  trace.jsonl                 每次模型尝试一行：原始输出、校验错误（失败的输出只进这里）
  cassette.jsonl              Reasoner 录音，用于确定性回放
  result.json                 入口返回值（eval 与 UI 读它）
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from catalyst.branches import dump_views
from catalyst.diff import content_hash, diff as graph_diff
from catalyst.schema import parse_proposals


class SnapshotExists(Exception):
    pass


class RunStore:
    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    @classmethod
    def new(cls, base: Path | str, case_id: str) -> "RunStore":
        stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        root, n = Path(base) / case_id / stamp, 1
        while root.exists():  # 同一秒启动的两次运行不能落进同一个目录
            n += 1
            root = Path(base) / case_id / f"{stamp}-{n}"
        return cls(root)

    # ---- 不可变写入 ----
    def _put(self, kind: str, version: str, obj: dict) -> Path:
        path = self.root / kind / f"{version}.json"
        path.parent.mkdir(exist_ok=True)
        if path.exists():
            if content_hash(json.loads(path.read_text())) == content_hash(obj):
                return path
            raise SnapshotExists(f"{kind}/{version} already exists with different content: snapshots cannot be overwritten")
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2))
        return path

    def put_snapshot(self, graph: dict) -> Path:
        return self._put("snapshots", graph["version"], graph)

    def put_proposals(self, version: str, proposals: list[dict]) -> Path:
        return self._put("proposals", version, list(proposals))

    def put_scenario(self, scenario: dict) -> Path:
        return self._put("scenarios", scenario["version"], scenario)

    def put_observations(self, version: str, excerpts: list[dict], *, synthetic: bool = False) -> Path:
        return self._put("observations", version, {"version": version, "excerpts": excerpts, "synthetic": synthetic})

    def get_snapshot(self, version: str) -> dict:
        return json.loads((self.root / "snapshots" / f"{version}.json").read_text())

    def get_proposals(self, version: str) -> list[dict]:
        """All plans of the version in canonical form. A legacy single-dict file becomes a one-item list
        (terminal_id is inferred from the instrument, see schema.parse_proposals)."""
        path = self.root / "proposals" / f"{version}.json"
        if not path.exists():
            return []
        return [p.dump() for p in parse_proposals(json.loads(path.read_text()), self.get_snapshot(version))]

    def get_observations(self, version: str) -> dict:
        """{version, excerpts, synthetic}; empty excerpts when there is no file, synthetic=false when the field is missing."""
        path = self.root / "observations" / f"{version}.json"
        data = json.loads(path.read_text()) if path.exists() else {"version": version, "excerpts": []}
        return {**data, "synthetic": bool(data.get("synthetic", False))}

    def bundle(self, version: str) -> dict:
        """The full view of a version (schema.VersionBundle), shared by GET /versions/{v} and promote."""
        graph = self.get_snapshot(version)
        sc = self.root / "scenarios" / f"{version}.json"
        obs = self.get_observations(version)
        scenario = json.loads(sc.read_text()) if sc.exists() else None
        parent = graph.get("parent_version")
        has_parent = parent and (self.root / "snapshots" / f"{parent}.json").exists()
        synthetic = {x["excerpt_id"] for x in obs["excerpts"]} if obs["synthetic"] else set()
        return {"graph": graph, "proposals": self.get_proposals(version),
                **dump_views(graph, scenario, synthetic_excerpt_ids=synthetic),
                "scenario": scenario,
                "diff": graph_diff(self.get_snapshot(parent), graph) if has_parent else None,
                "excerpts": obs["excerpts"]}

    def latest_version(self) -> str | None:
        ops = self.oplog()
        return next((o["output_version"] for o in reversed(ops) if o.get("output_version")), None)

    # ---- 追加日志 ----
    def _append(self, name: str, entry: dict) -> None:
        entry = {"ts": _dt.datetime.now().isoformat(timespec="seconds"), **entry}
        with (self.root / name).open("a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def log_op(self, **entry) -> None:
        self._append("oplog.jsonl", entry)

    def log_attempt(self, **entry) -> None:
        self._append("trace.jsonl", entry)

    def oplog(self) -> list[dict]:
        path = self.root / "oplog.jsonl"
        return [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []

    def put_result(self, result: dict) -> Path:
        path = self.root / "result.json"
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        return path

    @property
    def cassette(self) -> Path:
        return self.root / "cassette.jsonl"
