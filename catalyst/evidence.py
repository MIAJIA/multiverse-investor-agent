"""Evidence Provider：知识库统一接口，按行业分 pack。

pack 是 packs/<pack_id>.json（EvidencePack 形状）。证据先于推理：入口把选中 pack 的全部片段
放进 Reasoner 的上下文，模型只能引用其中的 excerpt_id。检索（BM25）由证据线补在 search() 上。
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

from catalyst.schema import EvidencePack, parse_pack

DEFAULT_PACKS_DIR = Path(__file__).resolve().parent.parent / "packs"


class EvidenceProvider:
    def __init__(self, packs_dir: Path | str = DEFAULT_PACKS_DIR):
        self.packs_dir = Path(packs_dir)
        self._registered: dict[str, EvidencePack] = {}

    def register(self, pack: EvidencePack | dict) -> EvidencePack:
        p = parse_pack(pack)
        self._registered[p.pack_id] = p
        return p

    def pack(self, pack_id: str) -> EvidencePack:
        if pack_id in self._registered:
            return self._registered[pack_id]
        path = self.packs_dir / f"{pack_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"evidence pack {pack_id} does not exist: {path}")
        return self.register(json.loads(path.read_text()))

    def load_pack(self, pack_id: str) -> list[dict]:
        return [x.dump() for x in self.pack(pack_id).excerpts]

    def combined(self, pack_ids: list[str]) -> EvidencePack | None:
        """多个 pack 合成本轮的资料包；excerpt_id 必须全局唯一。"""
        if not pack_ids:
            return None
        packs = [self.pack(i) for i in pack_ids]
        seen: dict[str, str] = {}
        for p in packs:
            for x in p.excerpts:
                if x.excerpt_id in seen:
                    raise ValueError(f"[{x.excerpt_id}] appears in both {seen[x.excerpt_id]} and {p.pack_id}")
                seen[x.excerpt_id] = p.pack_id
        return EvidencePack(pack_id="+".join(pack_ids), synthetic=any(p.synthetic for p in packs),
                            excerpts=[x for p in packs for x in p.excerpts])

    def search(self, query: str, pack_ids: list[str], k: int = 8) -> list[dict]:
        """BM25 关键词检索：返回得分 > 0 的前 k 段，每段是片段 dict 加 pack_id 和 score。

        索引 text 与 source 两个字段；英文按单词、中文按字符二元组分词（见 _tokens）。
        """
        docs = [(p.pack_id, x) for p in (self.pack(i) for i in pack_ids) for x in p.excerpts]
        q = set(_tokens(query))
        if not docs or not q:
            return []
        toks = [_tokens(f"{x.text} {x.source}") for _, x in docs]
        n, avgdl = len(docs), (sum(map(len, toks)) / len(docs)) or 1.0
        df = Counter(t for ts in toks for t in set(ts))
        scored = []
        for (pid, x), ts in zip(docs, toks):
            tf = Counter(ts)
            s = sum(_idf(n, df[t]) * tf[t] * (_K1 + 1) / (tf[t] + _K1 * (1 - _B + _B * len(ts) / avgdl))
                    for t in q if tf[t])
            if s > 0:
                scored.append({**x.dump(), "pack_id": pid, "score": round(s, 4)})
        scored.sort(key=lambda d: -d["score"])
        return scored[:k]


_K1, _B = 1.5, 0.75
_WORD = re.compile(r"[a-z0-9]+(?:[.'-][a-z0-9]+)*")
_CJK = re.compile(r"[㐀-䶿一-鿿豈-﫿]+")


def _tokens(text: str) -> list[str]:
    """英文与数字按单词（小写）；中文按字符二元组，单字成段时保留单字。"""
    text = text.lower()
    out = _WORD.findall(_CJK.sub(" ", text))
    for run in _CJK.findall(text):
        out += [run] if len(run) == 1 else [run[i:i + 2] for i in range(len(run) - 1)]
    return out


def _idf(n: int, df: int) -> float:
    return math.log(1 + (n - df + 0.5) / (df + 0.5))


def default_provider() -> EvidenceProvider:
    return EvidenceProvider()
