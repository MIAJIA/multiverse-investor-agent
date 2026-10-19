"""测试侧唯一 import catalyst 的地方。

核心落地或字段变化时，只改这个文件。每个函数在调用时才 import 对应的核心子模块，
子模块不存在就 pytest.importorskip 干净跳过——核心可以分批落地。
接口提议见 eval/INTERFACE.md。
"""
from __future__ import annotations

import copy
import dataclasses
import datetime as _dt
import enum
from typing import Any

import pytest


def _core(module: str):
    return pytest.importorskip(module, reason=f"{module} 尚未实现（eval/INTERFACE.md）")


def to_plain(obj: Any) -> Any:
    """把核心返回的对象归一成 dict / list / str。"""
    if isinstance(obj, enum.Enum):
        return obj.value
    if hasattr(obj, "model_dump"):
        return to_plain(obj.model_dump())
    if hasattr(obj, "to_dict"):
        return to_plain(obj.to_dict())
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return to_plain(dataclasses.asdict(obj))
    if isinstance(obj, dict):
        return {k: to_plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set, frozenset)):
        return [to_plain(v) for v in obj]
    return obj


def _schema_parse(name: str, data: dict) -> Any:
    """核心若提供 catalyst.schema.parse_<name>，用它把 dict 转成核心对象；否则直接传 dict。"""
    try:
        import catalyst.schema as schema  # noqa: WPS433
    except ImportError:
        return copy.deepcopy(data)
    parser = getattr(schema, f"parse_{name}", None)
    return parser(copy.deepcopy(data)) if parser else copy.deepcopy(data)


def _errors(result: Any) -> list[str]:
    return [str(e) for e in (result or [])]


def canonical_graph(graph: Any) -> dict:
    """规范形式：parse_graph(d).dump()，字段齐全、含默认值（docs/core-design.md「规范形式」）。

    E3 哈希比对前两边都要过这一步，否则 fixture 省略的默认字段（model_only: false、rebuttal: null）
    会被误判成改动。核心没提供 parse_graph 时原样返回。
    """
    try:
        import catalyst.schema as schema  # noqa: WPS433
    except ImportError:
        return to_plain(graph)
    parser = getattr(schema, "parse_graph", None)
    if parser is None:
        return to_plain(graph)
    g = parser(copy.deepcopy(graph) if isinstance(graph, dict) else graph)
    return to_plain(g.dump() if hasattr(g, "dump") else g)


# ---- gate ---------------------------------------------------------------

def evaluate_entry(conditions: list[dict]) -> str:
    gate = _core("catalyst.gate")
    result = gate.evaluate_entry([_schema_parse("condition", c) for c in conditions])
    return str(to_plain(result)).upper()


# ---- conditions ---------------------------------------------------------

def evaluate_condition(condition: dict, observations: list[dict], now: str) -> str:
    conditions = _core("catalyst.conditions")
    result = conditions.evaluate(
        _schema_parse("condition", condition),
        copy.deepcopy(observations),
        _dt.date.fromisoformat(now),
    )
    return str(to_plain(result)).lower()


def validate_condition(condition: dict) -> list[str]:
    validator = _core("catalyst.validator")
    return _errors(validator.validate_condition(_schema_parse("condition", condition)))


# ---- references ---------------------------------------------------------

def validate_references(graph: dict, evidence_pack: dict) -> list[str]:
    validator = _core("catalyst.validator")
    return _errors(validator.validate_references(_schema_parse("graph", graph), copy.deepcopy(evidence_pack)))


# ---- fork / diff --------------------------------------------------------

def scope_violation() -> type:
    return _core("catalyst.fork").ScopeViolation


def compute_write_scope(graph: dict, op: dict) -> tuple[set, set, Any]:
    """返回 (node_ids, edge_ids, raw_scope)；raw_scope 原样回传给 apply_patch。"""
    fork = _core("catalyst.fork")
    raw = fork.compute_write_scope(_schema_parse("graph", graph), copy.deepcopy(op))
    plain = to_plain(raw)
    if isinstance(plain, dict):
        nodes, edges = plain.get("nodes", []), plain.get("edges", [])
    else:
        nodes, edges = plain[0], plain[1]
    return set(nodes), set(edges), raw


def apply_patch(graph: Any, patch: dict, raw_scope: Any) -> dict:
    """graph 可以是 dict（会先 parse）或核心对象（原样传入，用来检查是否被原地修改）。"""
    fork = _core("catalyst.fork")
    core_graph = _schema_parse("graph", graph) if isinstance(graph, dict) else graph
    return to_plain(fork.apply_patch(core_graph, copy.deepcopy(patch), raw_scope))


def diff(g1: dict, g2: dict) -> dict[str, set]:
    diff_mod = _core("catalyst.diff")
    plain = to_plain(diff_mod.diff(_schema_parse("graph", g1), _schema_parse("graph", g2)))
    keys = ["nodes_changed", "edges_changed", "conditions_changed",
            "nodes_added", "edges_added", "nodes_removed", "edges_removed"]
    return {k: set(plain.get(k, []) or []) for k in keys}


# ---- 案例入口（runner 契约测试用）---------------------------------------

def core_entrypoints():
    return _core("catalyst.entrypoints")


def core_evidence_provider(packs_dir=None):
    """packs_dir 指向空目录时，所有 pack 都走 runner 的合成包回退（register）。"""
    evidence = _core("catalyst.evidence")
    return evidence.EvidenceProvider(packs_dir) if packs_dir is not None else evidence.default_provider()
