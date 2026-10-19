// 所有枚举 → 文案与颜色的唯一映射表。组件不自己写颜色或状态文案。
import type {
  AssessmentStatus, CriticStatus, EvaluationStatus, EvidenceStatus, ExitLogic, Gate, ProposalStatus, Role, SupportStatus,
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

export const KEY_DEPENDENCY = { label: 'Check first · 关键依赖', ...ORANGE };
export const CHANGED_TARGET = { label: '改动的假设', ...BLUE };
