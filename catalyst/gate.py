"""进场 / 退出判定。只看 evaluation_status；verifiable 不等于 met。"""
from __future__ import annotations

from typing import Literal

from catalyst.schema import Condition, ExitLogic, Gate, parse_condition


def evaluate_entry(conditions: list[Condition | dict]) -> Gate:
    """默认 AND：任一 not_met → BLOCKED；否则任一 unknown → WAIT；空集 → WAIT；全 met → READY_FOR_REVIEW。
    全部满足也只到 Ready for Review，不存在 Ready to Execute。"""
    statuses = [parse_condition(c).evaluation_status for c in conditions]
    if not statuses:
        return "WAIT"
    if "not_met" in statuses:
        return "BLOCKED"
    if "unknown" in statuses:
        return "WAIT"
    return "READY_FOR_REVIEW"


def evaluate_exit(conditions: list[Condition | dict], logic: ExitLogic) -> Literal["TRIGGERED", "NOT_TRIGGERED", "UNKNOWN"]:
    """退出条件必须显式声明 ANY / ALL，不默认「任一」。"""
    statuses = [parse_condition(c).evaluation_status for c in conditions]
    if not statuses:
        return "UNKNOWN"
    if logic == "ANY":
        if "met" in statuses:
            return "TRIGGERED"
        return "NOT_TRIGGERED" if all(s == "not_met" for s in statuses) else "UNKNOWN"
    if all(s == "met" for s in statuses):
        return "TRIGGERED"
    return "NOT_TRIGGERED" if "not_met" in statuses else "UNKNOWN"
