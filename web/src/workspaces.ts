// 研究工作区：每个问题一个工作区，列表存在浏览器的 localStorage 里。
// 只存元数据（问题、运行编号、产生过的版本、当前版本、状态、批准记录）；图和计划本身都在后端，
// 用 GET /api/runs/{run_id}/versions/{v} 随时取回。localStorage 读写一律 try/catch：空的、被禁用的、内容坏掉的都不影响页面。

export type WorkspaceStatus = 'analyzing' | 'ready' | 'failed';

export interface Approval {
  version: string; // 批准后产生的版本
  terminalId: string | null; // null = 这一版本一份都不批准（撤销 / 不交易）
  title: string | null; // 批准时那份计划的标题（结论短标题 + 标的），方便列表里直接看
  at: number; // Date.now()
}

export interface Workspace {
  id: string;
  event: string; // 用户问的问题（原话）
  online: boolean; // 发起时联网开关是否打开
  createdAt: number;
  runId: string | null; // 后端的运行编号；分析完成前为空
  versions: string[]; // 这个工作区产生过的版本，按顺序
  baseVersion: string | null; // 当前看的版本（B1 / B2 的版本）
  status: WorkspaceStatus;
  error: string | null; // 失败原因（后端原话）
  note: string | null; // 没有图的结果：弃权或找不到因果链的理由
  approvals: Approval[];
  mockFixture: string | null; // MOCK 模式下用的是哪份 fixture（重新打开时要切回去）
}

export interface WorkspaceStore {
  workspaces: Workspace[]; // 新的在前
  currentId: string | null;
}

export const STORAGE_KEY = 'catalyst.workspaces.v1';
export const EMPTY_STORE: WorkspaceStore = { workspaces: [], currentId: null };

/** 和 window.localStorage 一样的最小接口；测试里换成假的。 */
export interface KeyValueStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

function defaultStorage(): KeyValueStorage | null {
  try {
    return typeof window !== 'undefined' ? window.localStorage : null;
  } catch {
    return null; // 被浏览器禁用时访问 localStorage 本身就会抛错
  }
}

const isStr = (v: unknown): v is string => typeof v === 'string';
const isStrOrNull = (v: unknown): v is string | null => v === null || typeof v === 'string';

function cleanApproval(a: unknown): Approval | null {
  if (!a || typeof a !== 'object') return null;
  const x = a as Record<string, unknown>;
  if (!isStr(x.version) || !isStrOrNull(x.terminalId) || typeof x.at !== 'number') return null;
  return { version: x.version, terminalId: x.terminalId, title: isStrOrNull(x.title) ? x.title : null, at: x.at };
}

/** 读回来的东西不可信：字段不对的工作区直接丢掉，缺的可选字段补默认值。 */
function cleanWorkspace(w: unknown): Workspace | null {
  if (!w || typeof w !== 'object') return null;
  const x = w as Record<string, unknown>;
  if (!isStr(x.id) || !isStr(x.event) || typeof x.createdAt !== 'number') return null;
  const status: WorkspaceStatus = x.status === 'ready' || x.status === 'failed' ? x.status : 'analyzing';
  return {
    id: x.id, event: x.event, online: x.online === true, createdAt: x.createdAt,
    runId: isStr(x.runId) ? x.runId : null,
    versions: Array.isArray(x.versions) ? x.versions.filter(isStr) : [],
    baseVersion: isStr(x.baseVersion) ? x.baseVersion : null,
    // 上次关页面时还在分析的，回来时已经没有请求在等了，按失败处理（运行可能已经在后端完成，但前端拿不到它的编号）
    status: status === 'analyzing' ? 'failed' : status,
    error: status === 'analyzing' ? 'interrupted' : isStrOrNull(x.error) ? x.error : null,
    note: isStrOrNull(x.note) ? x.note : null,
    approvals: Array.isArray(x.approvals) ? x.approvals.map(cleanApproval).filter((a): a is Approval => !!a) : [],
    mockFixture: isStr(x.mockFixture) ? x.mockFixture : null,
  };
}

