"""离线生成前端 fixture（web/fixtures/*.json）。不调模型，不读 API key。

  ~/Downloads/multiverse-investor-agent/.venv/bin/python web/scripts/make_fixtures.py

方案 B：每个版本是一个 VersionBundle（graph、proposals、branches、node_kinds、edge_kinds、scenario、diff、
excerpts），全部由后端代码给出：运行时把版本写进临时 RunStore，再用 store.bundle(v) 读出来——和
GET /api/runs/{id}/versions/{v} 走同一段代码。批准走 ep.sign，分叉走 ep.fork。前端 fixture 只是这些结果的快照。

唯一手写的是三份计划草稿（DRAFTS，相当于模型输出）和分叉理由的演示句子；有了真实录制后整份替换。
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))  # 保证 import 的是本 worktree 的 catalyst/，不是 venv 里装的那份

from catalyst import entrypoints as ep  # noqa: E402
from catalyst.conditions import evaluate  # noqa: E402
from catalyst.evidence import EvidenceProvider  # noqa: E402
from catalyst.schema import ProposalDraft, parse_graph  # noqa: E402
from catalyst.store import RunStore  # noqa: E402
from eval.fakes import ScriptedReasoner  # noqa: E402
from eval.loader import load_case, load_fixture  # noqa: E402

OUT = ROOT / "web" / "fixtures"
TODAY = "2026-10-18"

JUDGMENT = {
    "original_statement": "Photonic chip adoption is faster than expected",
    "clarified_statement": "By 2027-06-30, quarterly CPO switch shipments reach a level you confirm, and laser vendors "
                           "formally disclose external-light-source design wins",
    "criteria": None, "deadline": "2027-06-30", "requires_user_confirmation": True,
}

# 三份计划草稿：每个 terminal 一份（C1 的三个终点是并列受益，不是竞争）。gate / status / support_status / meta 由代码派生。
DRAFTS = [
    {"terminal_id": "c1.term.laser_vendor",
     "direction": {"instrument": "LITE", "side": "long", "horizon_days": 270,
                   "note": "Laser vendors' data-center light-source revenue revised up as CPO shipments come forward"},
     "entry_condition_ids": ["cond.c1.cpo_shipments", "cond.c1.els_design_wins"],
     "exit_condition_ids": ["cond.c1.dsp_guidance"], "exit_logic": "ANY",
     "key_dependency": {"condition_id": None, "claim_id": "c1.assume.external_laser",
                        "why": "The whole laser path rests on the external-light-source architecture; the pack has an "
                               "integrated-laser counterpoint (sc-005), check it first"},
     "user_judgment": JUDGMENT},
    {"terminal_id": "c1.term.foundry",
     "direction": {"instrument": "TSM", "side": "long", "horizon_days": 270,
                   "note": "Silicon-photonics foundry revenue share rises with CPO volume"},
     "entry_condition_ids": ["cond.c1.cpo_shipments", "cond.c1.foundry_utilization"],
     "exit_condition_ids": [], "exit_logic": "ANY",
     "key_dependency": {"condition_id": "cond.c1.foundry_utilization", "claim_id": None,
                        "why": "Utilization is where foundry revenue is decided; it is the first number to move"},
     "user_judgment": JUDGMENT},
    {"terminal_id": "c1.term.dsp_vendor",
     "direction": {"instrument": "MRVL", "side": "short", "horizon_days": 365,
                   "note": "Pluggable DSP demand is displaced by CPO"},
     "entry_condition_ids": ["cond.c1.dsp_guidance"],
     "exit_condition_ids": ["cond.c1.cpo_shipments"], "exit_logic": "ANY",
     "key_dependency": {"condition_id": None, "claim_id": "c1.pluggable_dsp",
                        "why": "The substitution link is model inference only; no material supports it"},
     "user_judgment": JUDGMENT},
]

DEMO_REASONS = {
    "c1.assume.external_laser": "This is the changed assumption itself: integrated lasers in the scenario",
    "c1.laser_demand": "External light-source demand assumes every CPO port needs an external source; with integrated "
                       "lasers that premise fails",
    "c1.term.laser_vendor": "The laser vendors' upside comes from external light-source demand; the upstream premise is "
                            "challenged, so this conclusion is too",
    "shock.siph_fab_outage": "This is the added shock itself: assumed, not observed",
    "c1.siph_foundry": "The main line shuts for a quarter, so the utilization premise is challenged",
    "c1.term.foundry": "Utilization is challenged; the foundry revenue-share rise slips at least a quarter",
}

COMMON_NOTES = [
    "离线生成，不是模型输出：reasoner 是 eval.fakes.ScriptedReasoner（assessment 理由换成演示句子）",
    "三份计划草稿是脚本里手写的；gate / status / support_status / branches / node_kinds 由后端代码派生",
    "资料包是合成占位片段（synthetic: true），所以分支都是 model_only，并带 synthetic_evidence",
]

# BLOCKED 演示：日期放到设计中标条件的窗口之后，并给一份「覆盖整个窗口、但没有记录」的观测（编的），由代码判 not_met。
BLOCKED_TODAY = "2027-04-15"
BLOCKED_OBS = [{"source": "company_filings", "coverage": {"start": "2026-10-18", "end": BLOCKED_TODAY}, "records": []}]


class DemoReasoner(ScriptedReasoner):
    """ScriptedReasoner 的 fork 输出原样保留，只把 reason 换成演示句子。叠加分叉时基线图自己的 op 也会出现在 user
    里，所以只把「操作：」那一行交给它判断操作类型。"""

    def complete(self, *, stage, system, user, schema):
        if stage == "fork":
            user = next((l for l in user.splitlines() if l.startswith("操作：")), user)
        c = super().complete(stage=stage, system=system, user=user, schema=schema)
        if stage == "fork":
            out = json.loads(c.text)
            for a in out["assessment"]:
                a["reason"] = DEMO_REASONS.get(a["claim_id"], a["reason"])
            c.text = json.dumps(out, ensure_ascii=False)
        return c


class Run:
    """一次离线运行：版本写进临时 RunStore，bundle 由 store.bundle 读出。"""

    def __init__(self, cfg, ev, pack):
        self.cfg, self.ev, self.pack = cfg, ev, pack
        self._tmp = tempfile.TemporaryDirectory()
        self.store = RunStore(self._tmp.name)

    def baseline(self) -> str:
        golden = {k: v for k, v in load_fixture("c1_graph_v1.json").items() if not k.startswith("_")}
        g = parse_graph(golden)
        now = dt.date.fromisoformat(self.cfg.today)
        g = g.model_copy(update={"conditions": [
            c.model_copy(update={"evaluation_status": evaluate(c, self.cfg.observations, now)}) for c in g.conditions]})
        plans = [ep.derive_proposal(ProposalDraft.model_validate(d), g, model="scripted").dump() for d in DRAFTS]
        self.store.put_snapshot(g.dump())
        self.store.put_proposals(g.version, plans)
        self.store.put_observations(g.version, [x.dump() for x in self.ev.pack(self.pack["pack_id"]).excerpts],
                                    synthetic=bool(self.pack.get("synthetic")))
        self.store.log_op(op="inspect", actor="model", input_version=None, output_version=g.version)
        return g.version

    def fork(self, base: str, op: dict) -> str:
        b = self.store.bundle(base)
        res = ep.fork(b["graph"], op, reasoner=DemoReasoner(), evidence=self.ev, config=self.cfg, pack=self.pack,
                      proposals=b["proposals"], store=self.store)
        if not res["ok"]:
            sys.exit(f"fork 失败（{base} + {op['kind']}）：" + "; ".join(res["errors"]))
        return res["graph"]["version"]

    def sign(self, base: str, terminal_id: str | None, **kw) -> str:
        b = self.store.bundle(base)
        res = ep.sign(b["graph"], b["proposals"], terminal_id=terminal_id, config=self.cfg, store=self.store, **kw)
        if not res["ok"]:
            sys.exit(f"sign 失败（{base} → {terminal_id}）：" + "; ".join(res["errors"]))
        return res["version"]

    def write(self, name: str, label: str, versions: list[str], notes: list[str]) -> None:
        fixture = {
            "_source": {"script": "web/scripts/make_fixtures.py", "today": self.cfg.today, "synthetic": bool(self.pack.get("synthetic")),
                        "packs": [self.pack["pack_id"]], "notes": COMMON_NOTES + notes},
            "label": label, "event": JUDGMENT["original_statement"],
            "versions": {v: self.store.bundle(v) for v in versions}, "latest": versions[-1],
        }
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / f"{name}.json").write_text(json.dumps(fixture, ensure_ascii=False, indent=2) + "\n")
        print(f"fixture: web/fixtures/{name}.json（版本 {versions}）")


def main() -> None:
    pack = load_fixture("c1_evidence_pack.json")
    ev = EvidenceProvider(ROOT / "packs")
    ev.register(pack)
    change = load_fixture("c3_change_assumption.json")["op"]
    shock = load_fixture("c3_add_shock.json")["op"]
    cfg = ep.Config(packs=[pack["pack_id"]], today=TODAY, run_prefix="c1")

    r = Run(cfg, ev, pack)
    v1 = r.baseline()
    r.write("c1", "C1 光子芯片（WAIT）", [v1, r.fork(v1, change)], ["c1-v2 = 改假设（集成激光）：LITE 分支变成 hypothetical"])

    blocked = ep.Config(packs=[pack["pack_id"]], today=BLOCKED_TODAY, run_prefix="c1", observations=BLOCKED_OBS)
    r = Run(blocked, ev, pack)
    v1 = r.baseline()
    r.write("c1_blocked", "C1 到期复查（BLOCKED）", [v1, r.fork(v1, change)],
            [f"today={BLOCKED_TODAY}，观测是编的：company_filings 覆盖整个窗口但没有记录，cond.c1.els_design_wins 由代码判 not_met"])

    r = Run(cfg, ev, pack)
    v1 = r.baseline()
    a = r.fork(v1, change)
    b = r.fork(v1, shock)
    r.write("c1_multi", "C1 多情景（A / B / A+B）", [v1, a, b, r.fork(a, shock)],
            ["c1-v2 = 改假设，c1-v3 = 预定义冲击，c1-v4 = 在 c1-v2 上叠加同一个冲击"])

    r = Run(cfg, ev, pack)
    v1 = r.baseline()
    lite = r.sign(v1, "c1.term.laser_vendor")
    lite_fork = r.fork(lite, change)
    tsm = r.sign(v1, "c1.term.foundry")
    tsm_fork = r.fork(tsm, change)
    r.write("c1_approved", "C1 已批准后改假设", [v1, lite, lite_fork, tsm, tsm_fork], [
        f"{lite} = 批准 LITE；{lite_fork} = 在它上面改假设（LITE 受影响：approval_reset，其余 rival_changed）",
        f"{tsm} = 批准 TSM；{tsm_fork} = 在它上面改同一个假设（TSM 不受影响，保留批准，标 rival_changed）"])

    case = load_case("C4")["input"]
    res = ep.discover(case["event"], case.get("target"), reasoner=ScriptedReasoner(), evidence=ev,
                      config=ep.Config(packs=[pack["pack_id"]], today=TODAY, run_prefix="c4"))
    (OUT / "c4_abstain.json").write_text(json.dumps({
        "_source": {"script": "web/scripts/make_fixtures.py", "case": "C4 discover 弃权", "today": TODAY,
                    "packs": [pack["pack_id"]], "notes": ["离线生成：ScriptedReasoner 的 discover 一律弃权"]},
        "label": "C4 弃权（没有因果链）", "event": case["event"],
        "run": {"ok": res["ok"], "errors": res["errors"], "version": None,
                "discover": {k: res[k] for k in ("candidates", "abstained", "abstain_reason")}},
        "versions": {}, "latest": None,
    }, ensure_ascii=False, indent=2) + "\n")
    print("fixture: web/fixtures/c4_abstain.json（版本 []）")


if __name__ == "__main__":
    main()
