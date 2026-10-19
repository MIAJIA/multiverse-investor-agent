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


class AnthropicReasoner:
    def __init__(self, model: str = DEFAULT_MODEL, effort: str = DEFAULT_EFFORT, max_tokens: int = 32000):
        import anthropic  # 只有实时调用才需要 SDK

        self.client = anthropic.Anthropic()
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
        try:
            msg = self._stream(system, user, fmt)
            mode = "json_schema"
        except anthropic.BadRequestError as e:
            # schema 超出结构化输出支持的范围时退回提示词约束，由校验器兜底
            if "schema" not in str(e).lower():
                raise
            msg = self._stream(system, user + "\n\n只输出一个 JSON 对象，符合下面的 JSON Schema：\n"
                               + json.dumps(schema, ensure_ascii=False), None)
            mode = "prompt_json"
        if msg.stop_reason == "refusal":
            raise ReasonerRefusal(f"{stage}: {getattr(msg, 'stop_details', None)}")
        text = "".join(b.text for b in msg.content if b.type == "text")
        return Completion(text, {"model": msg.model, "stop_reason": msg.stop_reason, "mode": mode,
                                 "usage": msg.usage.model_dump() if msg.usage else None})

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
        return self.inner.single_prompt(prompt)


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
            raise CassetteMiss(f"{stage}: 录音里没有这个请求（{h}）——prompt、资料包或 schema 变了，需要重新录制")
        e = queue.pop(0)
        return Completion(e["text"], {**e.get("meta", {}), "replayed": True})


def default_reasoner() -> AnthropicReasoner:
    return AnthropicReasoner()
