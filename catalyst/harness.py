"""受控生成路径：一个阶段 = 调模型 → 解析 → schema 校验 → 领域校验 → 不过就把具体错误回给模型重写。

重试上限 max_retries，超限返回结构化失败，不抛半截结果。每次尝试（含失败的）都写进 trace；
只有通过校验的输出才会被入口写进版本快照。每次重试是一个新的单轮请求（原题 + 上次输出 +
错误清单），不改写历史消息。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Callable, Generic, TypeVar

from pydantic import BaseModel, ValidationError

from catalyst.reasoner import Reasoner
from catalyst.store import RunStore

T = TypeVar("T", bound=BaseModel)


@dataclass
class StageResult(Generic[T]):
    stage: str
    ok: bool
    value: T | None = None
    attempts: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)


def _extract_json(text: str) -> dict:
    text = text.strip()
    if m := re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S):
        text = m.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("输出里没有 JSON 对象")
    return json.loads(text[start:end + 1])


def _pydantic_errors(e: ValidationError) -> list[str]:
    return [f"[{'.'.join(map(str, err['loc']))}] {err['msg']}" for err in e.errors()[:20]]


def run_stage(
    stage: str,
    *,
    system: str,
    user: str,
    output_model: type[T],
    reasoner: Reasoner,
    validate: Callable[[T], tuple[list[str], list[str]]] = lambda _: ([], []),
    max_retries: int = 2,
    store: RunStore | None = None,
) -> StageResult[T]:
    """validate 返回 (阻断错误, 非阻断提示)。"""
    schema = output_model.model_json_schema(by_alias=True)
    prompt, last_errors = user, []
    for attempt in range(1, max_retries + 2):
        out = reasoner.complete(stage=stage, system=system, user=prompt, schema=schema)
        errors, warnings, value = [], [], None
        try:
            value = output_model.model_validate(_extract_json(out.text))
        except ValueError as e:  # json 解析失败
            errors = [f"[json] {e}"]
        except ValidationError as e:
            errors = _pydantic_errors(e)
        if value is not None:
            errors, warnings = validate(value)
        if store:
            store.log_attempt(stage=stage, attempt=attempt, ok=not errors, errors=errors,
                              warnings=warnings, raw=out.text, meta=out.meta)
        if not errors:
            return StageResult(stage, True, value, attempt, [], warnings, out.meta)
        last_errors = errors
        prompt = (f"{user}\n\n---\n你上一次的输出没有通过校验。上一次输出：\n{out.text}\n\n"
                  "校验错误（每条前面的方括号是出错对象的 id）：\n" + "\n".join(f"- {e}" for e in errors)
                  + "\n\n只修正这些问题，其余内容保持不变，重新输出完整 JSON。")
    return StageResult(stage, False, None, max_retries + 1, last_errors)
