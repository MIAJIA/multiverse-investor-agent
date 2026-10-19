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
from catalyst.branches import dump_views, terminals  # noqa: E402
from catalyst.schema import Excerpt, Graph, Scenario, TradeProposal  # noqa: E402
from catalyst.validator import blocking, validate_graph  # noqa: E402

TYPES_TS = ROOT / "web" / "src" / "types.ts"
# types.ts 名字 → schema.py 的 Literal
ENUMS = {
    "ROLES": "Role", "EVIDENCE_STATUSES": "EvidenceStatus", "STANCES": "Stance", "CONDITION_KINDS": "ConditionKind",
    "VERIFICATION_STATUSES": "VerificationStatus", "EVALUATION_STATUSES": "EvaluationStatus",
    "ASSESSMENT_STATUSES": "AssessmentStatus", "GATES": "Gate", "PROPOSAL_STATUSES": "ProposalStatus",
    "SUPPORT_STATUSES": "SupportStatus", "EXIT_LOGICS": "ExitLogic", "SIDES": "Side", "OP_KINDS": "OpKind",
    "BRANCH_KINDS": "BranchKind",
}
# 不是独立 Literal 别名的枚举：从模型字段的注解里取
FIELD_ENUMS = {"CRITIC_STATUSES": ("CriticReport", "status")}
# 主 session 已决定、后端还没合进 schema 的取值：前端先认，schema 加上后从这里删掉
PENDING: dict[str, set[str]] = {}


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
    for ts_name, (model, field) in FIELD_ENUMS.items():
        m = re.search(rf"export const {ts_name} = \[(.*?)\] as const", ts, re.S)
        got = set(re.findall(r"'([^']+)'", m.group(1))) if m else set()
        want = set(typing.get_args(getattr(schema, model).model_fields[field].annotation))
        if got != want:
            errs.append(f"{ts_name} 与 schema.{model}.{field} 不一致：{sorted(got)} vs {sorted(want)}")
    return errs


def same_canonical(model, d: dict, label: str) -> list[str]:
    return [] if model.model_validate(d).dump() == d else [f"{label} 不是规范形式（与 dump() 不一致）"]


def check_fixture(path: Path) -> list[str]:
    fx = json.loads(path.read_text())
    versions, errs = fx["versions"], []
    if not fx.get("label") or not fx.get("event"):
        errs.append(f"{path.name} 缺少 label 或 event（MOCK 的数据选择器要用）")
    if not versions:  # 没有图的运行（弃权 / 无因果链）：必须带 run，且说明了原因
        run = fx.get("run") or {}
        d = run.get("discover") or {}
        if run.get("version") is not None or not (d.get("abstained") and d.get("abstain_reason")):
            errs.append(f"{path.name} 没有版本，但 run 里不是带理由的弃权")
    elif fx.get("latest") not in versions:
        errs.append(f"latest={fx.get('latest')} 不在 versions 里")
    for v, b in versions.items():
        p = f"{path.name}:{v}"
        g = Graph.model_validate(b["graph"])
        errs += same_canonical(Graph, b["graph"], f"{p} graph")
        if g.version != v:
            errs.append(f"{p} graph.version={g.version}")
        errs += [f"{p} {i}" for i in blocking(validate_graph(g))]
        if "proposal" in b:
            errs.append(f"{p} 还有旧字段 proposal（方案 B 只有 proposals）")
        # 方案 B：每个 terminal 恰好一份计划；同一版本最多一份已批准
        plans = [TradeProposal.model_validate(x) for x in b.get("proposals", [])]
        for x in b.get("proposals", []):
            errs += same_canonical(TradeProposal, x, f"{p} proposal {x.get('terminal_id')}")
        if sorted(x.terminal_id for x in plans) != sorted(terminals(g)):
            errs.append(f"{p} 计划的 terminal 集合 {sorted(x.terminal_id for x in plans)} ≠ 图上的 {sorted(terminals(g))}")
        if bad := [x.terminal_id for x in plans if x.graph_version != v]:
            errs.append(f"{p} 计划的 graph_version 不是 {v}：{bad}")
        if sum(x.user_judgment.confirmed for x in plans) > 1:
            errs.append(f"{p} 同一版本有不止一份已批准的计划")
        if len({(x.user_judgment.original_statement, x.user_judgment.clarified_statement) for x in plans}) > 1:
            errs.append(f"{p} 几份计划的理解确认不一致（应该全版本只有一句）")
        if b.get("scenario"):
            sc = Scenario.model_validate(b["scenario"])
            errs += same_canonical(Scenario, b["scenario"], f"{p} scenario")
            if sc.version != v:
                errs.append(f"{p} scenario.version={sc.version}")
        # 分支与类别表：用后端的 branches.py 复算，必须一致（防止 fixture 被手改）
        synthetic = {x["excerpt_id"] for x in b.get("excerpts", [])} if fx.get("_source", {}).get("synthetic") else set()
        views = dump_views(g, b.get("scenario"), synthetic_excerpt_ids=synthetic)
        for k in ("branches", "node_kinds", "edge_kinds"):
            if b.get(k) != views[k]:
                errs.append(f"{p} {k} 与 catalyst.branches 复算结果不一致")
        parent = g.parent_version
        if parent in versions and graph_diff(versions[parent]["graph"], b["graph"]) != b.get("diff"):
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
    print(f"{'OK' if not errs else 'FAILED'}: {len(paths)} fixture(s), {len(ENUMS) + len(FIELD_ENUMS)} enums")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
