// B2（答案卡）的属性、草稿类型和只读推导：按终点顺序排的计划、已批准的那份、当前选中、分支、前提。
import { nodeLabel } from '../../node/labels';
import { toFlow } from '../../toFlow';
import type { Claim, ConditionOverride, PlanBBundle, TradeProposal } from '../../types';

/** 一份计划还没提交的输入：改过的阈值 / 截止、勾选的前提、备注。 */
export interface PlanDraft {
  overrides: Record<string, ConditionOverride>;
  confirmedClaimIds: string[];
  note: string;
}

export const EMPTY_DRAFT: PlanDraft = { overrides: {}, confirmedClaimIds: [], note: '' };

/** 「你的想法」确认；text 是用户改过的说法，null = 沿用后端的 clarified_statement。 */
export interface Understood {
  confirmed: boolean;
  text: string | null;
}

export interface ApproveProps {
  bundle: PlanBBundle;
  selected: string | null;
  onSelect: (terminalId: string) => void;
  drafts: Record<string, PlanDraft>;
  onDraft: (terminalId: string, d: PlanDraft) => void;
  understood: Understood;
  onUnderstood: (u: Understood) => void;
  onApprove: (terminalId: string) => void;
  onRevoke: () => void;
  busy: boolean;
  labelOf?: (c: Claim) => string;
}

export function approveModel({ bundle, selected, labelOf = nodeLabel }: ApproveProps) {
  const { graph, proposals, branches } = bundle;
  const node = (id: string) => graph.nodes.find((n) => n.id === id)!;
  const order = new Map(toFlow(graph).nodes.map((n) => [n.id, n.position.x])); // 纯展示：按画布左右顺序
  const rows = [...proposals].sort((a, b) => (order.get(a.terminal_id!) ?? 0) - (order.get(b.terminal_id!) ?? 0));
  const approved = proposals.find((p) => p.user_judgment.confirmed) ?? null;
  const current = rows.find((p) => p.terminal_id === selected) ?? null;
  const branchOf = (p: TradeProposal) => branches.find((b) => b.terminal_id === p.terminal_id);
  const premises = (p: TradeProposal) => (branchOf(p)?.own_node_ids ?? []).filter((id) => id !== p.terminal_id);
  const title = (p: TradeProposal) => labelOf(node(p.terminal_id!));
  const uj = proposals[0]?.user_judgment; // 后端保证同一版本几份计划的这一句相同
  return { graph, rows, approved, current, branchOf, premises, title, node, labelOf, uj };
}

/** 数值条件里阈值还是 null、用户也没填的个数。 */
export function missingThresholds(p: TradeProposal, d: PlanDraft): number {
  return [...p.entry_conditions, ...p.exit_conditions]
    .filter((c) => c.kind === 'numeric' && c.threshold == null && d.overrides[c.id]?.threshold == null).length;
}
