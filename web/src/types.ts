// catalyst/schema.py 的 TS 镜像：字段名一字不改。枚举取值数组由 scripts/check_fixtures.py 与 schema 的 Literal 比对。

export const ROLES = ['event', 'assumption', 'intermediate', 'terminal', 'shock'] as const;
export const EVIDENCE_STATUSES = ['supported', 'contradicted', 'unknown'] as const;
export const STANCES = ['supports', 'contradicts', 'neutral'] as const; // neutral：背景信息，不算正方也不算反方
export const CONDITION_KINDS = ['numeric', 'document', 'event'] as const;
export const VERIFICATION_STATUSES = ['verifiable', 'unverified'] as const;
export const EVALUATION_STATUSES = ['met', 'not_met', 'unknown'] as const;
export const ASSESSMENT_STATUSES = ['unaffected', 'challenged', 'unresolved'] as const;
export const GATES = ['WAIT', 'BLOCKED', 'READY_FOR_REVIEW'] as const;
export const PROPOSAL_STATUSES = ['draft', 'needs_review'] as const;
export const SUPPORT_STATUSES = ['supported', 'challenged', 'unknown'] as const;
export const EXIT_LOGICS = ['ANY', 'ALL'] as const;
export const SIDES = ['long', 'short'] as const;
export const CRITIC_STATUSES = ['disabled', 'ok', 'failed'] as const;
export const OP_KINDS = ['generate', 'discover', 'inspect', 'change_assumption', 'add_shock', 'sign'] as const;
// 方案 B：分支类别由后端 branches.py 推导（kind 三类，trunk 只有前两类）
export const BRANCH_KINDS = ['evidenced', 'model_only', 'hypothetical'] as const;

export type Role = (typeof ROLES)[number];
export type EvidenceStatus = (typeof EVIDENCE_STATUSES)[number];
export type Stance = (typeof STANCES)[number];
export type ConditionKind = (typeof CONDITION_KINDS)[number];
export type VerificationStatus = (typeof VERIFICATION_STATUSES)[number];
export type EvaluationStatus = (typeof EVALUATION_STATUSES)[number];
export type AssessmentStatus = (typeof ASSESSMENT_STATUSES)[number];
export type Gate = (typeof GATES)[number];
export type ProposalStatus = (typeof PROPOSAL_STATUSES)[number];
export type SupportStatus = (typeof SUPPORT_STATUSES)[number];
export type ExitLogic = (typeof EXIT_LOGICS)[number];
export type Side = (typeof SIDES)[number];
export type CriticStatus = (typeof CRITIC_STATUSES)[number];
export type OpKind = (typeof OP_KINDS)[number];
export type BranchKind = (typeof BRANCH_KINDS)[number];

export interface Claim {
  id: string;
  role: Role;
  statement: string;
  original_statement: string;
  label: string | null; // 短标题：模型写，10 个汉字以内；为空时前端截短 statement
  evidence_status: EvidenceStatus;
  time_bucket: string | null;
  instruments: string[];
}

export interface EvidenceRef {
  tier: 'T1' | 'T2' | 'T3';
  source_id: string;
  excerpt_id: string;
  stance: Stance;
  supports: string;
  rebuttal: string | null; // 只用于 contradicts
}

export interface Mechanism {
  id: string;
  from: string;
  to: string;
  channel: string;
  sign: '+' | '-';
  lag_days: number | null;
  mechanism: string;
  evidence: EvidenceRef[];
  model_only: boolean;
}

export interface Window {
  start: string;
  end: string;
}

export interface Condition {
  id: string;
  claim_id: string;
  kind: ConditionKind;
  predicate: 'observed_by' | 'not_observed_by' | 'at_deadline';
  series: string | null;
  source: string | null;
  comparator: '>=' | '<=' | '>' | '<' | '==' | null;
  threshold: number | null;
  threshold_note: string | null;
  anchor: string;
  deadline: string;
  observation_window: Window;
  rule: string;
  verification_status: VerificationStatus;
  evaluation_status: EvaluationStatus;
}

export interface Op {
  kind: OpKind;
  target: string | null;
  value: unknown;
  impacts: string[];
  new_nodes: Claim[];
  new_edges: Mechanism[];
}

export interface Graph {
  version: string;
  parent_version: string | null;
  op: Op;
  nodes: Claim[];
  edges: Mechanism[];
  conditions: Condition[];
  model_output_ref: string | null;
  observations_ref: string | null;
}

export interface Scenario {
  version: string;
  base_version: string;
  ops: Op[];
  assessment: Record<string, AssessmentStatus>;
  assessment_reason: Record<string, string>;
  root_version: string | null; // 最初的非情景基线；叠加时 ops / assessment 都继承父情景
}

