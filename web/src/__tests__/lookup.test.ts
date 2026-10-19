import { describe, expect, it } from 'vitest';
import fixture from '../../fixtures/c1.json';
import { nodeConditions, nodeEvidence } from '../lookup';
import type { Fixture } from '../types';

const v1 = (fixture as unknown as Fixture).versions['c1-v1'];

describe('lookup', () => {
  it('节点证据 = 入边 evidence，按 stance 分栈并带片段原文', () => {
    const ev = nodeEvidence(v1.graph, 'c1.laser_demand', v1.excerpts);
    expect(ev.inEdges.map((e) => e.id).sort()).toEqual(['c1.e3', 'c1.e4']);
    expect(ev.supporting.map((r) => r.ref.excerpt_id).sort()).toEqual(['sc-003', 'sc-004']);
    expect(ev.contradicting.map((r) => r.ref.excerpt_id)).toEqual(['sc-005']);
    expect(ev.contradicting[0].ref.rebuttal).toBeTruthy();
    expect(ev.supporting.every((r) => r.excerpt?.text)).toBe(true);
    expect(ev.modelOnly).toBe(false);
  });

  it('入边全是 model_only → modelOnly；没有入边 → inEdges 为空', () => {
    expect(nodeEvidence(v1.graph, 'c1.term.dsp_vendor', v1.excerpts).modelOnly).toBe(true);
    const root = nodeEvidence(v1.graph, 'c1.event', v1.excerpts);
    expect(root.inEdges).toEqual([]);
    expect(root.modelOnly).toBe(false);
  });

  it('neutral 证据单独成「背景」一组', () => {
    const g = structuredClone(v1.graph);
    const e3 = g.edges.find((e) => e.id === 'c1.e3')!;
    e3.evidence = [...e3.evidence, { ...e3.evidence[0], excerpt_id: 'bg-1', stance: 'neutral', supports: '数据每周才更新' }];
    const ev = nodeEvidence(g, 'c1.laser_demand', v1.excerpts);
    expect([ev.supporting.length, ev.contradicting.length, ev.background.length]).toEqual([2, 1, 1]);
  });

  it('节点上的条件', () => {
    expect(nodeConditions(v1.graph, 'c1.laser_demand').map((c) => c.id)).toEqual(['cond.c1.els_design_wins']);
  });
});
