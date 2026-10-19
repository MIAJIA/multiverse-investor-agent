"""真实资料包（packs/*.json）的结构检查与 BM25 检索排序。"""
import datetime as dt
import json
import re
from pathlib import Path

import pytest

from catalyst.evidence import DEFAULT_PACKS_DIR, EvidenceProvider, _tokens
from catalyst.schema import parse_pack

PREFIX = {"semiconductor": "sc", "hormuz": "hz"}
TIERS = ("T1", "T2", "T3")


def _raw(pack_id: str) -> dict:
    return json.loads((DEFAULT_PACKS_DIR / f"{pack_id}.json").read_text())


@pytest.fixture(scope="module")
def provider() -> EvidenceProvider:
    return EvidenceProvider()


@pytest.mark.parametrize("pack_id", PREFIX)
def test_pack_parses(pack_id):
    p = parse_pack(_raw(pack_id))
    assert p.pack_id == pack_id
    assert p.note and p.excerpts


@pytest.mark.parametrize("pack_id", PREFIX)
def test_excerpt_ids_follow_prefix(pack_id):
    pattern = re.compile(rf"^{PREFIX[pack_id]}-\d{{3}}$")
    ids = [x.excerpt_id for x in parse_pack(_raw(pack_id)).excerpts]
    assert all(pattern.match(i) for i in ids), ids
    assert len(ids) == len(set(ids))


def test_excerpt_ids_globally_unique():
    ids = [x.excerpt_id for pid in PREFIX for x in parse_pack(_raw(pid)).excerpts]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("pack_id", PREFIX)
def test_dates_real_and_not_synthetic(pack_id):
    p = parse_pack(_raw(pack_id))
    assert p.synthetic is False
    for x in p.excerpts:
        d = dt.date.fromisoformat(x.date)
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", x.date)
        assert d <= dt.date(2026, 10, 18), x.excerpt_id


@pytest.mark.parametrize("pack_id", PREFIX)
def test_every_excerpt_is_traceable(pack_id):
    """每段写明来源等级，并能回溯到 URL；文本短到一两句。"""
    for x in parse_pack(_raw(pack_id)).excerpts:
        assert any(f"（{t} " in x.source for t in TIERS), x.source
        assert x.url and x.url.startswith("https://"), x.excerpt_id
        assert len(x.text) <= 160, x.excerpt_id


@pytest.mark.parametrize("pack_id", PREFIX)
def test_each_pack_has_contradicts(pack_id):
    stances = {x.stance for x in parse_pack(_raw(pack_id)).excerpts}
    assert stances == {"supports", "contradicts"}


def test_combined(provider):
    pack = provider.combined(["semiconductor", "hormuz"])
    assert pack.synthetic is False
    assert len(pack.excerpts) == len(_raw("semiconductor")["excerpts"]) + len(_raw("hormuz")["excerpts"])


# ---- search（BM25）------------------------------------------------------

@pytest.mark.parametrize("query, expected", [
    ("CPO 激光器 光源需求", "sc-025"),
    ("co-packaged optics TSMC COUPE", "sc-023"),
    ("H200 出口中国 许可审查", "sc-029"),
    ("CoWoS 产能 2027 扩产", "sc-008"),
    ("PortWatch 更新 数据滞后", "hz-006"),
    ("霍尔木兹 石油流量 消费", "hz-002"),
    ("CPO 激光器 订单 需求", "sc-039"),
    ("集成激光 替代", "sc-043"),
    ("模型权重 出口管制", "sc-044"),
    ("宣布开放 过境 恢复", "hz-011"),
    ("曼德海峡 停火", "hz-016"),
])
def test_search_top3(provider, query, expected):
    top = [x["excerpt_id"] for x in provider.search(query, ["semiconductor", "hormuz"], k=3)]
    assert expected in top, (query, top)


def test_search_shape_and_order(provider):
    out = provider.search("TSMC HPC 收入", ["semiconductor"], k=5)
    assert 0 < len(out) <= 5
    assert all(x["pack_id"] == "semiconductor" and x["score"] > 0 for x in out)
    assert [x["score"] for x in out] == sorted((x["score"] for x in out), reverse=True)
    assert set(_raw("semiconductor")["excerpts"][0]) <= set(out[0])


def test_search_respects_pack_ids(provider):
    assert all(x["pack_id"] == "hormuz" for x in provider.search("TSMC 海峡", ["hormuz"]))


def test_search_no_hit_returns_empty(provider):
    assert provider.search("中期选举", ["semiconductor", "hormuz"]) == []
    assert provider.search("", ["semiconductor"]) == []
    assert provider.search("CPO", []) == []


def test_tokens_english_words_and_cjk_bigrams():
    assert _tokens("CPO 光子芯片 H200") == ["cpo", "h200", "光子", "子芯", "芯片"]
    assert _tokens("光") == ["光"]


def test_search_on_registered_pack(tmp_path):
    p = EvidenceProvider(packs_dir=tmp_path)
    p.register({"pack_id": "t", "excerpts": [
        {"source_id": "a", "excerpt_id": "t-1", "source": "x", "date": "2026-01-01", "stance": "supports", "text": "外置激光光源"},
        {"source_id": "a", "excerpt_id": "t-2", "source": "x", "date": "2026-01-01", "stance": "supports", "text": "代工产能利用率"},
    ]})
    assert [x["excerpt_id"] for x in p.search("激光", ["t"])] == ["t-1"]
