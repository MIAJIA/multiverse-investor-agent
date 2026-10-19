// 只给 playground 用的演示短标题：fixture 还没有 label 字段时，让 A/B 对比看起来接近真实效果。
// 应用本身不用这张表，走 node/labels.ts 的 nodeLabel（有 label 用 label，没有就截短）。
import { nodeLabel } from '../node/labels';
import type { Claim } from '../types';

const DEMO_LABELS: Record<string, string> = {
  'c1.event': 'Photonics adopted early',
  'c1.assume.capex': 'Capex holds',
  'c1.assume.external_laser': 'External laser design',
  'c1.cpo_ramp': 'CPO ships early',
  'c1.laser_demand': 'Laser demand rises',
  'c1.siph_foundry': 'SiPh fab utilization up',
  'c1.pluggable_dsp': 'DSP demand slows',
  'c1.term.laser_vendor': 'Laser revenue beats',
  'c1.term.foundry': 'SiPh foundry share up',
  'c1.term.dsp_vendor': 'DSP business squeezed',
  'shock.siph_fab_outage': 'Foundry down a quarter',
};

export function demoLabel(claim: Claim, changed = false): string {
  if (claim.label) return nodeLabel(claim);
  if (changed && claim.id === 'c1.assume.external_laser') return 'Integrated lasers instead';
  return DEMO_LABELS[claim.id] ?? nodeLabel(claim);
}