export function loadStore(storage: KeyValueStorage | null = defaultStorage()): WorkspaceStore {
  try {
    const raw = storage?.getItem(STORAGE_KEY);
    if (!raw) return EMPTY_STORE;
    const data = JSON.parse(raw) as { workspaces?: unknown; currentId?: unknown };
    const workspaces = Array.isArray(data.workspaces)
      ? data.workspaces.map(cleanWorkspace).filter((w): w is Workspace => !!w) : [];
    const currentId = isStr(data.currentId) && workspaces.some((w) => w.id === data.currentId) ? data.currentId : null;
    return { workspaces, currentId };
  } catch {
    return EMPTY_STORE; // 坏掉的 JSON：当作没有，不让页面崩
  }
}

export function saveStore(store: WorkspaceStore, storage: KeyValueStorage | null = defaultStorage()): boolean {
  try {
    storage?.setItem(STORAGE_KEY, JSON.stringify(store));
    return !!storage;
  } catch {
    return false; // 存满或被禁用：这次不记住，页面照常用
  }
}

let seq = 0;
function newId(now: number): string {
  seq += 1;
  return `ws-${now.toString(36)}-${seq.toString(36)}-${Math.random().toString(36).slice(2, 6)}`;
}

/** 新开一个问题：放在列表最前面，并切过去。 */
export function createWorkspace(store: WorkspaceStore, input: { event: string; online: boolean; mockFixture?: string | null },
  now = Date.now()): { store: WorkspaceStore; workspace: Workspace } {
  const workspace: Workspace = {
    id: newId(now), event: input.event, online: input.online, createdAt: now, runId: null, versions: [],
    baseVersion: null, status: 'analyzing', error: null, note: null, approvals: [], mockFixture: input.mockFixture ?? null,
  };
  return { store: { workspaces: [workspace, ...store.workspaces], currentId: workspace.id }, workspace };
}

/** 把一个已经建好的工作区放到最前面并切过去（React 的 setState 更新函数可能跑两次，id 要在外面先定好）。 */
export function addWorkspace(store: WorkspaceStore, workspace: Workspace): WorkspaceStore {
  return { workspaces: [workspace, ...store.workspaces.filter((w) => w.id !== workspace.id)], currentId: workspace.id };
}

export function updateWorkspace(store: WorkspaceStore, id: string, patch: Partial<Workspace>): WorkspaceStore {
  return { ...store, workspaces: store.workspaces.map((w) => (w.id === id ? { ...w, ...patch } : w)) };
}

/** 切换到某个工作区；null = 「新建研究」的空白页。 */
export function switchWorkspace(store: WorkspaceStore, id: string | null): WorkspaceStore {
  return { ...store, currentId: id === null || store.workspaces.some((w) => w.id === id) ? id : store.currentId };
}

/** 记一个新版本；setBase 为 true 时它同时成为当前版本（批准、在情景版本上重新批准）。 */
export function recordVersion(store: WorkspaceStore, id: string, version: string, setBase = false): WorkspaceStore {
  return {
    ...store,
    workspaces: store.workspaces.map((w) => (w.id !== id ? w : {
      ...w, versions: w.versions.includes(version) ? w.versions : [...w.versions, version],
      baseVersion: setBase ? version : w.baseVersion,
    })),
  };
}

export function recordApproval(store: WorkspaceStore, id: string, approval: Approval): WorkspaceStore {
  const s = recordVersion(store, id, approval.version, true);
  return { ...s, workspaces: s.workspaces.map((w) => (w.id === id ? { ...w, approvals: [...w.approvals, approval] } : w)) };
}

export function currentWorkspace(store: WorkspaceStore): Workspace | null {
  return store.workspaces.find((w) => w.id === store.currentId) ?? null;
}

/** 这个工作区现在批准的是哪份：最后一条批准记录；撤销（terminalId 为 null）之后就是没有。 */
export function latestApproval(w: Workspace): Approval | null {
  const a = w.approvals.at(-1);
  return a && a.terminalId ? a : null;
}

/** 所有工作区里目前处于批准状态的计划，新的在前。 */
export function approvedOverview(store: WorkspaceStore): { workspace: Workspace; approval: Approval }[] {
  return store.workspaces
    .map((workspace) => ({ workspace, approval: latestApproval(workspace) }))
    .filter((x): x is { workspace: Workspace; approval: Approval } => !!x.approval)
    .sort((a, b) => b.approval.at - a.approval.at);
}
