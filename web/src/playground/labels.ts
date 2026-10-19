// 短标题：只给 playground 演示用。正式做法是后端让模型给一个 `label` 字段、由校验器限制长度；
// 在那之前前端只能截断（shortLabel 的兜底分支）。
const DEMO_LABELS: Record<string, string> = {
  'c1.event': '光子芯片采用提前',
  'c1.assume.capex': '云厂商资本开支不下修',
  'c1.assume.external_laser': '外置光源架构',
  'c1.cpo_ramp': 'CPO 出货提前',
  'c1.laser_demand': '光源需求上升',
  'c1.siph_foundry': '硅光代工利用率上升',
  'c1.pluggable_dsp': '可插拔 DSP 需求放缓',
  'c1.term.laser_vendor': '光源营收超预期',
  'c1.term.foundry': '硅光代工营收占比上升',
  'c1.term.dsp_vendor': 'DSP 业务承压',
};

export const MAX_LABEL = 12;

export function shortLabel(id: string, statement: string, changed = false): string {
  if (changed && id === 'c1.assume.external_laser') return '改用集成激光';
  return DEMO_LABELS[id] ?? (statement.length > MAX_LABEL ? `${statement.slice(0, MAX_LABEL)}…` : statement);
}
