import { describe, expect, it } from 'vitest';
import c3 from '../../../eval/fixtures/c3_add_shock.json';
import { addShockOp, canLink, changeAssumptionOp, editedIds, freshCauseId, plainForkError } from '../edits';
import type { Graph, Scenario } from '../types';

const graph = {
  nodes: [{ id: 'a' }, { id: 'b' }, { id: 'user.cause.1' }],
  edges: [{ id: 'e1', from: 'a', to: 'b' }],
} as unknown as Graph;

describe('在图上改：请求体', () => {
  it('改节点 = change_assumption，target 是节点 id，value 去掉首尾空白', () => {
    expect(changeAssumptionOp('a', '  new text ')).toEqual({
      kind: 'change_assumption', target: 'a', value: 'new text', impacts: [], new_nodes: [], new_edges: [],
    });
  });

  it('加原因 = add_shock：新 shock 节点 + 从它连到每个受影响节点的边，带推高 / 压低', () => {
    const op = addShockOp('user.cause.2', ' Tariffs on optics ', [{ to: 'a', sign: '+' }, { to: 'b', sign: '-' }]);
    expect(op).toMatchObject({ kind: 'add_shock', target: 'user.cause.2', value: 'Tariffs on optics', impacts: ['a', 'b'] });
    expect(op.new_nodes).toEqual([{
      id: 'user.cause.2', role: 'shock', statement: 'Tariffs on optics', original_statement: 'Tariffs on optics',
      label: 'Tariffs on optics', evidence_status: 'unknown', time_bucket: null, instruments: [],
    }]);
    expect(op.new_edges.map((e) => [e.id, e.from, e.to, e.sign])).toEqual([
      ['user.cause.2.e1', 'user.cause.2', 'a', '+'], ['user.cause.2.e2', 'user.cause.2', 'b', '-'],
    ]);
    expect(op.new_edges[0]).toMatchObject({ channel: 'sentiment', lag_days: null, mechanism: 'User-added cause', evidence: [], model_only: true });
  });

  it('加原因的请求体字段和后端的 C3 样例一致（多出的只有 label、evidence）', () => {
    const op = addShockOp('x', 'y', [{ to: 'a', sign: '-' }]);
    expect(Object.keys(op).sort()).toEqual(Object.keys(c3.op).sort());
    expect(Object.keys(c3.op.new_nodes[0]).every((k) => k in op.new_nodes[0])).toBe(true);
    expect(Object.keys(c3.op.new_edges[0]).every((k) => k in op.new_edges[0])).toBe(true);
  });

  it('新原因的 id 不和图里已有的重复', () => {
    expect(freshCauseId(graph)).toBe('user.cause.2');
  });

  it('只能从草稿连到图里已有的节点，不能重复、不能反过来、不能连自己', () => {
    expect(canLink(graph, 'd', [], 'd', 'a')).toBe(true);
    expect(canLink(graph, 'd', [{ to: 'a', sign: '+' }], 'd', 'a')).toBe(false);
    expect(canLink(graph, 'd', [], 'a', 'b')).toBe(false); // 改连线：不支持
    expect(canLink(graph, 'd', [], 'a', 'd')).toBe(false);
    expect(canLink(graph, 'd', [], 'd', 'd')).toBe(false);
    expect(canLink(graph, 'd', [], 'd', 'nope')).toBe(false);
  });

  it('后端拒绝理由翻成白话中文，认不出的原样附上', () => {
    expect(plainForkError('[x] an id added by add_shock clashes with an existing object')).toMatch(/重复/);
    expect(plainForkError('[e] a Stage 1 edge must go from a new node to the impacts: a → b')).toMatch(/只能从它自己连/);
    expect(plainForkError('boom')).toContain('boom');
  });

  it('情景里用户动过的节点：改过的 + 加进来的原因', () => {
    const sc = { ops: [changeAssumptionOp('a', 'v'), addShockOp('user.cause.2', 't', [{ to: 'b', sign: '+' }])] } as Scenario;
    expect(editedIds(sc)).toEqual(['a', 'user.cause.2']);
    expect(editedIds(null)).toEqual([]);
  });
});

describe('B3 已去掉', () => {
  const app = Object.values(import.meta.glob('../App.tsx', { query: '?raw', import: 'default', eager: true }))[0] as string;
  const components = Object.keys(import.meta.glob('../components/*.tsx'));
  it('页签只有 B1 和 B2，没有单独的情景页和顶部的「假如…改成…」', () => {
    expect(app).toMatch(/const TABS[^\n]*\['workspace'[^\n]*\['signoff'[^\n]*\]\];/);
    expect(app).not.toMatch(/'scenario', T\.app\.tabs/);
    expect(components.some((p) => p.endsWith('/Scenario.tsx'))).toBe(false);
  });
});
