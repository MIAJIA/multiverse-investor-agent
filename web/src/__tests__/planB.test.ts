// 方案 B：计划按 terminal、关键依赖、分支高亮、后端写的失效字段，以及 MOCK 的批准 / 撤销 / 分叉。
import { describe, expect, it } from 'vitest';
import approvedFx from '../../fixtures/c1_approved.json';
import c1Fx from '../../fixtures/c1.json';
import * as api from '../api';
import { branchViewOf } from '../components/Workspace';
import { approvedPlan, isUserEventNode, keyClaimIds, planOf } from '../lookup';
import type { Fixture } from '../types';

const c1 = (c1Fx as unknown as Fixture).versions;
const ap = (approvedFx as unknown as Fixture).versions;
const LITE = 'c1.term.laser_vendor';
const TSM = 'c1.term.foundry';

describe('方案 B 的版本包', () => {
  it('每个结论一份计划，和分支一一对应', () => {
    const v1 = c1['c1-v1'];
    expect(v1.proposals.map((p) => p.terminal_id).sort()).toEqual(v1.branches.map((b) => b.terminal_id).sort());
    expect(planOf(v1, TSM)?.direction.instrument).toBe('TSM');
    expect(approvedPlan(v1)).toBeNull();
  });

  it('关键依赖：claim 形式和条件形式都落到 claim 上', () => {
    expect(keyClaimIds(c1['c1-v1']).sort()).toEqual(['c1.assume.external_laser', 'c1.pluggable_dsp', 'c1.siph_foundry']);
  });

  it('改假设后 LITE 分支变成假设类（后端给的类别表）', () => {
    expect(c1['c1-v1'].branches.find((b) => b.terminal_id === LITE)!.kind).toBe('model_only');
    expect(c1['c1-v2'].branches.find((b) => b.terminal_id === LITE)!.kind).toBe('hypothetical');
    expect(c1['c1-v2'].node_kinds['c1.assume.external_laser']).toBe('hypothetical');
  });

  it('B1 高亮：选中结论的独有部分 + 全部祖先', () => {
    const v = branchViewOf(c1['c1-v1'], LITE);
    expect([...v.highlight!.nodes].sort()).toEqual(
      ['c1.assume.capex', 'c1.assume.external_laser', 'c1.cpo_ramp', 'c1.event', 'c1.laser_demand', 'c1.term.laser_vendor']);
    expect(v.highlight!.nodes.has('c1.siph_foundry')).toBe(false);
    expect(branchViewOf(c1['c1-v1'], null).highlight).toBeNull();
  });

  it('批准后改假设：受影响的计划 approval_reset，其余 rival_changed（只读后端字段）', () => {
    expect(approvedPlan(ap['c1-v2'])?.terminal_id).toBe(LITE);
    const after = ap['c1-v3'];
    expect(planOf(after, LITE)).toMatchObject({ approval_reset: true, user_judgment: { confirmed: false } });
    expect(planOf(after, TSM)).toMatchObject({ approval_reset: false, rival_changed: true });
    // 批准的是 TSM 时改同一处：TSM 不受影响，保留批准
    expect(planOf(ap['c1-v5'], TSM)).toMatchObject({ user_judgment: { confirmed: true }, rival_changed: true });
  });
});

describe('用户自己的事件', () => {
  it('重述 user_event 的节点被认出来（忽略大小写和句末标点）', () => {
    const g = structuredClone(c1['c1-v1'].graph);
    g.user_event = 'photonic chips are being adopted FASTER than expected.';
    g.nodes[0].original_statement = 'Photonic chips are being adopted faster than expected';
    expect(isUserEventNode(g, g.nodes[0].id)).toBe(true);
    expect(isUserEventNode(g, g.nodes[1].id)).toBe(false);
  });
});

describe('MOCK 的批准 / 撤销 / 分叉', () => {
  it('批准优先用 fixture 里录好的版本；撤销没录到时在内存里改', async () => {
    api.setMockFixture('c1_approved');
    await api.createRun({ event: 'x' });
    expect((await api.sign('mock', { version: 'c1-v1', terminal_id: TSM, confirmed_claim_ids: [], condition_overrides: {} })).version)
      .toBe('c1-v4');
    const r = await api.sign('mock', { version: 'c1-v2', terminal_id: null, confirmed_claim_ids: [], condition_overrides: {} });
    expect(r.version).toBe('c1-v2');
    expect(approvedPlan(await api.getVersion('mock', 'c1-v2'))).toBeNull();
  });

  it('分叉按「从哪个版本出发」找录好的版本', async () => {
    api.setMockFixture('c1_approved');
    await api.createRun({ event: 'x' });
    const op = { kind: 'change_assumption' as const, target: 'c1.assume.external_laser', value: 'x', impacts: [], new_nodes: [], new_edges: [] };
    expect((await api.fork('mock', { base_version: 'c1-v2', op })).version).toBe('c1-v3');
    expect((await api.fork('mock', { base_version: 'c1-v4', op })).version).toBe('c1-v5');
    expect((await api.fork('mock', { base_version: 'c1-v1', op: { ...op, target: 'c1.assume.capex' } })).ok).toBe(false);
  });
});
