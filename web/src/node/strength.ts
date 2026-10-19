// 证据符号用的计数：只数快照里已有的引用条数，不算概率、不打分。
import { nodeEvidence } from '../lookup';
import type { Excerpt, Graph } from '../types';

export type Slot = 'support' | 'contra' | 'empty';

export interface Strength {
  support: number;
  contra: number;
  modelOnly: boolean; // 有入边，但全是 model_only、没有引用
  noInEdges: boolean; // 根节点：证据只挂在边上，这里没有
  slots: Slot[]; // 3 格：先放反方（红），再放正方（绿），其余空
}

export const SLOTS = 3;

export function strength(graph: Graph, nodeId: string, excerpts: Excerpt[]): Strength {
  const ev = nodeEvidence(graph, nodeId, excerpts);
  const support = ev.supporting.length;
  const contra = ev.contradicting.length;
  const red = Math.min(contra, SLOTS);
  const green = Math.min(support, SLOTS - red);
  const slots: Slot[] = [
    ...Array<Slot>(green).fill('support'),
    ...Array<Slot>(red).fill('contra'),
    ...Array<Slot>(SLOTS - green - red).fill('empty'),
  ];
  return { support, contra, modelOnly: ev.modelOnly, noInEdges: ev.inEdges.length === 0, slots };
}
