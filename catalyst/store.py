"""Immutable Graph Snapshots + Operation Log，落地成一次运行一个目录：

runs/<case>/<run_id>/
  snapshots/<version>.json    图快照（写入后不可覆盖）
  proposals/<version>.json    该图版本派生的提案
  scenarios/<version>.json    分叉的情景与 assessment
  observations/<version>.json 该版本推理时进入上下文的全部片段
  oplog.jsonl                 每次操作一行：谁做的、输入版本、输出版本、prompt 版本
  trace.jsonl                 每次模型尝试一行：原始输出、校验错误（失败的输出只进这里）
  cassette.jsonl              Reasoner 录音，用于确定性回放
  result.json                 入口返回值（eval 与 UI 读它）
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from catalyst.diff import content_hash, diff as graph_diff


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
            raise SnapshotExists(f"{kind}/{version} 已存在且内容不同：快照不可覆盖")
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2))
        return path

    def put_snapshot(self, graph: dict) -> Path:
        return self._put("snapshots", graph["version"], graph)

    def put_proposal(self, version: str, proposal: dict) -> Path:
        return self._put("proposals", version, proposal)

    def put_scenario(self, scenario: dict) -> Path:
        return self._put("scenarios", scenario["version"], scenario)

    def put_observations(self, version: str, excerpts: list[dict]) -> Path:
        return self._put("observations", version, {"version": version, "excerpts": excerpts})

    def get_snapshot(self, version: str) -> dict:
        return json.loads((self.root / "snapshots" / f"{version}.json").read_text())

    def get_proposal(self, version: str) -> dict | None:
        path = self.root / "proposals" / f"{version}.json"
        return json.loads(path.read_text()) if path.exists() else None

    def bundle(self, version: str) -> dict:
        """一个版本的完整视图：GET /versions/{v} 与 promote 的 fixture 用同一个形状。"""
        graph = self.get_snapshot(version)
        sc = self.root / "scenarios" / f"{version}.json"
        obs = self.root / "observations" / f"{version}.json"
        parent = graph.get("parent_version")
        has_parent = parent and (self.root / "snapshots" / f"{parent}.json").exists()
        return {"graph": graph, "proposal": self.get_proposal(version),
                "scenario": json.loads(sc.read_text()) if sc.exists() else None,
                "diff": graph_diff(self.get_snapshot(parent), graph) if has_parent else None,
                "excerpts": json.loads(obs.read_text())["excerpts"] if obs.exists() else []}

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
