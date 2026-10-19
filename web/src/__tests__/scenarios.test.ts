import { describe, expect, it } from 'vitest';
import fixture from '../../fixtures/c1_multi.json';
import {
  chain, cumulativeChallenged, cumulativeColoring, fullName, layerColoring, newChallenged, rootOf, scenarioIds,
} from '../scenarios/model';
import type { Fixture } from '../types';

const v = (fixture as unknown as Fixture).versions;
const lit = (a: Record<string, string>) => Object.entries(a).filter(([, s]) => s === 'challenged').map(([id]) => id).sort();

describe('多情景辅助', () => {
  it('版本链、根与名字', () => {
    expect(rootOf(v)).toBe('c1-v1');
    expect(scenarioIds(v)).toEqual(['c1-v2', 'c1-v3', 'c1-v4']);
    expect(chain(v, 'c1-v4')).toEqual(['c1-v1', 'c1-v2', 'c1-v4']);
    expect(v['c1-v4'].scenario!.root_version).toBe('c1-v1');
    expect(fullName(v, 'c1-v4')).toBe('Integrated lasers instead › + outage');
  });

  it('累计：直接用后端给的 scenario_ref.challenged_claim_ids（叠加后的全部）', () => {
    expect([...cumulativeChallenged(v['c1-v4'])].sort())
      .toEqual(['c1.laser_demand', 'c1.siph_foundry', 'c1.term.foundry', 'c1.term.laser_vendor']);
    expect(lit(cumulativeColoring(v, 'c1-v4').assessment))
      .toEqual(['c1.laser_demand', 'c1.siph_foundry', 'c1.term.foundry', 'c1.term.laser_vendor']);
    expect(cumulativeColoring(v, 'c1-v4').changed).toEqual(['c1.assume.external_laser']);
  });

  it('这一层新增：本版本减去父版本的受挑战集合', () => {
    expect(newChallenged(v, 'c1-v4').sort()).toEqual(['c1.siph_foundry', 'c1.term.foundry']);
    expect(newChallenged(v, 'c1-v2').sort()).toEqual(['c1.laser_demand', 'c1.term.laser_vendor']);
    expect(lit(layerColoring(v, 'c1-v4').assessment)).toEqual(['c1.siph_foundry', 'c1.term.foundry']);
    // 这一层是加冲击，没有改假设；父层改的假设不算这一层的
    expect(layerColoring(v, 'c1-v4').changed).toEqual([]);
  });

  it('集合差与后端 diff 一致：新增的受挑战节点都在本版本的 changed_claim_ids 里', () => {
    const changedIds = new Set(v['c1-v4'].diff!.changed_claim_ids);
    expect(newChallenged(v, 'c1-v4').every((id) => changedIds.has(id))).toBe(true);
  });
});
