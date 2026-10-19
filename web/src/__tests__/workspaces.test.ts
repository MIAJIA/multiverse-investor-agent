import { describe, expect, it } from 'vitest';
import {
  approvedOverview, createWorkspace, currentWorkspace, EMPTY_STORE, latestApproval, loadStore, recordApproval,
  recordVersion, saveStore, STORAGE_KEY, switchWorkspace, updateWorkspace, type KeyValueStorage,
} from '../workspaces';

function memory(initial: Record<string, string> = {}): KeyValueStorage & { data: Record<string, string> } {
  const data = { ...initial };
  return { data, getItem: (k) => data[k] ?? null, setItem: (k, v) => { data[k] = v; } };
}

describe('研究工作区', () => {
  it('新建：放在最前面并切过去，状态是分析中', () => {
    const a = createWorkspace(EMPTY_STORE, { event: 'Q1', online: false }, 1000);
    const b = createWorkspace(a.store, { event: 'Q2', online: true }, 2000);
    expect(b.store.workspaces.map((w) => w.event)).toEqual(['Q2', 'Q1']);
    expect(currentWorkspace(b.store)?.event).toBe('Q2');
    expect(b.workspace).toMatchObject({ status: 'analyzing', online: true, versions: [], runId: null });
    expect(a.workspace.id).not.toBe(b.workspace.id);
  });

  it('切换：切到已有的、切到「新建研究」空白页；不存在的 id 不动', () => {
    const a = createWorkspace(EMPTY_STORE, { event: 'Q1', online: false });
    const b = createWorkspace(a.store, { event: 'Q2', online: false });
    expect(currentWorkspace(switchWorkspace(b.store, a.workspace.id))?.event).toBe('Q1');
    expect(switchWorkspace(b.store, null).currentId).toBeNull();
    expect(switchWorkspace(b.store, 'nope').currentId).toBe(b.workspace.id);
  });

  it('版本只记在自己的工作区里，不会混到别的问题', () => {
    const a = createWorkspace(EMPTY_STORE, { event: 'Q1', online: false });
    const b = createWorkspace(a.store, { event: 'Q2', online: false });
    let s = updateWorkspace(b.store, a.workspace.id, { runId: 'run-1', status: 'ready' });
    s = recordVersion(s, a.workspace.id, 'r-v1', true);
    s = recordVersion(s, a.workspace.id, 'r-v2');
    s = recordVersion(s, a.workspace.id, 'r-v2'); // 重复的不再记
    const [q2, q1] = s.workspaces;
    expect(q1).toMatchObject({ versions: ['r-v1', 'r-v2'], baseVersion: 'r-v1' });
    expect(q2.versions).toEqual([]);
  });

  it('批准：记一条批准并把它的版本设为当前；撤销之后就没有已批准的', () => {
    const { store, workspace } = createWorkspace(EMPTY_STORE, { event: 'Q1', online: false });
    let s = recordApproval(store, workspace.id, { version: 'r-v2', terminalId: 't1', title: 'Brent falls · Brent', at: 5 });
    expect(s.workspaces[0]).toMatchObject({ baseVersion: 'r-v2', versions: ['r-v2'] });
    expect(latestApproval(s.workspaces[0])?.title).toBe('Brent falls · Brent');
    s = recordApproval(s, workspace.id, { version: 'r-v3', terminalId: null, title: null, at: 6 });
    expect(latestApproval(s.workspaces[0])).toBeNull();
    expect(s.workspaces[0].approvals).toHaveLength(2);
  });

  it('跨工作区的已批准计划总览：只列当前处于批准状态的，新的在前', () => {
    const a = createWorkspace(EMPTY_STORE, { event: 'Q1', online: false });
    const b = createWorkspace(a.store, { event: 'Q2', online: false });
    const c = createWorkspace(b.store, { event: 'Q3', online: false });
    let s = recordApproval(c.store, a.workspace.id, { version: 'v2', terminalId: 't', title: 'A', at: 10 });
    s = recordApproval(s, b.workspace.id, { version: 'v2', terminalId: 't', title: 'B', at: 20 });
    s = recordApproval(s, c.workspace.id, { version: 'v2', terminalId: 't', title: 'C', at: 30 });
    s = recordApproval(s, c.workspace.id, { version: 'v3', terminalId: null, title: null, at: 40 });
    expect(approvedOverview(s).map((x) => x.approval.title)).toEqual(['B', 'A']);
  });

  it('保存再读回：内容一样；上次还在分析中的读回来算失败（被打断）', () => {
    const storage = memory();
    const a = createWorkspace(EMPTY_STORE, { event: 'Q1', online: true, mockFixture: 'c1' }, 1000);
    let s = updateWorkspace(a.store, a.workspace.id, { runId: 'run-1', status: 'ready' });
    s = recordVersion(s, a.workspace.id, 'r-v1', true);
    const b = createWorkspace(s, { event: 'Q2', online: false }, 2000); // 这个还在分析中
    expect(saveStore(b.store, storage)).toBe(true);
    const back = loadStore(storage);
    expect(back.currentId).toBe(b.workspace.id);
    expect(back.workspaces[1]).toEqual(s.workspaces[0]);
    expect(back.workspaces[0]).toMatchObject({ event: 'Q2', status: 'failed', error: 'interrupted' });
  });

  it('坏掉的存储：空的、不是 JSON、结构不对、读写会抛错，都不让页面崩', () => {
    expect(loadStore(memory())).toEqual(EMPTY_STORE);
    expect(loadStore(memory({ [STORAGE_KEY]: '{not json' }))).toEqual(EMPTY_STORE);
    expect(loadStore(memory({ [STORAGE_KEY]: JSON.stringify({ workspaces: 'x', currentId: 3 }) }))).toEqual(EMPTY_STORE);
    // 一条好的、一条字段不对的：只留好的；currentId 指向不存在的就清掉
    const mixed = { workspaces: [{ id: 'w1', event: 'Q', createdAt: 1, status: 'ready', versions: ['v1', 7] }, { id: 2 }], currentId: 'gone' };
    const s = loadStore(memory({ [STORAGE_KEY]: JSON.stringify(mixed) }));
    expect(s.workspaces).toHaveLength(1);
    expect(s.workspaces[0]).toMatchObject({ id: 'w1', versions: ['v1'], approvals: [], runId: null });
    expect(s.currentId).toBeNull();
    const throwing: KeyValueStorage = { getItem: () => { throw new Error('blocked'); }, setItem: () => { throw new Error('full'); } };
    expect(loadStore(throwing)).toEqual(EMPTY_STORE);
    expect(saveStore(EMPTY_STORE, throwing)).toBe(false);
    expect(loadStore(null)).toEqual(EMPTY_STORE);
  });
});
