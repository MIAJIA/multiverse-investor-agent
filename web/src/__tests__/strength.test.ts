import { describe, expect, it } from 'vitest';
import fixture from '../../fixtures/c1.json';
import { nodeLabel } from '../node/labels';
import { strength } from '../node/strength';
import type { Fixture } from '../types';

const v1 = (fixture as unknown as Fixture).versions['c1-v1'];
const s = (id: string) => strength(v1.graph, id, v1.excerpts);

describe('证据符号计数', () => {
  it('正方 2 + 反方 1：两格绿、一格红', () => {
    expect(s('c1.laser_demand')).toMatchObject({ support: 2, contra: 1, neutral: 0, slots: ['support', 'support', 'contra'] });
  });
  it('一条引用：一格绿、两格空', () => {
    expect(s('c1.term.laser_vendor').slots).toEqual(['support', 'empty', 'empty']);
  });
  it('neutral 证据画灰格，不算正方也不算反方', () => {
    const g = structuredClone(v1.graph);
    const e3 = g.edges.find((e) => e.id === 'c1.e3')!;
    e3.evidence = [{ ...e3.evidence[0], excerpt_id: 'bg-1', stance: 'neutral', supports: '数据每周才更新' }];
    const r = strength(g, 'c1.laser_demand', v1.excerpts);
    expect(r).toMatchObject({ support: 1, contra: 1, neutral: 1, slots: ['support', 'contra', 'neutral'] });
  });
  it('仅模型推断与没有入边分开', () => {
    expect(s('c1.term.dsp_vendor')).toMatchObject({ modelOnly: true, noInEdges: false });
    expect(s('c1.event')).toMatchObject({ modelOnly: false, noInEdges: true });
  });
  it('短标题：有 label 用 label，没有（或空白）就截短 statement 到 10 个字', () => {
    expect(nodeLabel({ label: '光源需求上升', statement: '外置 CW 激光光源需求随 CPO 端口数上升' })).toBe('光源需求上升');
    expect(nodeLabel({ label: null, statement: '一二三四五六七八九十一二' })).toBe('一二三四五六七八九十…');
    expect(nodeLabel({ label: '  ', statement: '短句' })).toBe('短句');
    expect(nodeLabel({ label: null, statement: '十个字以内的话' })).toBe('十个字以内的话');
    expect(nodeLabel({ label: null, statement: 'Photonic chips are being adopted faster than expected' })).toBe('Photonic chips are being…');
    expect(nodeLabel({ label: null, statement: 'CPO switch shipments' })).toBe('CPO switch shipments');
  });
});
