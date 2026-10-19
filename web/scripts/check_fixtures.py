"""用 schema 校验前端 fixture，并核对 src/types.ts 的枚举与 schema.py 一致。退出码非 0 即失败。

  ~/Downloads/multiverse-investor-agent/.venv/bin/python web/scripts/check_fixtures.py [fixture.json ...]
"""
from __future__ import annotations

import json
import re
import sys
import typing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from catalyst import schema  # noqa: E402
from catalyst.diff import diff as graph_diff  # noqa: E402
from catalyst.schema import Excerpt, Graph, Scenario, TradeProposal  # noqa: E402
from catalyst.validator import blocking, validate_graph  # noqa: E402

TYPES_TS = ROOT / "web" / "src" / "types.ts"
# types.ts 名字 → schema.py 的 Literal
ENUMS = {
    "ROLES": "Role", "EVIDENCE_STATUSES": "EvidenceStatus", "STANCES": "Stance", "CONDITION_KINDS": "ConditionKind",
    "VERIFICATION_STATUSES": "VerificationStatus", "EVALUATION_STATUSES": "EvaluationStatus",
    "ASSESSMENT_STATUSES": "AssessmentStatus", "GATES": "Gate", "PROPOSAL_STATUSES": "ProposalStatus",
    "SUPPORT_STATUSES": "SupportStatus", "EXIT_LOGICS": "ExitLogic", "SIDES": "Side", "OP_KINDS": "OpKind",
}
# 主 session 已决定、后端还没合进 schema 的取值：前端先认，schema 加上后从这里删掉
PENDING = {"OpKind": {"sign"}}


def check_enums() -> list[str]:
    ts = TYPES_TS.read_text()
    errs = []
    for ts_name, py_name in ENUMS.items():
        m = re.search(rf"export const {ts_name} = \[(.*?)\] as const", ts, re.S)
        if not m:
            errs.append(f"types.ts 缺少 {ts_name}")
            continue
        got = set(re.findall(r"'([^']+)'", m.group(1)))
        want = set(typing.get_args(getattr(schema, py_name)))
        extra = got - want - PENDING.get(py_name, set())
        if extra or want - got:
            errs.append(f"{ts_name} 与 schema.{py_name} 不一致：多 {sorted(extra)}，少 {sorted(want - got)}")
    return errs


def same_canonical(model, d: dict, label: str) -> list[str]:
    return [] if model.model_validate(d).dump() == d else [f"{label} 不是规范形式（与 dump() 不一致）"]


def check_fixture(path: Path) -> list[str]:
    fx = json.loads(path.read_text())
    versions, errs = fx["versions"], []
    if fx.get("latest") not in versions:
        errs.append(f"latest={fx.get('latest')} 不在 versions 里")
    for v, b in versions.items():
        p = f"{path.name}:{v}"
        g = Graph.model_validate(b["graph"])
        errs += same_canonical(Graph, b["graph"], f"{p} graph")
        if g.version != v:
            errs.append(f"{p} graph.version={g.version}")
        errs += [f"{p} {i}" for i in blocking(validate_graph(g))]
        if b.get("proposal"):
            pr = TradeProposal.model_validate(b["proposal"])
            errs += same_canonical(TradeProposal, b["proposal"], f"{p} proposal")
            if pr.graph_version != v:
                errs.append(f"{p} proposal.graph_version={pr.graph_version}")
        if b.get("scenario"):
            sc = Scenario.model_validate(b["scenario"])
            errs += same_canonical(Scenario, b["scenario"], f"{p} scenario")
            if sc.version != v or sc.base_version not in versions:
                errs.append(f"{p} scenario.version / base_version 不对：{sc.version} / {sc.base_version}")
            elif b.get("diff") is not None and graph_diff(versions[sc.base_version]["graph"], b["graph"]) != b["diff"]:
                errs.append(f"{p} diff 与 catalyst.diff 复算结果不一致")
        known = {Excerpt.model_validate(x).excerpt_id for x in b.get("excerpts", [])}
        cited = {r.excerpt_id for e in g.edges for r in e.evidence}
        if missing := cited - known:
            errs.append(f"{p} 引用的片段不在 excerpts 里：{sorted(missing)}")
    return errs


def main() -> None:
    paths = [Path(a) for a in sys.argv[1:]] or sorted((ROOT / "web" / "fixtures").glob("*.json"))
    errs = check_enums()
    for path in paths:
        errs += check_fixture(path)
    for e in errs:
        print(f"FAIL {e}")
    print(f"{'OK' if not errs else 'FAILED'}: {len(paths)} fixture(s), {len(ENUMS)} enums")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