export interface Direction {
  instrument: string;
  side: Side;
  horizon_days: number | null;
  note: string | null;
}

export interface KeyDependency {
  condition_id: string | null;
  claim_id: string | null;
  why: string;
}

export interface UserJudgment {
  original_statement: string;
  clarified_statement: string;
  criteria: string | null;
  deadline: string | null;
  probability: number | null;
  requires_user_confirmation: boolean;
  confirmed: boolean;
  confirmed_claim_ids: string[];
  note: string | null; // 方案 B：批准时的可选备注
}

export interface ScenarioRef {
  base_version: string;
  challenged_claim_ids: string[]; // 叠加后的全部受挑战 claim
  next_checks: string[];
  root_version: string | null;
}

export interface CriticReport {
  status: CriticStatus;
  reason: string;
  items: { claim_id: string; challenge: string }[];
}

export interface TradeProposal {
  status: ProposalStatus;
  gate: Gate;
  direction: Direction;
  entry_conditions: Condition[];
  exit_conditions: Condition[];
  exit_logic: ExitLogic;
  key_dependency: KeyDependency | null;
  user_judgment: UserJudgment;
  market_reference: { question: string; source: string; value: string | null } | null;
  scenario_ref: ScenarioRef | null;
  support_status: SupportStatus;
  graph_version: string;
  critic: CriticReport; // 本期一律 disabled
  // 方案 B：每份计划对应一个 terminal；改假设后由后端标出受影响的批准
  terminal_id: string;
  approval_reset: boolean; // true：前提已改动，请重新批准
  rival_changed: boolean; // true：同一版本里另一份计划受了影响
  meta: { proposal_version: string; prompt_version: string; model: string; approval_required: true };
}

export interface Excerpt {
  source_id: string;
  excerpt_id: string;
  source: string;
  date: string;
  text: string;
  stance: Stance;
  url: string | null;
}

export interface GraphDiff {
  nodes_changed: string[];
  nodes_added: string[];
  nodes_removed: string[];
  edges_changed: string[];
  edges_added: string[];
  edges_removed: string[];
  conditions_changed: string[];
  conditions_added: string[];
  conditions_removed: string[];
  changed_claim_ids: string[];
}

/** GET /api/runs/{id}/versions/{v} 的返回值，也是 fixture 里 versions[v] 的形状（方案 B）。 */
export interface VersionBundle {
  graph: Graph;
  proposals: TradeProposal[]; // 每个 terminal 一份，按 terminal_id 关联，不依赖顺序
  branches: Branch[];
  node_kinds: Record<string, BranchKind>; // 后端给的节点类别，前端只查表
  edge_kinds: Record<string, BranchKind>;
  scenario: Scenario | null;
  diff: GraphDiff | null;
  excerpts: Excerpt[];
}

export interface Fixture {
  _source?: unknown;
  label: string; // MOCK 数据选择器里的名字
  event: string;
  run?: RunCreated; // 没有图的运行（弃权）时，POST /runs 的返回值
  versions: Record<string, VersionBundle>;
  latest: string | null;
}

export interface DiscoverResult {
  candidates: unknown[];
  abstained: boolean | null;
  abstain_reason: string | null;
}

/** 所有写操作（建 run、fork、sign）的返回值：成功时给新版本号，失败时给校验器的拒绝理由。 */
export interface WriteResult {
  ok: boolean;
  errors: string[];
  version: string | null;
}

export interface WebStatus {
  online: boolean;
  status?: string;
  message?: string | null;
}

export interface RunCreated extends WriteResult {
  run_id: string | null;
  web?: WebStatus | null; // 联网开关的结果：开 / 关、拿到几段或失败原因
  discover?: DiscoverResult | null;
  inspect?: { no_chain?: boolean | null; no_chain_reason?: string | null } | null;
}

export interface ConditionOverride {
  threshold?: number | null;
  deadline?: string;
}


// ---- 方案 B（B-最小）--------------------------------------------------------

export interface Branch {
  terminal_id: string;
  divergence_node_ids: string[];
  own_node_ids: string[];
  own_edge_ids: string[];
  kind: BranchKind;
  trunk: Exclude<BranchKind, 'hypothetical'>;
  synthetic_evidence: boolean; // true：支撑它的是占位资料包，所以降级成 model_only
}

/** 方案 B 的版本包就是 VersionBundle；保留这个名字给早先写的组件用。 */
export type PlanBBundle = VersionBundle;

/** sign 的新语义是「批准」：terminal_id 为 null 表示本版本一份都不批准（撤销批准）。 */
export interface ApproveBody {
  version: string;
  terminal_id: string | null;
  clarified_statement?: string;
  criteria?: string | null;
  deadline?: string | null;
  note?: string | null;
  confirmed_claim_ids: string[];
  condition_overrides: Record<string, ConditionOverride>;
}
