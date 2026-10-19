// 所有枚举 → 文案与颜色的唯一映射表。组件不自己写颜色或状态文案。
import type {
  AssessmentStatus, BranchKind, CriticStatus, EvaluationStatus, EvidenceStatus, ExitLogic, Gate, ProposalStatus, Role, SupportStatus,
  VerificationStatus,
} from './types';

export interface Look {
  label: string;
  color: string; // 前景 / 描边色
  bg: string; // 底色
}

const BLUE = { color: '#2457c5', bg: '#e8effc' };
const GREEN = { color: '#1f7a4d', bg: '#e6f4ec' };
const PURPLE = { color: '#6b3fb8', bg: '#efe8fa' };
const ORANGE = { color: '#c25e00', bg: '#fdf0e3' };
const RED = { color: '#b42318', bg: '#fdecea' };
const GREY = { color: '#5b6472', bg: '#f1f3f5' };

export const ROLE: Record<Role, Look> = {
  event: { label: '事件', ...BLUE },
  assumption: { label: '假设', ...GREEN },
  intermediate: { label: '中间环节', ...GREEN },
  terminal: { label: '终点', ...PURPLE },
  shock: { label: '冲击 · 假设，未观测', ...ORANGE },
};

export const EVIDENCE: Record<EvidenceStatus, Look> = {
  supported: { label: 'supported · 有证据', ...GREEN },
  contradicted: { label: 'contradicted · 被反驳', ...RED },
  unknown: { label: 'unknown · 证据不明', ...GREY },
};

export const ASSESSMENT: Record<AssessmentStatus, Look & { mark: string; border: 'solid' | 'dashed' }> = {
  challenged: { label: '受挑战', mark: '●', border: 'solid', ...ORANGE },
  unaffected: { label: '未变', mark: '✓', border: 'solid', ...GREY },
  unresolved: { label: '暂时到不了', mark: '…', border: 'dashed', ...GREY },
};

export const GATE: Record<Gate, Look> = {
  WAIT: { label: 'WAIT · 先别动', ...ORANGE },
  BLOCKED: { label: 'BLOCKED · 受阻', ...RED },
  READY_FOR_REVIEW: { label: 'Ready for review · 待复核', ...GREEN },
};

export const PROPOSAL_STATUS: Record<ProposalStatus, Look> = {
  draft: { label: 'draft · 草稿', ...GREY },
  needs_review: { label: 'needs_review · 待复核', ...BLUE },
};

export const SUPPORT: Record<SupportStatus, Look> = {
  supported: { label: '支持度：supported', ...GREEN },
  challenged: { label: '支持度：challenged', ...ORANGE },
  unknown: { label: '支持度：unknown', ...GREY },
};

export const VERIFICATION: Record<VerificationStatus, Look> = {
  verifiable: { label: '可核实', ...BLUE },
  unverified: { label: '未核实', ...GREY },
};

export const EVALUATION: Record<EvaluationStatus, Look> = {
  met: { label: '已满足', ...GREEN },
  not_met: { label: '未满足', ...RED },
  unknown: { label: '未知', ...GREY },
};

export const EXIT_LOGIC: Record<ExitLogic, Look> = {
  ANY: { label: 'ANY · 任一触发（或）', ...GREY },
  ALL: { label: 'ALL · 全部触发（且）', ...GREY },
};

export const CRITIC: Record<CriticStatus, Look> = {
  disabled: { label: 'Critic 挑刺：未启用（下一期）', ...GREY },
  ok: { label: 'Critic 挑刺', ...ORANGE },
  failed: { label: 'Critic 挑刺：没有跑成', ...GREY },
};

/** 分支类别（D-B9）：靠底纹 + 线型 + 标签区分，不只靠颜色。B1 画布、B2 结论列表、B3 共用这一张表。 */
export interface BranchLook extends Look {
  tag: string | null; // 节点和结论卡片上的标签；evidenced 默认不加字
  line: 'solid' | 'dashed' | 'dotted';
  dash: string | undefined; // SVG strokeDasharray
  border: string; // 描边色
  edge: string; // 连线色
  title: string; // 标题文字色（model_only 减淡用颜色，不用 opacity）
  pattern: string | undefined; // 底纹（CSS background-image）
}

export const BRANCH_KIND: Record<BranchKind, BranchLook> = {
  evidenced: {
    label: '有资料支持', tag: null, color: '#1f7a4d', bg: '#e6f4ec', line: 'solid', dash: undefined,
    border: '#1f7a4d', edge: '#9aa1ab', title: '#1c1f24', pattern: undefined,
  },
  model_only: {
    label: '仅模型推断', tag: '仅推断', color: '#6b7280', bg: '#ffffff', line: 'dashed', dash: '5 4',
    border: '#b9bfc8', edge: '#c4c9d0', title: '#6b7280', pattern: undefined,
  },
  hypothetical: {
    label: '假设 · 未观测', tag: '假设 · 未观测', color: '#5b4a9e', bg: '#f1eef7', line: 'dotted', dash: '2 3',
    border: '#8e7cc3', edge: '#8e7cc3', title: '#4b3f72',
    pattern: 'repeating-linear-gradient(45deg, #e3ddef 0 2px, transparent 2px 8px)',
  },
};

/** 合成资料包导致的降级，跟在「仅推断」后面。 */
export const SYNTHETIC_EVIDENCE_TAG = '资料为占位';

export const KEY_DEPENDENCY = { label: 'Check first · 关键依赖', ...ORANGE };
export const CHANGED_TARGET = { label: '改动的假设', ...BLUE };
