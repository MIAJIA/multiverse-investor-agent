// 在 B1 图上直接改：两种 fork 操作的请求体，以及新原因能连到哪里。纯函数，后端仍然做最终校验。
// - 改节点：change_assumption，target = 节点 id，value = 新的说法
// - 加原因：add_shock，新建一个 shock 节点，只能从它连到已有节点（后端：新边必须从新节点连到声明的 impacts）
import { truncate } from './node/labels';
import { T } from './strings';
import type { Claim, Graph, Mechanism, Op, Scenario } from './types';

export type Sign = '+' | '-';
export interface DraftLink { to: string; sign: Sign }

export function changeAssumptionOp(target: string, value: string): Op {
  return { kind: 'change_assumption', target, value: value.trim(), impacts: [], new_nodes: [], new_edges: [] };
}

/** 新原因节点的 id：user.cause.<n>，跳过图里已有的（后端拒绝和已有对象重名的 id）。 */
export function freshCauseId(graph: Graph): string {
  const ids = new Set([...graph.nodes.map((n) => n.id), ...graph.edges.map((e) => e.id)]);
  let n = 1;
  while (ids.has(`user.cause.${n}`) || graph.edges.some((e) => e.id.startsWith(`user.cause.${n}.`))) n += 1;
  return `user.cause.${n}`;
}

/** 草稿原因能不能连到这个节点：只能从草稿连出去，连到图里已有的节点，不重复。删节点、插中间、改连线都不支持。 */
export function canLink(graph: Graph, draftId: string, links: DraftLink[], source: string | null, target: string | null): boolean {
  if (source !== draftId || !target || target === draftId) return false;
  return graph.nodes.some((n) => n.id === target) && !links.some((l) => l.to === target);
}

export function addShockOp(draftId: string, text: string, links: DraftLink[]): Op {
  const value = text.trim();
  const node: Claim = {
    id: draftId, role: 'shock', statement: value, original_statement: value, label: truncate(value),
    evidence_status: 'unknown', time_bucket: null, instruments: [],
  };
  const edges: Mechanism[] = links.map((l, i) => ({
    id: `${draftId}.e${i + 1}`, from: draftId, to: l.to, channel: 'sentiment', sign: l.sign, lag_days: null,
    mechanism: 'User-added cause', evidence: [], model_only: true,
  }));
  return { kind: 'add_shock', target: draftId, value, impacts: links.map((l) => l.to), new_nodes: [node], new_edges: edges };
}

/** 后端 fork 拒绝理由 → 白话中文；认不出的原样附在后面。 */
export function plainForkError(raw: string): string {
  const rules: [RegExp, string][] = [
    [/change_assumption target is not in the graph/, T.edit.err.target],
    [/add_shock impact is not in the graph/, T.edit.err.impact],
    [/clashes with an existing object/, T.edit.err.clash],
    [/Stage 1 edge must go from a new node/, T.edit.err.edge],
    [/not a fork operation/, T.edit.err.kind],
  ];
  const hit = rules.find(([re]) => re.test(raw));
  return hit ? hit[1] : T.edit.err.other(raw);
}

/** 情景里用户动过的节点：改过的节点和加进来的原因（叠加的情景会继承父情景的操作）。 */
export function editedIds(scenario: Scenario | null | undefined): string[] {
  return (scenario?.ops ?? []).flatMap((o) => (o.kind === 'add_shock' ? o.new_nodes.map((n) => n.id) : o.target ? [o.target] : []));
}
