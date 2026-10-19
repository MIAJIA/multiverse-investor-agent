"""Evidence Provider：知识库统一接口，按行业分 pack。

pack 是 packs/<pack_id>.json（EvidencePack 形状）。证据先于推理：入口把选中 pack 的全部片段
放进 Reasoner 的上下文，模型只能引用其中的 excerpt_id。检索（BM25）由证据线补在 search() 上。
"""
from __future__ import annotations

import json
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
            raise FileNotFoundError(f"资料包 {pack_id} 不存在：{path}")
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
                    raise ValueError(f"[{x.excerpt_id}] 在 {seen[x.excerpt_id]} 和 {p.pack_id} 里重复")
                seen[x.excerpt_id] = p.pack_id
        return EvidencePack(pack_id="+".join(pack_ids), synthetic=any(p.synthetic for p in packs),
                            excerpts=[x for p in packs for x in p.excerpts])

    def search(self, query: str, pack_ids: list[str], k: int = 8) -> list[dict]:
        raise NotImplementedError("检索由证据线实现（BM25）；POC 先把整包放进上下文")


def default_provider() -> EvidenceProvider:
    return EvidenceProvider()
