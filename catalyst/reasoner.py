"""Reasoner 边界：谁来推理。核心只依赖 complete()，不关心背后是实时模型还是录音。

- AnthropicReasoner：实时调用 Claude，结构化输出（json_schema）。
- RecordingReasoner：包一层，把每次请求与原始输出写进 cassette.jsonl。
- ReplayReasoner：按请求哈希回放 cassette，确定性、零成本。prompt、资料包或 schema 一变，
  哈希就对不上，回放会明确报错，而不是悄悄返回旧答案。
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

DEFAULT_MODEL = os.environ.get("CATALYST_MODEL", "claude-opus-5-5")
DEFAULT_EFFORT = os.environ.get("CATALYST_EFFORT", "high")


def client_timeout():
    """Read timeout for API calls. The SDK default (10 minutes) lets a silently dropped stream hang a run for ten
    minutes before retrying; 5 minutes (CATALYST_TIMEOUT, seconds) still covers long thinking."""
    import anthropic  # the SDK re-exports its HTTP client's Timeout (httpx2 in SDK 1.x)

    read = float(os.environ.get("CATALYST_TIMEOUT", "300"))
    return anthropic.Timeout(connect=15.0, read=read, write=60.0, pool=15.0)


@dataclass
class Completion:
    text: str
    meta: dict = field(default_factory=dict)


class ReasonerRefusal(Exception):
    pass


class Reasoner(Protocol):
    name: str

    def complete(self, *, stage: str, system: str, user: str, schema: dict) -> Completion: ...


def request_hash(stage: str, system: str, user: str, schema: dict) -> str:
    blob = json.dumps({"stage": stage, "system": system, "user": user, "schema": schema},
                      sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def strict_schema(schema: dict) -> dict:
    """pydantic JSON Schema → 结构化输出可接受的形状：每个 object 都 additionalProperties=false，
    所有属性都列进 required（可空字段靠 null 表达），去掉 default / title。"""
    s = copy.deepcopy(schema)

    def walk(node):
        if isinstance(node, dict):
            node.pop("default", None)
            node.pop("title", None)
            if node.get("type") == "object" and "properties" in node:
                node["additionalProperties"] = False
                node["required"] = list(node["properties"])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(s)
    return s


SCHEMA_ERROR_MARKERS = ("schema", "grammar", "union")


def _error_message(e) -> str:
    """API 错误里给人看的那句话（body.error.message），拿不到就用异常文本。"""
    body = getattr(e, "body", None)
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict) and err.get("message"):
            return str(err["message"])
    return str(e)


class AnthropicReasoner:
    def __init__(self, model: str = DEFAULT_MODEL, effort: str = DEFAULT_EFFORT, max_tokens: int = 32000):
        import anthropic  # 只有实时调用才需要 SDK

        self.client = anthropic.Anthropic(timeout=client_timeout(), max_retries=2)
        self.model, self.effort, self.max_tokens = model, effort, max_tokens
        self.name = f"anthropic:{model}"

    def _stream(self, system: str, user: str, output_format: dict | None):
        output_config = {"effort": self.effort}
        if output_format:
            output_config["format"] = output_format
        with self.client.beta.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config=output_config,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        ) as stream:
            return stream.get_final_message()

    def complete(self, *, stage: str, system: str, user: str, schema: dict) -> Completion:
        import anthropic

        fmt = {"type": "json_schema", "schema": strict_schema(schema)}
        schema_fallback_reason = None
        try:
            msg = self._stream(system, user, fmt)
            mode = "json_schema"
        except anthropic.BadRequestError as e:
            # schema 超出结构化输出支持的范围（语法过大、union 过多等）时退回提示词约束，由校验器兜底；
            # 原因原样记进 meta，录音和 trace 里都看得到为什么退回
            reason = _error_message(e)
            if not any(k in reason.lower() for k in SCHEMA_ERROR_MARKERS):
                raise
            msg = self._stream(system, user + "\n\nOutput a single JSON object that matches this JSON Schema:\n"
                               + json.dumps(schema, ensure_ascii=False), None)
            mode, schema_fallback_reason = "prompt_json", reason
        if msg.stop_reason == "refusal":
            raise ReasonerRefusal(f"{stage}: {getattr(msg, 'stop_details', None)}")
        text = "".join(b.text for b in msg.content if b.type == "text")
        meta = {"model": msg.model, "stop_reason": msg.stop_reason, "mode": mode,
                "usage": msg.usage.model_dump() if msg.usage else None}
        if schema_fallback_reason:
            meta["schema_fallback_reason"] = schema_fallback_reason
        return Completion(text, meta)

    def single_prompt(self, prompt: str) -> str:
        """baseline 组：同一模型、同一资料，单次 prompt，无 schema、无校验。"""
        msg = self._stream("", prompt, None)
        return "".join(b.text for b in msg.content if b.type == "text")


class RecordingReasoner:
    def __init__(self, inner: Reasoner, cassette: Path | str):
        self.inner, self.cassette = inner, Path(cassette)
        self.name = f"record({inner.name})"

    def complete(self, *, stage: str, system: str, user: str, schema: dict) -> Completion:
        out = self.inner.complete(stage=stage, system=system, user=user, schema=schema)
        entry = {"stage": stage, "request_hash": request_hash(stage, system, user, schema),
                 "text": out.text, "meta": out.meta}
        self.cassette.parent.mkdir(parents=True, exist_ok=True)
        with self.cassette.open("a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return out

    def single_prompt(self, prompt: str) -> str:
        """baseline 组也录音（stage=baseline，schema 为空），否则对照组无法回放。"""
        text = self.inner.single_prompt(prompt)
        entry = {"stage": "baseline", "request_hash": request_hash("baseline", "", prompt, {}), "text": text, "meta": {}}
        self.cassette.parent.mkdir(parents=True, exist_ok=True)
        with self.cassette.open("a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return text


class CassetteMiss(Exception):
    pass


class ReplayReasoner:
    def __init__(self, cassette: Path | str):
        self.cassette = Path(cassette)
        self.name = f"replay({self.cassette.parent.name})"
        self._by_hash: dict[str, list[dict]] = {}
        for line in self.cassette.read_text().splitlines():
            e = json.loads(line)
            self._by_hash.setdefault(e["request_hash"], []).append(e)

    def complete(self, *, stage: str, system: str, user: str, schema: dict) -> Completion:
        h = request_hash(stage, system, user, schema)
        queue = self._by_hash.get(h)
        if not queue:
            raise CassetteMiss(f"{stage}: request {h} is not in the recording; the prompt, evidence pack or schema changed, so re-record")
        e = queue.pop(0)
        return Completion(e["text"], {**e.get("meta", {}), "replayed": True})

    def single_prompt(self, prompt: str) -> str:
        return self.complete(stage="baseline", system="", user=prompt, schema={}).text


def default_reasoner() -> AnthropicReasoner:
    return AnthropicReasoner()
