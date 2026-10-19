// 证据符号用的计数：只数快照里已有的引用条数，不算概率、不打分。
import { nodeEvidence } from '../lookup';
import type { Excerpt, Graph } from '../types';

export type Slot = 'support' | 'contra' | 'neutral' | 'empty';

export interface Strength {
  support: number;
  contra: number;
  neutral: number; // 背景信息：圆环上画灰格，不算正方也不算反方
  modelOnly: boolean; // 有入边，但全是 model_only、没有引用
  noInEdges: boolean; // 根节点：证据只挂在边上，这里没有
  slots: Slot[]; // 3 格：正方（绿）、反方（红）、背景（灰），其余空；反方优先占格
}

export const SLOTS = 3;

export function strength(graph: Graph, nodeId: string, excerpts: Excerpt[]): Strength {
  const ev = nodeEvidence(graph, nodeId, excerpts);
  const support = ev.supporting.length;
  const contra = ev.contradicting.length;
  const neutral = ev.background.length;
  const red = Math.min(contra, SLOTS);
  const green = Math.min(support, SLOTS - red);
  const grey = Math.min(neutral, SLOTS - red - green);
  const slots: Slot[] = [
    ...Array<Slot>(green).fill('support'),
    ...Array<Slot>(red).fill('contra'),
    ...Array<Slot>(grey).fill('neutral'),
    ...Array<Slot>(SLOTS - green - red - grey).fill('empty'),
  ];
  return { support, contra, neutral, modelOnly: ev.modelOnly, noInEdges: ev.inEdges.length === 0, slots };
}
