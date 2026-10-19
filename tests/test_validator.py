"""Reference Validator（依赖核心）。设计规则见 docs/eval/test-plan.md A4。"""
import pytest

pytest.importorskip("catalyst", reason="核心包 catalyst 尚未落地")

from eval.loader import load_fixture  # noqa: E402
from tests import _adapter  # noqa: E402
from tests._graph import apply_mutation  # noqa: E402

GRAPH = load_fixture("c1_graph_v1.json")
PACK = load_fixture("c1_evidence_pack.json")
CASES = load_fixture("reference_cases.json")["cases"]


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_validate_references(case):
    graph = apply_mutation(GRAPH, case["node_updates"], case["edge_updates"])
    errors = _adapter.validate_references(graph, PACK)
    if case["expect_error"]:
        assert errors, case["why"]
        assert any(case["error_mentions"] in e for e in errors), f"错误文本应包含 {case['error_mentions']}：{errors}"
    else:
        assert errors == [], f"{case['why']}：{errors}"
