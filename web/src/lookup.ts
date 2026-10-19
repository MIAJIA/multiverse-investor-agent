// 只读查找：不做判断，只把快照里已有的东西按 id 找出来。
import type { Branch, Condition, EvidenceRef, Excerpt, Graph, Mechanism, Scenario, TradeProposal, VersionBundle } from './types';

export interface NodeEvidence {
  inEdges: Mechanism[];
  supporting: { ref: EvidenceRef; edge: Mechanism; excerpt?: Excerpt }[];
  contradicting: { ref: EvidenceRef; edge: Mechanism; excerpt?: Excerpt }[];
  background: { ref: EvidenceRef; edge: Mechanism; excerpt?: Excerpt }[]; // stance=neutral：背景信息，不算正反方
  /** 有入边，且入边全是 model_only、没有任何引用 */
  modelOnly: boolean;
}

/** 节点证据 = 它入边的 evidence，按 excerpt_id 关联资料包片段。 */
export function nodeEvidence(graph: Graph, nodeId: string, excerpts: Excerpt[]): NodeEvidence {
  const byId = new Map(excerpts.map((x) => [x.excerpt_id, x]));
  const inEdges = graph.edges.filter((e) => e.to === nodeId);
  const refs = inEdges.flatMap((edge) => edge.evidence.map((ref) => ({ ref, edge, excerpt: byId.get(ref.excerpt_id) })));
  return {
    inEdges,
    supporting: refs.filter((r) => r.ref.stance === 'supports'),
    contradicting: refs.filter((r) => r.ref.stance === 'contradicts'),
    background: refs.filter((r) => r.ref.stance === 'neutral'),
    modelOnly: inEdges.length > 0 && refs.length === 0 && inEdges.every((e) => e.model_only),
  };
}

export function nodeConditions(graph: Graph, nodeId: string): Condition[] {
  return graph.conditions.filter((c) => c.claim_id === nodeId);
}

/** key_dependency 是提案上的引用：直接指 claim，或指一个条件（取该条件的 claim_id）。 */
export function keyClaimId(proposal: TradeProposal | null | undefined, graph: Graph): string | null {
  const kd = proposal?.key_dependency;
  if (!kd) return null;
  if (kd.claim_id) return kd.claim_id;
  return graph.conditions.find((c) => c.id === kd.condition_id)?.claim_id ?? null;
}

/** 情景里被用户改动的目标（change_assumption 的 target）。只用于打角标。 */
export function changedTargets(scenario: Scenario | null | undefined): string[] {
  return (scenario?.ops ?? []).filter((o) => o.kind === 'change_assumption' && o.target).map((o) => o.target as string);
}

/** 一个节点的全部祖先（沿入边往上找）。B1 高亮整条分支用：分支 = 独有部分 + 它的祖先。只按边查找，不做判断。 */
export function ancestors(graph: Graph, id: string): Set<string> {
  const parents = new Map<string, string[]>();
  for (const e of graph.edges) parents.set(e.to, [...(parents.get(e.to) ?? []), e.from]);
  const seen = new Set<string>();
  const todo = [...(parents.get(id) ?? [])];
  while (todo.length) {
    const p = todo.pop()!;
    if (!seen.has(p)) {
      seen.add(p);
      todo.push(...(parents.get(p) ?? []));
    }
  }
  return seen;
}

/** 方案 B：按 terminal 找这一版本的计划和分支（按 terminal_id 关联，不依赖数组顺序）。 */
export function planOf(bundle: Pick<VersionBundle, 'proposals'>, terminalId: string | null | undefined): TradeProposal | null {
  return bundle.proposals.find((p) => p.terminal_id === terminalId) ?? null;
}

export function branchOf(bundle: Pick<VersionBundle, 'branches'>, terminalId: string | null | undefined): Branch | null {
  return bundle.branches.find((b) => b.terminal_id === terminalId) ?? null;
}

/** 几份计划各自的关键依赖落在哪个 claim 上（去重）。 */
export function keyClaimIds(bundle: Pick<VersionBundle, 'proposals' | 'graph'>): string[] {
  return [...new Set(bundle.proposals.map((p) => keyClaimId(p, bundle.graph)).filter((x): x is string => !!x))];
}

/** 这一版本已批准的那份计划（同一版本最多一份）。 */
export function approvedPlan(bundle: Pick<VersionBundle, 'proposals'>): TradeProposal | null {
  return bundle.proposals.find((p) => p.user_judgment.confirmed) ?? null;
}

const norm = (t: string | null | undefined) => (t ?? '').toLowerCase().split(/\s+/).filter(Boolean).join(' ').replace(/[ .\u3002!\uff01?\uff1f]+$/, ''); // 句末的中英文句号、叹号、问号

/** 重述用户自己输入事件的节点（original_statement 等于 graph.user_event，忽略大小写和空白）。
 *  和后端 branches.user_event_nodes 同一条规则：这类节点不算「尚未发生的假设」，横幅里不拿它当原因。 */
export function isUserEventNode(graph: Graph, nodeId: string): boolean {
  const want = norm(graph.user_event);
  const n = graph.nodes.find((x) => x.id === nodeId);
  return !!want && !!n && norm(n.original_statement) === want;
}
