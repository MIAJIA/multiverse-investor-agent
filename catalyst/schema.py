"""数据契约：ClaimGraph（Claim / Mechanism / Condition）、Scenario、Patch、TradeProposal。

字段名沿用 docs/engineering-design.md「核心数据模型」；设计文档没写、实现需要的字段
（node.role、edge.id、condition.id、graph.conditions、patch）照 eval/INTERFACE.md 的提议。

两类模型：
- 持久化对象（Graph、TradeProposal …）：进版本快照，UI / eval / harness 共用这一份。
- 模型输出对象（*Output）：Reasoner 必须返回的 JSON 形状。它比持久化对象少字段——
  凡是由代码裁决的东西（gate、status、meta、evaluation_status、版本号）模型不写。
"""
from __future__ import annotations

import datetime as _dt
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---- 枚举 ---------------------------------------------------------------

Role = Literal["event", "assumption", "intermediate", "terminal", "shock"]
EvidenceStatus = Literal["supported", "contradicted", "unknown"]
Channel = Literal[
    "adoption", "capex", "demand", "supply", "price", "substitution",
    "technology", "policy", "revenue", "sentiment", "logistics", "geopolitics",
]
Sign = Literal["+", "-"]
Tier = Literal["T1", "T2", "T3"]
Stance = Literal["supports", "contradicts", "neutral"]  # neutral：背景信息（如「数据每周才更新」），既不支持也不反驳
ConditionKind = Literal["numeric", "document", "event"]
Predicate = Literal["observed_by", "not_observed_by", "at_deadline"]
Comparator = Literal[">=", "<=", ">", "<", "=="]
VerificationStatus = Literal["verifiable", "unverified"]
EvaluationStatus = Literal["met", "not_met", "unknown"]
AssessmentStatus = Literal["unaffected", "challenged", "unresolved"]
Gate = Literal["WAIT", "BLOCKED", "READY_FOR_REVIEW"]
ProposalStatus = Literal["draft", "needs_review"]
SupportStatus = Literal["supported", "challenged", "unknown"]
CandidateLabel = Literal["grounded", "hypothesis", "not_recommended"]
OpKind = Literal["generate", "discover", "inspect", "change_assumption", "add_shock", "sign"]
ExitLogic = Literal["ANY", "ALL"]
Side = Literal["long", "short"]
BranchKind = Literal["hypothetical", "evidenced", "model_only"]
TrunkKind = Literal["evidenced", "model_only"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    def dump(self) -> dict:
        """规范形式：字段齐全（含默认值）。快照、API、哈希比对一律用它。"""
        return self.model_dump(by_alias=True, mode="json")


def _iso_date(v: str) -> str:
    """绝对日期，或 scenario:<事件>（由用户确认的情景起点，确认前不能判定）。"""
    if not v.startswith("scenario:"):
        _dt.date.fromisoformat(v)
    return v


# ---- 图 -----------------------------------------------------------------

class Claim(Strict):
    id: str
    role: Role
    statement: str
    label: Optional[str] = Field(default=None, description="节点短标题：10 个汉字或 4 个英文词以内，概括 statement")
    original_statement: str
    evidence_status: EvidenceStatus
    time_bucket: Optional[str] = None
    instruments: list[str] = Field(default_factory=list)


class EvidenceRef(Strict):
    tier: Tier
    source_id: str
    excerpt_id: str
    stance: Stance
    supports: str = Field(description="这条证据支持、反驳或交代背景的是 claim 的哪一部分")
    rebuttal: Optional[str] = Field(default=None, description="只用于 stance=contradicts：为什么不构成反驳；为空表示接受反驳。neutral 不需要")


class Mechanism(Strict):
    id: str
    from_: str = Field(alias="from")
    to: str
    channel: Channel
    sign: Sign
    lag_days: Optional[int] = None
    mechanism: str
    evidence: list[EvidenceRef] = Field(default_factory=list)
    model_only: bool = False


class Window(Strict):
    start: str
    end: str

    @field_validator("start", "end")
    @classmethod
    def _dates(cls, v: str) -> str:
        return _iso_date(v)


class Condition(Strict):
    id: str
    claim_id: str
    kind: ConditionKind
    predicate: Predicate
    series: Optional[str] = None
    source: Optional[str] = None
    comparator: Optional[Comparator] = None
    threshold: Optional[float] = None
    threshold_note: Optional[str] = None
    anchor: str = Field(description="绝对日期 YYYY-MM-DD，或 scenario:<事件> 表示由用户确认的情景起点")
    deadline: str
    observation_window: Window
    rule: str
    verification_status: VerificationStatus
    evaluation_status: EvaluationStatus = "unknown"


class Op(Strict):
    kind: OpKind
    target: Optional[str] = None
    value: Any = None
    # AddShock 的 Stage 1 结果（三小时由代码查预定义表填）
    impacts: list[str] = Field(default_factory=list)
    new_nodes: list[Claim] = Field(default_factory=list)
    new_edges: list[Mechanism] = Field(default_factory=list)


class Graph(Strict):
    version: str
    parent_version: Optional[str] = None
    op: Op
    nodes: list[Claim]
    edges: list[Mechanism]
    conditions: list[Condition] = Field(default_factory=list)
    model_output_ref: Optional[str] = None
    observations_ref: Optional[str] = None

    def node(self, node_id: str) -> Claim:
        return next(n for n in self.nodes if n.id == node_id)


# ---- 分叉 ---------------------------------------------------------------

class FieldUpdate(Strict):
    id: str
    fields: dict[str, Any]


class Patch(Strict):
    base_version: str
    node_updates: list[FieldUpdate] = Field(default_factory=list)
    edge_updates: list[FieldUpdate] = Field(default_factory=list)
    condition_updates: list[FieldUpdate] = Field(default_factory=list)
    node_adds: list[Claim] = Field(default_factory=list)
    edge_adds: list[Mechanism] = Field(default_factory=list)
    assessment: dict[str, AssessmentStatus] = Field(default_factory=dict)
    assessment_reason: dict[str, str] = Field(default_factory=dict)


class Scenario(Strict):
    """情景是叠加的：在情景版本上再分叉时，ops 与 assessment 继承父版本的情景。
    base_version 是直接父版本，root_version 是最初的非情景基线（老快照没有这个字段，为 None 时等于 base_version）。
    要撤销一层情景只能回到更早的版本，不能在新版本里抹掉。"""
    version: str
    base_version: str
    ops: list[Op]
    assessment: dict[str, AssessmentStatus]
    assessment_reason: dict[str, str] = Field(default_factory=dict)
    root_version: Optional[str] = None


# ---- 提案 ---------------------------------------------------------------

class Direction(Strict):
    instrument: str
    side: Side
    horizon_days: Optional[int] = None
    note: Optional[str] = None


class KeyDependency(Strict):
    condition_id: Optional[str] = None
    claim_id: Optional[str] = None
    why: str


class UserJudgment(Strict):
    original_statement: str
    clarified_statement: str
    criteria: Optional[str] = None
    deadline: Optional[str] = None
    probability: Optional[float] = None
    requires_user_confirmation: bool = True
    confirmed: bool = False
    confirmed_claim_ids: list[str] = Field(default_factory=list)


class MarketReference(Strict):
    question: str
    source: str
    value: Optional[str] = None


class ScenarioRef(Strict):
    base_version: str
    challenged_claim_ids: list[str]  # 叠加后的全部受挑战 claim，不只是这一层的
    next_checks: list[str]
    root_version: Optional[str] = None  # 最初的非情景基线；老提案没有这个字段


class ProposalMeta(Strict):
    proposal_version: str = Field(description="f\"{graph_version}.{terminal_id}\"：同一版本里的多份计划不重名")
    prompt_version: str
    model: str
    approval_required: Literal[True] = True


class CriticItem(Strict):
    claim_id: str
    challenge: str = Field(description="对这个 claim 提了什么质疑")


CRITIC_DISABLED_REASON = "未启用：不在本期范围"


class CriticReport(Strict):
    """对用户选中那一条链的挑刺结果。本期不启用：一律 status=disabled，见 entrypoints.critic。"""
    status: Literal["disabled", "ok", "failed"]
    reason: str
    items: list[CriticItem] = Field(default_factory=list)


def _critic_disabled() -> CriticReport:
    return CriticReport(status="disabled", reason=CRITIC_DISABLED_REASON, items=[])


class TradeProposal(Strict):
    """一个 terminal 的计划：派生分析 + 用户判断 + 图版本号。每个版本每个 terminal 恰好一份（版本包的 proposals）。
    gate / status / support_status / meta / approval_reset / rival_changed 只由代码写。

    user_judgment.confirmed 就是「已批准」：同一版本最多一份为 true（批准一份会撤销同版本其他计划的批准）。
    approval_reset 与 rival_changed 描述「这个版本相对父版本发生了什么」，每次派生都重新计算，不继承父版本的值；
    只有 fork 会写 true，inspect / sign 一律 false：
    - approval_reset：这份计划在父版本里已批准，这次分叉的写范围碰到了它（docs/changes 4.3），批准已撤销，需要重新批准。
    - rival_changed：这份计划没受这次分叉影响，但同版本另一份计划受了影响。它只说明「另一份计划受了影响」，
      不判断两者是不是竞争关系：并列受益的 terminal（如 C1）也会触发。"""
    terminal_id: str
    status: ProposalStatus = "draft"
    gate: Gate
    direction: Direction
    entry_conditions: list[Condition]
    exit_conditions: list[Condition]
    exit_logic: ExitLogic
    key_dependency: Optional[KeyDependency] = None
    user_judgment: UserJudgment
    market_reference: Optional[MarketReference] = None  # None = no_market
    scenario_ref: Optional[ScenarioRef] = None
    support_status: SupportStatus
    graph_version: str
    meta: ProposalMeta
    critic: CriticReport = Field(default_factory=_critic_disabled)  # 老快照没有这个字段时也按 disabled 解析
    approval_reset: bool = False
    rival_changed: bool = False


# ---- 分支（catalyst/branches.py 由代码推导，不由模型标注）----------------------

class Branch(Strict):
    """一个 terminal 一条分支。kind 按优先级：hypothetical > evidenced > model_only（规则见 branches.py）。"""
    terminal_id: str
    divergence_node_ids: list[str] = Field(description="这条分支祖先里的分叉点：几条出边能到达的 terminal 集合不一样的节点")
    own_node_ids: list[str] = Field(description="(ancestors(t) ∪ {t}) − 其他 terminal 的全部祖先")
    own_edge_ids: list[str] = Field(description="终点落在 own_node_ids 里的边")
    kind: BranchKind
    trunk: TrunkKind = Field(description="共用上游（祖先里不属于独有部分的节点及其入边）的强度")
    synthetic_evidence: bool = Field(description="独有边引用了合成占位资料包的片段：kind 一律不是 evidenced，界面标「资料为占位」")


# ---- 证据 ---------------------------------------------------------------

class Excerpt(Strict):
    source_id: str
    excerpt_id: str
    source: str
    date: str
    text: str
    stance: Stance
    url: Optional[str] = None


class EvidencePack(Strict):
    pack_id: str
    synthetic: bool = False
    note: Optional[str] = None
    excerpts: list[Excerpt]


# ---- 模型输出（Reasoner 返回的 JSON 形状）---------------------------------
# 结构化输出不支持 dict[str, X]，所以这里的映射一律写成列表。

class ModelCondition(Strict):
    id: str
    claim_id: str
    kind: ConditionKind
    predicate: Predicate
    series: Optional[str]
    source: Optional[str]
    comparator: Optional[Comparator]
    threshold: Optional[float]
    threshold_note: Optional[str]
    anchor: str
    deadline: str
    observation_window: Window
    rule: str
    verification_status: VerificationStatus


class ModelUserJudgment(Strict):
    """模型只能提议「澄清后的判断」；确认、概率、确认过的 claim 只能由用户写。"""
    original_statement: str
    clarified_statement: str
    criteria: Optional[str]
    deadline: Optional[str]
    requires_user_confirmation: bool


class ProposalDraft(Strict):
    """一个 terminal 的计划草稿。每个 terminal 恰好一份；direction.instrument 必须是该 terminal 的 instrument。"""
    terminal_id: str
    direction: Direction
    entry_condition_ids: list[str]
    exit_condition_ids: list[str]
    exit_logic: ExitLogic
    key_dependency: Optional[KeyDependency]
    user_judgment: ModelUserJudgment


class Judgment(Strict):
    label: Literal["YES", "NO", "AMBIGUOUS"]
    rationale: str


class InspectOutput(Strict):
    """Inspect 的完整产出。结构化输出放不下这一整份 schema（API 报「compiled grammar is too large」），
    所以实时调用分两步：InspectGraphOutput（图）→ InspectPlanOutput（条件与提案草稿），见 entrypoints.inspect。"""
    no_chain: bool
    no_chain_reason: Optional[str]
    nodes: list[Claim]
    edges: list[Mechanism]
    conditions: list[ModelCondition]
    proposals: list[ProposalDraft]


class InspectGraphOutput(Strict):
    """Inspect 第 1 步：只出因果图（节点与边），或者 no_chain。"""
    no_chain: bool
    no_chain_reason: Optional[str]
    nodes: list[Claim]
    edges: list[Mechanism]


class InspectPlanOutput(Strict):
    """Inspect 第 2 步：在已通过校验的图上挂判定条件，每个 terminal 给一份计划草稿。"""
    conditions: list[ModelCondition]
    proposals: list[ProposalDraft]


class JudgmentOutput(Strict):
    judgment: Judgment


class Candidate(Strict):
    id: str
    direction: str
    instruments: list[str]
    label: CandidateLabel
    rationale: str
    excerpt_ids: list[str]


class DiscoverOutput(Strict):
    candidates: list[Candidate]
    abstained: bool
    abstain_reason: Optional[str]


class AssessmentItem(Strict):
    claim_id: str
    status: AssessmentStatus
    reason: str


class ModelFieldUpdate(Strict):
    id: str
    statement: Optional[str] = None
    label: Optional[str] = None
    mechanism: Optional[str] = None
    sign: Optional[Sign] = None
    lag_days: Optional[int] = None
    threshold: Optional[float] = None
    threshold_note: Optional[str] = None
    deadline: Optional[str] = None
    rule: Optional[str] = None


class ForkOutput(Strict):
    node_updates: list[ModelFieldUpdate]
    edge_updates: list[ModelFieldUpdate]
    condition_updates: list[ModelFieldUpdate]
    assessment: list[AssessmentItem]
    next_checks: list[str]


# ---- 版本包（GET /api/runs/{id}/versions/{v}、promote 的 fixture 同形）------

class VersionBundle(Strict):
    """一个版本的完整视图。proposals 按图里 terminal 的顺序排，每个 terminal 一份；没有提案时是 []。
    branches 由 catalyst/branches.py 从图和情景推导（没有 terminal 时是 []）。"""
    graph: Graph
    proposals: list[TradeProposal]
    branches: list[Branch]
    scenario: Optional[Scenario]
    diff: Optional[dict[str, Any]]
    excerpts: list[Excerpt]


# ---- 便捷解析（eval 的 tests/_adapter.py 会自动用上）---------------------

def _strip_private(data: dict) -> dict:
    return {k: v for k, v in data.items() if not k.startswith("_")}


def parse_graph(data: dict | Graph) -> Graph:
    return data if isinstance(data, Graph) else Graph.model_validate(_strip_private(data))


def parse_condition(data: dict | Condition) -> Condition:
    return data if isinstance(data, Condition) else Condition.model_validate(_strip_private(data))


def parse_pack(data: dict | EvidencePack) -> EvidencePack:
    return data if isinstance(data, EvidencePack) else EvidencePack.model_validate(_strip_private(data))


class LegacyProposalError(ValueError):
    pass


def parse_proposals(data: list | dict | None, graph: dict | Graph) -> list[TradeProposal]:
    """读一个版本的提案。新格式是列表；方案 B 之前的旧文件是单个 dict，包成只有一项的列表。
    旧提案没有 terminal_id 时，按 direction.instrument 在图里找唯一含它的 terminal 填上；
    找不到、或同一个 instrument 出现在多个 terminal 上，直接报错，不猜。"""
    if data is None:
        return []
    if isinstance(data, list):
        return [p if isinstance(p, TradeProposal) else TradeProposal.model_validate(_strip_private(p)) for p in data]
    d = _strip_private(dict(data))
    if not d.get("terminal_id"):
        g = parse_graph(graph)
        inst = (d.get("direction") or {}).get("instrument")
        hits = [n.id for n in g.nodes if n.role == "terminal" and inst in n.instruments]
        if len(hits) != 1:
            raise LegacyProposalError(
                f"[{inst}] 旧提案没有 terminal_id，按标的在图 {g.version} 里找到 {len(hits)} 个 terminal {hits}，无法确定")
        d["terminal_id"] = hits[0]
    return [TradeProposal.model_validate(d)]
