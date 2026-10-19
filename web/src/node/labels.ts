// 节点卡片上的短标题：后端给了 label（模型写、10 个汉字或 4 个英文词以内）就用它，没有就截短 statement：
// 中文截 10 个字，英文（基本是 ASCII 的句子）截前 4 个词。
import type { Claim } from '../types';

export const MAX_LABEL = 10;
export const MAX_WORDS = 4;

export function truncate(text: string, max = MAX_LABEL): string {
  const latin = text.length > 0 && [...text].filter((ch) => ch.charCodeAt(0) < 128).length / text.length > 0.8;
  if (latin) {
    const words = text.trim().split(/\s+/);
    return words.length > MAX_WORDS ? `${words.slice(0, MAX_WORDS).join(' ').replace(/[,;:.]$/, '')}…` : text;
  }
  return text.length > max ? `${text.slice(0, max)}…` : text;
}

export function nodeLabel(claim: Pick<Claim, 'label' | 'statement'>): string {
  return claim.label?.trim() || truncate(claim.statement);
}
