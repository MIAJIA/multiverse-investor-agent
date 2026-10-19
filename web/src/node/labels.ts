// 节点卡片上的短标题：后端给了 label（模型写、10 个汉字以内）就用它，没有就截短 statement。
import type { Claim } from '../types';

export const MAX_LABEL = 10;

export function truncate(text: string, max = MAX_LABEL): string {
  return text.length > max ? `${text.slice(0, max)}…` : text;
}

export function nodeLabel(claim: Pick<Claim, 'label' | 'statement'>): string {
  return claim.label?.trim() || truncate(claim.statement);
}
