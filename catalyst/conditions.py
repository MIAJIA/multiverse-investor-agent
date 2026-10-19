"""条件判定：met / not_met / unknown，规则写成代码。

evaluation_status 回答「这个条件是否成立」。数据缺失、阈值未知、窗口未结束都给 unknown，
不把「还没看到」当成「没发生」。

观测（observation）的形状：
    {"source": str, "coverage": {"start": date, "end": date},
     "records": [{"date": date, "value": number | None, "excerpt_id": str | None}]}
source 与条件的 series 或 source 匹配；coverage 是来源实际覆盖到的区间。
"""
from __future__ import annotations

import datetime as _dt
import operator

from catalyst.schema import Condition, EvaluationStatus, parse_condition

_OPS = {">=": operator.ge, "<=": operator.le, ">": operator.gt, "<": operator.lt, "==": operator.eq}


def _d(v) -> _dt.date:
    return v if isinstance(v, _dt.date) else _dt.date.fromisoformat(str(v))


def _hit(c: Condition, record: dict) -> bool:
    if c.kind != "numeric":
        return True  # 文件 / 事件型：窗口内出现一条经来源记录的事件即算观测到
    value = record.get("value")
    return value is not None and _OPS[c.comparator](float(value), c.threshold)


def evaluate(condition: Condition | dict, observations: list[dict], now: _dt.date) -> EvaluationStatus:
    """日期不合法、观测格式不对时给 unknown，不抛异常：判定在校验之前也可能被调用。"""
    try:
        return _evaluate(parse_condition(condition), observations, now)
    except (ValueError, KeyError, TypeError):
        return "unknown"


def _evaluate(c: Condition, observations: list[dict], now: _dt.date) -> EvaluationStatus:
    if c.kind == "numeric" and (c.threshold is None or c.comparator is None):
        return "unknown"
    if "scenario:" in (c.anchor + c.observation_window.start + c.observation_window.end):
        return "unknown"  # 情景起点未经用户确认，不能判定
    key = {c.series, c.source} - {None}
    obs = [o for o in observations if o.get("source") in key]
    start, end = _d(c.observation_window.start), _d(c.observation_window.end)

    in_window = [r for o in obs for r in o.get("records", []) if start <= _d(r["date"]) <= end and _d(r["date"]) <= now]
    hit = any(_hit(c, r) for r in in_window)
    covered = any(_d(o["coverage"]["start"]) <= start and _d(o["coverage"]["end"]) >= end for o in obs)
    closed = now > end

    if c.predicate == "observed_by":
        if hit:
            return "met"
        return "not_met" if closed and covered else "unknown"

    if c.predicate == "not_observed_by":
        # 「到期未发生」是合法条件：窗口内看到了 → 不成立；窗口结束且来源覆盖整个窗口仍没看到 → 成立
        if hit:
            return "not_met"
        return "met" if closed and covered else "unknown"

    # at_deadline：只看截止日当天或之前最近的一条记录（不受观测窗口结束早于截止日的影响）
    deadline = _d(c.deadline)
    if now < deadline or not any(_d(o["coverage"]["end"]) >= deadline for o in obs):
        return "unknown"
    upto = [r for o in obs for r in o.get("records", []) if start <= _d(r["date"]) <= deadline]
    last = max(upto, key=lambda r: _d(r["date"]), default=None)
    if last is None or (c.kind == "numeric" and last.get("value") is None):
        return "unknown"
    return "met" if _hit(c, last) else "not_met"
