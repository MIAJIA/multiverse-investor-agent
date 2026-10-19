// 方案 B 视觉预览用的演示数据：在 c1_multi 的 c1-v3（加了「代工停产」冲击）上，手动指定分支、类别和三份计划。
// 这些本该由后端 branches.py 和 Inspect 第二步给出；后端交付后整份文件删掉，换成真实 fixture。
import type { Branch, BranchKind, Fixture, PlanBBundle, TradeProposal } from '../types';

export const DEMO_SUBTITLE = '光子芯片采用快于预期 + 情景「代工停产」';
export const DEMO_NOTE = '演示数据：分支、类别和 TSM / MRVL 两份计划是手动指定的，不是后端输出';

const OWN: Record<string, { kind: BranchKind; own: string[]; synthetic: boolean }> = {
  'c1.term.laser_vendor': { kind: 'evidenced', own: ['c1.assume.external_laser', 'c1.laser_demand', 'c1.term.laser_vendor'], synthetic: false },
  'c1.term.foundry': { kind: 'hypothetical', own: ['shock.siph_fab_outage', 'c1.siph_foundry', 'c1.term.foundry'], synthetic: false },
  'c1.term.dsp_vendor': { kind: 'model_only', own: ['c1.pluggable_dsp', 'c1.term.dsp_vendor'], synthetic: true },
};

export function demoBundle(fx: Fixture): PlanBBundle {
  const b = structuredClone(fx.versions['c1-v3']);
  const g = b.graph;
  const node_kinds: Record<string, BranchKind> = {};
  for (const n of g.nodes) node_kinds[n.id] = 'evidenced'; // 共用主干（事件、资本开支、CPO 出货）按 trunk = evidenced
  const branches: Branch[] = Object.entries(OWN).map(([terminal_id, { kind, own, synthetic }]) => {
    for (const id of own) node_kinds[id] = kind;
    return {
      terminal_id, kind, trunk: 'evidenced', synthetic_evidence: synthetic, divergence_node_ids: ['c1.cpo_ramp'],
      own_node_ids: own, own_edge_ids: g.edges.filter((e) => own.includes(e.to)).map((e) => e.id),
    };
  });
  const edge_kinds: Record<string, BranchKind> = {};
  for (const e of g.edges) edge_kinds[e.id] = node_kinds[e.to];

  const lite = b.proposal!;
  const cond = (id: string) => g.conditions.find((c) => c.id === id)!;
  const plan = (terminal_id: string, patch: Partial<TradeProposal>): TradeProposal => ({
    ...structuredClone(lite), ...patch, terminal_id, approval_reset: false, rival_changed: false,
    user_judgment: { ...lite.user_judgment, confirmed: false, confirmed_claim_ids: [], note: null },
    meta: { ...lite.meta, proposal_version: `${g.version}.${terminal_id}` },
  });
  const proposals = [
    plan('c1.term.laser_vendor', {}),
    plan('c1.term.foundry', {
      direction: { instrument: 'TSM', side: 'long', horizon_days: 270, note: '硅光代工营收占比随 CPO 量产上升' },
      entry_conditions: [cond('cond.c1.cpo_shipments'), cond('cond.c1.foundry_utilization')], exit_conditions: [],
      key_dependency: { claim_id: 'c1.siph_foundry', condition_id: null, why: '停产冲击直接打在代工利用率上：先确认停产是否发生、持续多久' },
      support_status: 'challenged',
    }),
    plan('c1.term.dsp_vendor', {
      direction: { instrument: 'MRVL', side: 'short', horizon_days: 365, note: '可插拔 DSP 需求被 CPO 替代' },
      entry_conditions: [cond('cond.c1.dsp_guidance')], exit_conditions: [cond('cond.c1.cpo_shipments')], exit_logic: 'ANY',
      key_dependency: { claim_id: 'c1.pluggable_dsp', condition_id: null, why: '替代关系只是模型推断，没有资料支撑' },
      support_status: 'unknown',
    }),
  ];
  return { graph: g, proposals, branches, node_kinds, edge_kinds, scenario: b.scenario, diff: b.diff, excerpts: b.excerpts };
}
