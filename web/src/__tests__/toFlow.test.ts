import { describe, expect, it } from 'vitest';
import fixture from '../../fixtures/c1.json';
import { changedTargets, keyClaimId } from '../lookup';
import { depths, toFlow } from '../toFlow';
import type { Fixture, Graph, TradeProposal } from '../types';

const fx = fixture as unknown as Fixture;
const v1 = fx.versions['c1-v1'];
const v2 = fx.versions['c1-v2'];

describe('toFlow', () => {
  it('节点、边与图一一对应', () => {
    const { nodes, edges, warnings } = toFlow(v1.graph);
    expect(nodes.map((n) => n.id).sort()).toEqual(v1.graph.nodes.map((n) => n.id).sort());
    expect(nodes).toHaveLength(10);
    expect(edges).toHaveLength(9);
    expect(warnings).toEqual([]);
  });

  it('深度取最长路径，同层 y 相同、x 不重叠', () => {
    const d = depths(v1.graph);
    expect(['c1.event', 'c1.assume.capex', 'c1.assume.external_laser'].map((id) => d.get(id))).toEqual([0, 0, 0]);
    expect(d.get('c1.cpo_ramp')).toBe(1);
    expect(['c1.laser_demand', 'c1.siph_foundry', 'c1.pluggable_dsp'].map((id) => d.get(id))).toEqual([2, 2, 2]);
    expect(['c1.term.laser_vendor', 'c1.term.foundry', 'c1.term.dsp_vendor'].map((id) => d.get(id))).toEqual([3, 3, 3]);
    const { nodes } = toFlow(v1.graph);
    for (const depth of [0, 1, 2, 3]) {
      const layer = nodes.filter((n) => d.get(n.id) === depth);
      expect(new Set(layer.map((n) => n.position.y)).size).toBe(1);
      expect(new Set(layer.map((n) => n.position.x)).size).toBe(layer.length);
    }
  });

  it('边的 source 来自 schema 的 from；model_only 画虚线', () => {
    const { edges } = toFlow(v1.graph);
    const e1 = edges.find((e) => e.id === 'c1.e1')!;
    expect([e1.source, e1.target]).toEqual(['c1.event', 'c1.cpo_ramp']);
    expect(edges.filter((e) => e.data!.modelOnly).map((e) => e.id).sort()).toEqual(['c1.e6', 'c1.e9']);
  });

  it('关键依赖：claim_id 形式和 condition_id 形式都能解析', () => {
    const k = keyClaimId(v1.proposal, v1.graph);
    expect(k).toBe('c1.assume.external_laser');
    const { nodes } = toFlow(v1.graph, { keyClaimId: k });
    expect(nodes.filter((n) => n.data.isKey).map((n) => n.id)).toEqual(['c1.assume.external_laser']);
    const viaCondition = {
      ...v1.proposal!,
      key_dependency: { claim_id: null, condition_id: 'cond.c1.cpo_shipments', why: 'x' },
    } as TradeProposal;
    expect(keyClaimId(viaCondition, v1.graph)).toBe('c1.cpo_ramp');
  });

  it('情景：assessment 原样着色，改动的假设单独标注', () => {
    const plain = toFlow(v1.graph);
    expect(plain.nodes.every((n) => n.data.assessment === undefined)).toBe(true);
    const { nodes } = toFlow(v2.graph, { assessment: v2.scenario!.assessment, changedTargets: changedTargets(v2.scenario) });
    expect(nodes.filter((n) => n.data.assessment === 'challenged').map((n) => n.id).sort())
      .toEqual(['c1.laser_demand', 'c1.term.laser_vendor']);
    expect(nodes.filter((n) => n.data.assessment === 'unaffected')).toHaveLength(8);
    expect(nodes.filter((n) => n.data.isChangedTarget).map((n) => n.id)).toEqual(['c1.assume.external_laser']);
  });

  it('不改输入', () => {
    const before = JSON.stringify(v2.graph);
    toFlow(v2.graph, { assessment: v2.scenario!.assessment, keyClaimId: 'c1.cpo_ramp' });
    expect(JSON.stringify(v2.graph)).toBe(before);
  });

  it('悬空边不崩：忽略并给 warning', () => {
    const g: Graph = { ...v1.graph, edges: [...v1.graph.edges, { ...v1.graph.edges[0], id: 'bad', to: 'nope' }] };
    const { edges, warnings } = toFlow(g);
    expect(edges).toHaveLength(9);
    expect(warnings).toHaveLength(1);
  });
});
