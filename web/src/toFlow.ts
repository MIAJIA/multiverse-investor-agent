// 快照 → React Flow 的 nodes / edges。纯函数：不改输入，不存状态；坐标按节点深度算（不做自动布局）。
import type { Edge, Node } from '@xyflow/react';
import type { AssessmentStatus, Claim, Graph, Mechanism } from './types';
import { T } from './strings';

export interface ClaimNodeData extends Record<string, unknown> {
  claim: Claim;
  evidenceCount: number;
  isKey: boolean;
  isChangedTarget: boolean;
  assessment?: AssessmentStatus;
}

export interface MechanismEdgeData extends Record<string, unknown> {
  edge: Mechanism;
  modelOnly: boolean;
}

export interface FlowOpts {
  keyClaimId?: string | null;
  assessment?: Record<string, AssessmentStatus>;
  changedTargets?: string[];
}

export const COL_W = 260;
export const ROW_H = 170;

/** 每个节点的深度 = 从任一根节点出发的最长路径长度。有环时环上的节点停在已算出的深度。 */
export function depths(graph: Graph): Map<string, number> {
  const ids = new Set(graph.nodes.map((n) => n.id));
  const parents = new Map<string, string[]>();
  for (const e of graph.edges) {
    if (ids.has(e.from) && ids.has(e.to)) parents.set(e.to, [...(parents.get(e.to) ?? []), e.from]);
  }
  const memo = new Map<string, number>();
  const visiting = new Set<string>();
  const depth = (id: string): number => {
    if (memo.has(id)) return memo.get(id)!;
    if (visiting.has(id)) return 0;
    visiting.add(id);
    const d = Math.max(-1, ...(parents.get(id) ?? []).map(depth)) + 1;
    visiting.delete(id);
    memo.set(id, d);
    return d;
  };
  graph.nodes.forEach((n) => depth(n.id));
  return memo;
}

export function toFlow(graph: Graph, opts: FlowOpts = {}) {
  const ids = new Set(graph.nodes.map((n) => n.id));
  const warnings = graph.edges
    .filter((e) => !ids.has(e.from) || !ids.has(e.to))
    .map((e) => T.graph.danglingEdge(e.id, e.from, e.to));
  const validEdges = graph.edges.filter((e) => ids.has(e.from) && ids.has(e.to));
  const d = depths(graph);

  const layers = new Map<number, Claim[]>();
  for (const n of graph.nodes) layers.set(d.get(n.id)!, [...(layers.get(d.get(n.id)!) ?? []), n]);
  const widest = Math.max(1, ...[...layers.values()].map((l) => l.length));

  const evidenceCount = new Map<string, number>();
  for (const e of validEdges) evidenceCount.set(e.to, (evidenceCount.get(e.to) ?? 0) + e.evidence.length);

  const nodes: Node<ClaimNodeData>[] = graph.nodes.map((claim) => {
    const depth = d.get(claim.id)!;
    const layer = layers.get(depth)!;
    const offset = ((widest - layer.length) * COL_W) / 2; // 每层居中
    return {
      id: claim.id,
      type: 'claim',
      position: { x: offset + layer.indexOf(claim) * COL_W, y: depth * ROW_H },
      data: {
        claim,
        evidenceCount: evidenceCount.get(claim.id) ?? 0,
        isKey: opts.keyClaimId === claim.id,
        isChangedTarget: (opts.changedTargets ?? []).includes(claim.id),
        assessment: opts.assessment?.[claim.id],
      },
    };
  });

  const edges: Edge<MechanismEdgeData>[] = validEdges.map((edge) => ({
    id: edge.id,
    source: edge.from,
    target: edge.to,
    label: `${edge.channel} ${edge.sign}`,
    style: edge.model_only ? { strokeDasharray: '6 4' } : undefined,
    data: { edge, modelOnly: edge.model_only },
  }));

  return { nodes, edges, warnings };
}
