// 只给 playground 用的演示短标题：fixture 还没有 label 字段时，让 A/B 对比看起来接近真实效果。
// 应用本身不用这张表，走 node/labels.ts 的 nodeLabel（有 label 用 label，没有就截短）。
import { nodeLabel } from '../node/labels';
import type { Claim } from '../types';

const DEMO_LABELS: Record<string, string> = {
  'c1.event': '光子芯片采用提前',
  'c1.assume.capex': '资本开支不下修',
  'c1.assume.external_laser': '外置光源架构',
  'c1.cpo_ramp': 'CPO 出货提前',
  'c1.laser_demand': '光源需求上升',
  'c1.siph_foundry': '硅光代工利用率升',
  'c1.pluggable_dsp': 'DSP 需求放缓',
  'c1.term.laser_vendor': '光源营收超预期',
  'c1.term.foundry': '硅光代工营收占比升',
  'c1.term.dsp_vendor': 'DSP 业务承压',
  'shock.siph_fab_outage': '代工厂停产一季',
};

export function demoLabel(claim: Claim, changed = false): string {
  if (claim.label) return nodeLabel(claim);
  if (changed && claim.id === 'c1.assume.external_laser') return '改用集成激光';
  return DEMO_LABELS[claim.id] ?? nodeLabel(claim);
}
