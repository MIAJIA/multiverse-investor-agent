import { describe, expect, it } from 'vitest';
import fixture from '../../fixtures/c1.json';
import { shortLabel } from '../playground/labels';
import { strength } from '../playground/strength';
import type { Fixture } from '../types';

const v1 = (fixture as unknown as Fixture).versions['c1-v1'];
const s = (id: string) => strength(v1.graph, id, v1.excerpts);

describe('证据符号计数', () => {
  it('正方 2 + 反方 1：两格绿、一格红', () => {
    expect(s('c1.laser_demand')).toMatchObject({ support: 2, contra: 1, slots: ['support', 'support', 'contra'] });
  });
  it('一条引用：一格绿、两格空', () => {
    expect(s('c1.term.laser_vendor').slots).toEqual(['support', 'empty', 'empty']);
  });
  it('仅模型推断与没有入边分开', () => {
    expect(s('c1.term.dsp_vendor')).toMatchObject({ modelOnly: true, noInEdges: false });
    expect(s('c1.event')).toMatchObject({ modelOnly: false, noInEdges: true });
  });
  it('短标题：没有演示标题时截断', () => {
    expect(shortLabel('x', '一二三四五六七八九十一二三四')).toBe('一二三四五六七八九十一二…');
    expect(shortLabel('c1.laser_demand', 'whatever')).toBe('光源需求上升');
  });
});
