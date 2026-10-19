"""进场条件 AND 真值表（依赖核心）。设计规则见 docs/eval/test-plan.md A1。"""
import copy

import pytest

pytest.importorskip("catalyst", reason="核心包 catalyst 尚未落地")

from eval.loader import load_fixture  # noqa: E402
from tests import _adapter  # noqa: E402

TABLE = load_fixture("gate_truth_table.json")
BASE = load_fixture("condition_cases.json")["base_condition"]


def _full(minimal: dict) -> dict:
    c = copy.deepcopy(BASE)
    c.update(minimal)
    c["id"] = f"cond.gate.{minimal['id']}"
    return c


@pytest.mark.parametrize("row", TABLE["rows"], ids=[r["id"] for r in TABLE["rows"]])
def test_entry_truth_table(row):
    result = _adapter.evaluate_entry([_full(c) for c in row["conditions"]])
    assert result in TABLE["allowed_results"], f"不存在 Ready to Execute 一类的结果：{result}"
    assert result == row["expected"], row["why"]


def test_verifiable_is_not_met():
    """verifiable ≠ met：可核验但未判定的条件不能让提案通过。"""
    conditions = [_full({"id": "a", "verification_status": "verifiable", "evaluation_status": "unknown"})]
    assert _adapter.evaluate_entry(conditions) == "WAIT"
