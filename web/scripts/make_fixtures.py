"""离线生成前端 fixture：web/fixtures/c1.json。不调模型，不读 API key。

  ~/Downloads/multiverse-investor-agent/.venv/bin/python web/scripts/make_fixtures.py

格式与 `python -m catalyst promote` 一致（versions / latest），每个版本另带 diff 与 excerpts，
即 GET /api/runs/{id}/versions/{v} 的返回值。有了真实录制后，用 promote 生成同格式文件直接替换。

- 基线 c1-v1：golden C1 图 + 代码派生的提案。golden 图的根节点标了 supported，过不了 inspect 的
  _root_issues，所以这里不走 inspect，直接 derive_proposal；ProposalDraft 是手写的（见 DRAFT）。
- 情景 c1-v2：ep.fork 在 golden 图上跑 C3 的 change_assumption，reasoner 是 ScriptedReasoner，
  只把 assessment 的理由换成可读的演示句子。写范围、补丁校验、assessment 默认值、diff、提案都由代码给出。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))  # 保证 import 的是本 worktree 的 catalyst/，不是 venv 里装的那份

from catalyst import entrypoints as ep  # noqa: E402
from catalyst.evidence import EvidenceProvider  # noqa: E402
from catalyst.schema import ProposalDraft, parse_graph  # noqa: E402
from eval.fakes import ScriptedReasoner  # noqa: E402
from eval.loader import load_fixture  # noqa: E402

OUT = ROOT / "web" / "fixtures" / "c1.json"
TODAY = "2026-10-18"

# 唯一手写的「模型输出」：基线提案草稿。gate / status / support_status / meta 由 derive_proposal 派生。
DRAFT = {
    "direction": {"instrument": "LITE", "side": "long", "horizon_days": 270,
                  "note": "激光器供应商的数据中心光源营收，随 CPO 出货提前而上修"},
    "entry_condition_ids": ["cond.c1.cpo_shipments", "cond.c1.els_design_wins"],
    "exit_condition_ids": ["cond.c1.dsp_guidance"],
    "exit_logic": "ANY",
    "key_dependency": {"condition_id": None, "claim_id": "c1.assume.external_laser",
                       "why": "整条激光器路径都建立在外置光源架构上；资料包里有集成激光的反方片段（sc-005），先查它"},
    "user_judgment": {
        "original_statement": "光子芯片采用快于预期",
        "clarified_statement": "2027-06-30 前，CPO 交换机季度出货量达到用户确认的水平，且激光器供应商正式披露外置光源设计中标",
        "criteria": None,
        "deadline": "2027-06-30",
        "requires_user_confirmation": True,
    },
}

DEMO_REASONS = {
    "c1.assume.external_laser": "这是被改的假设本身：情景下改为集成激光",
    "c1.laser_demand": "外置光源需求以「每个 CPO 端口需要外置光源」为前提；改用集成激光后这条前提不成立",
    "c1.term.laser_vendor": "激光器供应商的营收超预期来自外置光源需求；上游前提受挑战，这个终点随之受挑战",
}


class DemoReasoner(ScriptedReasoner):
    """ScriptedReasoner 的 fork 输出原样保留，只把 reason: "scripted" 换成演示句子。"""

    def complete(self, *, stage, system, user, schema):
        c = super().complete(stage=stage, system=system, user=user, schema=schema)
        if stage == "fork":
            out = json.loads(c.text)
            for a in out["assessment"]:
                a["reason"] = DEMO_REASONS.get(a["claim_id"], a["reason"])
            c.text = json.dumps(out, ensure_ascii=False)
        return c


def main() -> None:
    golden = {k: v for k, v in load_fixture("c1_graph_v1.json").items() if not k.startswith("_")}
    pack = load_fixture("c1_evidence_pack.json")
    fx = load_fixture("c3_change_assumption.json")
    ev = EvidenceProvider(ROOT / "packs")
    ev.register(pack)
    cfg = ep.Config(packs=[pack["pack_id"]], today=TODAY, run_prefix="c1")

    base = parse_graph(golden)
    proposal = ep.derive_proposal(ProposalDraft.model_validate(DRAFT), base, model="scripted").dump()
    res = ep.fork(base.dump(), fx["op"], reasoner=DemoReasoner(), evidence=ev, config=cfg, pack=pack, proposal=proposal)
    if not res["ok"]:
        sys.exit("fork 失败：" + "; ".join(res["errors"]))

    excerpts = [x.dump() for x in ev.pack(pack["pack_id"]).excerpts]
    v1, v2 = base.version, res["graph"]["version"]
    fixture = {
        "_source": {
            "script": "web/scripts/make_fixtures.py",
            "case": "C1 golden + C3 change_assumption",
            "today": TODAY,
            "packs": [pack["pack_id"]],
            "notes": [
                "离线生成，不是模型输出：reasoner 是 eval.fakes.ScriptedReasoner（assessment 理由换成演示句子）",
                "golden C1 图的根节点标了 supported，过不了 inspect 的 _root_issues，所以基线没走 inspect，"
                "直接 derive_proposal；ProposalDraft 是脚本里手写的，gate / status / support_status 由代码派生",
                "资料包是合成占位片段（synthetic: true），不能当证据引用",
            ],
        },
        "versions": {
            v1: {"graph": base.dump(), "proposal": proposal, "scenario": None, "diff": None, "excerpts": excerpts},
            v2: {"graph": res["graph"], "proposal": res["proposal"], "scenario": res["scenario"], "diff": res["diff"],
                 "excerpts": excerpts},
        },
        "latest": v2,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(fixture, ensure_ascii=False, indent=2) + "\n")
    challenged = sorted(k for k, s in res["scenario"]["assessment"].items() if s == "challenged")
    print(f"fixture: {OUT.relative_to(ROOT)}（版本 {list(fixture['versions'])}，challenged={challenged}）")


if __name__ == "__main__":
    main()
