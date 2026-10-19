"""条件时间语义与 Condition 校验（依赖核心）。设计规则见 docs/eval/test-plan.md A2。"""
import copy

import pytest

pytest.importorskip("catalyst", reason="核心包 catalyst 尚未落地")

from eval.loader import load_fixture  # noqa: E402
from tests import _adapter  # noqa: E402

CASES = load_fixture("condition_cases.json")


def _condition(overrides: dict, case_id: str) -> dict:
    c = copy.deepcopy(CASES["base_condition"])
    c.update(copy.deepcopy(overrides))
    c["id"] = f"cond.{case_id}"
    return c


@pytest.mark.parametrize("case", CASES["evaluate"], ids=[c["id"] for c in CASES["evaluate"]])
def test_evaluate(case):
    cond = _condition(case["condition_overrides"], case["id"])
    result = _adapter.evaluate_condition(cond, case["observations"], case["now"])
    assert result == case["expected"], case["why"]


@pytest.mark.parametrize("case", CASES["validate"], ids=[c["id"] for c in CASES["validate"]])
def test_validate_condition(case):
    cond = _condition(case["condition_overrides"], case["id"])
    errors = _adapter.validate_condition(cond)
    if case["expect_error"]:
        assert errors, case["why"]
        assert any(cond["id"] in e for e in errors), f"错误文本应包含 {cond['id']}：{errors}"
    else:
        assert errors == [], f"{case['why']}：{errors}"


def test_d1_null_threshold_is_valid():
    """D1 的过境阈值为 null 但带说明：校验通过。"""
    d1 = load_fixture("d1_hormuz.json")
    for cond in d1["entry_conditions"]:
        assert _adapter.validate_condition(cond) == [], cond["id"]


def test_d1_gate_is_wait():
    d1 = load_fixture("d1_hormuz.json")
    assert _adapter.evaluate_entry(d1["entry_conditions"]) == d1["expected"]["gate"]
