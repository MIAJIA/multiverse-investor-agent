// 所有枚举 → 颜色（和 strings.ts 里的文案）的唯一映射表。组件不自己写颜色或状态文案。
import { T } from './strings';
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
  event: { label: T.role.event, ...BLUE },
  assumption: { label: T.role.assumption, ...GREEN },
  intermediate: { label: T.role.intermediate, ...GREEN },
  terminal: { label: T.role.terminal, ...PURPLE },
  shock: { label: T.role.shock, ...ORANGE },
};

export const EVIDENCE: Record<EvidenceStatus, Look> = {
  supported: { label: T.evidence.supported, ...GREEN },
  contradicted: { label: T.evidence.contradicted, ...RED },
  unknown: { label: T.evidence.unknown, ...GREY },
};

export const ASSESSMENT: Record<AssessmentStatus, Look & { mark: string; border: 'solid' | 'dashed' }> = {
  challenged: { label: T.assessment.challenged, mark: '●', border: 'solid', ...ORANGE },
  unaffected: { label: T.assessment.unaffected, mark: '✓', border: 'solid', ...GREY },
  unresolved: { label: T.assessment.unresolved, mark: '…', border: 'dashed', ...GREY },
};

export const GATE: Record<Gate, Look> = {
  WAIT: { label: T.gate.WAIT, ...ORANGE },
  BLOCKED: { label: T.gate.BLOCKED, ...RED },
  READY_FOR_REVIEW: { label: T.gate.READY_FOR_REVIEW, ...GREEN },
};

export const PROPOSAL_STATUS: Record<ProposalStatus, Look> = {
  draft: { label: T.proposalStatus.draft, ...GREY },
  needs_review: { label: T.proposalStatus.needs_review, ...BLUE },
};

export const SUPPORT: Record<SupportStatus, Look> = {
  supported: { label: T.support.supported, ...GREEN },
  challenged: { label: T.support.challenged, ...ORANGE },
  unknown: { label: T.support.unknown, ...GREY },
};

export const VERIFICATION: Record<VerificationStatus, Look> = {
  verifiable: { label: T.verification.verifiable, ...BLUE },
  unverified: { label: T.verification.unverified, ...GREY },
};

export const EVALUATION: Record<EvaluationStatus, Look> = {
  met: { label: T.evaluation.met, ...GREEN },
  not_met: { label: T.evaluation.not_met, ...RED },
  unknown: { label: T.evaluation.unknown, ...GREY },
};

export const EXIT_LOGIC: Record<ExitLogic, Look> = {
  ANY: { label: T.exitLogic.ANY, ...GREY },
  ALL: { label: T.exitLogic.ALL, ...GREY },
};

export const CRITIC: Record<CriticStatus, Look> = {
  disabled: { label: T.critic.disabled, ...GREY },
  ok: { label: T.critic.ok, ...ORANGE },
  failed: { label: T.critic.failed, ...GREY },
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
    label: T.branchKind.evidenced.label, tag: T.branchKind.evidenced.tag, color: '#1f7a4d', bg: '#e6f4ec', line: 'solid', dash: undefined,
    border: '#1f7a4d', edge: '#9aa1ab', title: '#1c1f24', pattern: undefined,
  },
  model_only: {
    label: T.branchKind.model_only.label, tag: T.branchKind.model_only.tag, color: '#6b7280', bg: '#ffffff', line: 'dashed', dash: '5 4',
    border: '#b9bfc8', edge: '#c4c9d0', title: '#6b7280', pattern: undefined,
  },
  hypothetical: {
    label: T.branchKind.hypothetical.label, tag: T.branchKind.hypothetical.tag, color: '#5b4a9e', bg: '#f1eef7', line: 'dotted', dash: '2 3',
    border: '#8e7cc3', edge: '#8e7cc3', title: '#4b3f72',
    pattern: 'repeating-linear-gradient(45deg, #e3ddef 0 2px, transparent 2px 8px)',
  },
};

/** 合成资料包导致的降级，跟在「仅推断」后面。 */
export const SYNTHETIC_EVIDENCE_TAG = T.syntheticEvidenceTag;

export const KEY_DEPENDENCY = { label: T.keyDependency, ...ORANGE };
export const CHANGED_TARGET = { label: T.changedTarget, ...BLUE };
