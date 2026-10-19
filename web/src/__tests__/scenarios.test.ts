import { describe, expect, it } from 'vitest';
import fixture from '../../fixtures/c1_multi.json';
import { chain, challenged, cumulativeColoring, fullName, relativeColoring, rootOf, scenarioIds } from '../scenarios/model';
import type { Fixture } from '../types';

const v = (fixture as unknown as Fixture).versions;

describe('多情景辅助', () => {
  it('版本链与根', () => {
    expect(rootOf(v)).toBe('c1-v1');
    expect(scenarioIds(v)).toEqual(['c1-v2', 'c1-v3', 'c1-v4']);
    expect(chain(v, 'c1-v4')).toEqual(['c1-v1', 'c1-v2', 'c1-v4']);
    expect(fullName(v, 'c1-v4')).toBe('改用集成激光 › + 停产');
  });
  it('相对上一层：只用后端给的这一层', () => {
    expect(Object.entries(relativeColoring(v['c1-v4']).assessment).filter(([, s]) => s === 'challenged').map(([id]) => id).sort())
      .toEqual(['c1.siph_foundry', 'c1.term.foundry']);
  });
  it('累计：链上每层的 challenged 合起来，改动的假设也带上', () => {
    const c = cumulativeColoring(v, 'c1-v4');
    expect(Object.entries(c.assessment).filter(([, s]) => s === 'challenged').map(([id]) => id).sort())
      .toEqual(['c1.laser_demand', 'c1.siph_foundry', 'c1.term.foundry', 'c1.term.laser_vendor']);
    expect(c.changed).toEqual(['c1.assume.external_laser']);
    expect(challenged(v['c1-v2']).sort()).toEqual(['c1.laser_demand', 'c1.term.laser_vendor']);
  });
});
