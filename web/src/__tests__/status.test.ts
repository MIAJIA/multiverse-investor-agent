import { describe, expect, it } from 'vitest';
import * as S from '../status';
import * as T from '../types';

const TABLES: [string, readonly string[], Record<string, S.Look>][] = [
  ['ROLE', T.ROLES, S.ROLE],
  ['EVIDENCE', T.EVIDENCE_STATUSES, S.EVIDENCE],
  ['ASSESSMENT', T.ASSESSMENT_STATUSES, S.ASSESSMENT],
  ['GATE', T.GATES, S.GATE],
  ['PROPOSAL_STATUS', T.PROPOSAL_STATUSES, S.PROPOSAL_STATUS],
  ['SUPPORT', T.SUPPORT_STATUSES, S.SUPPORT],
  ['VERIFICATION', T.VERIFICATION_STATUSES, S.VERIFICATION],
  ['EVALUATION', T.EVALUATION_STATUSES, S.EVALUATION],
  ['EXIT_LOGIC', T.EXIT_LOGICS, S.EXIT_LOGIC],
  ['CRITIC', T.CRITIC_STATUSES, S.CRITIC],
  ['BRANCH_KIND', T.BRANCH_KINDS, S.BRANCH_KIND],
];

describe('status 映射', () => {
  it.each(TABLES)('%s 覆盖每个取值，且只覆盖这些取值', (_name, values, table) => {
    expect(Object.keys(table).sort()).toEqual([...values].sort());
    for (const v of values) {
      expect(table[v].label.length).toBeGreaterThan(0);
      expect(table[v].color).toMatch(/^#/);
      expect(table[v].bg).toMatch(/^#/);
    }
  });

  it('gate 没有执行类文案', () => {
    for (const look of Object.values(S.GATE)) expect(look.label).not.toMatch(/execute|order|执行|下单/i);
  });

  it('status 和 gate 是两张表，文案不重叠', () => {
    const a = Object.values(S.PROPOSAL_STATUS).map((l) => l.label);
    const b = Object.values(S.GATE).map((l) => l.label);
    expect(a.filter((x) => b.includes(x))).toEqual([]);
  });

  it('exit_logic 显式写出或 / 且', () => {
    expect(S.EXIT_LOGIC.ANY.label).toContain('OR');
    expect(S.EXIT_LOGIC.ALL.label).toContain('AND');
  });

  it('三态着色：challenged 橙、unresolved 虚线', () => {
    expect(S.ASSESSMENT.challenged.color).toBe(S.ROLE.shock.color);
    expect(S.ASSESSMENT.unresolved.border).toBe('dashed');
  });

  it('三类分支：线型各不相同，假设分支有底纹和「Assumed · not observed」标签，有资料的默认不加字', () => {
    const k = S.BRANCH_KIND;
    expect(new Set([k.evidenced.line, k.model_only.line, k.hypothetical.line]).size).toBe(3);
    expect(k.hypothetical.tag).toBe('Assumed · not observed');
    expect(k.hypothetical.pattern).toContain('repeating-linear-gradient');
    expect(k.evidenced.tag).toBeNull();
    expect(k.model_only.dash).toBeTruthy();
  });
});
