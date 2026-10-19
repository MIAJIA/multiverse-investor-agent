// 页面的 state 分两层：
// - 研究工作区（workspaces.ts，存在 localStorage）：每个问题一个工作区，记着运行编号、版本、批准历史；
// - 当前工作区的视图（AppState）：从后端取回的版本快照、选中的结论、草稿……切换工作区时整份重置，不同问题的版本不会混在一起。
// 所有后端调用都从这里发；写操作之后按返回的版本号重新取快照，并把版本 / 批准记进发起它的那个工作区。
import { useEffect, useRef, useState } from 'react';
import * as api from './api';
import ApproveCard from './components/approve/ApproveCard';
import { EMPTY_DRAFT, type PlanDraft, type Understood } from './components/approve/model';
import BusyHint, { type BusyKind } from './components/BusyHint';
import Scenario from './components/Scenario';
import Workspace from './components/Workspace';
import WorkspaceSidebar from './components/WorkspaceSidebar';
import { planOf } from './lookup';
import { nodeLabel } from './node/labels';
import type { RunCreated, VersionBundle, WriteResult } from './types';
import { T } from './strings';
import {
  addWorkspace, createWorkspace, currentWorkspace, EMPTY_STORE, loadStore, recordApproval, recordVersion, saveStore,
  switchWorkspace, updateWorkspace, type Workspace as Ws, type WorkspaceStore,
} from './workspaces';

type Tab = 'workspace' | 'signoff' | 'scenario';

export interface AppState {
  runId: string | null;
  versions: Record<string, VersionBundle>; // 当前工作区从后端取回的快照，按版本号存
  baseVersion: string | null; // B1 / B2 看的版本，也是 fork 的 base_version
  scenarioVersion: string | null; // 最近一次 fork 产出的版本
  viewing: 'base' | 'scenario';
  tab: Tab;
  selectedNodeId: string | null;
  selectedTerminalId: string | null; // B1 高亮的结论 = B2 选中的那一行
  understood: Understood; // 「你的想法」确认；同一个工作区里一直有效
  drafts: Record<string, PlanDraft>; // 按 terminal 存还没提交的输入；当前版本变了就清空
  busy: boolean; // 正在等改假设 / 批准（分析的等待看工作区状态）
  errors: string[] | null; // 后端 / 校验器的拒绝理由，原样显示
  notices: string[] | null;
  runNote: string | null; // 没有图的运行：弃权或找不到因果链的理由（后端原话）
  webMessage: string | null; // 建 run 时返回的 web.message（联网：开，拿到 N 段 / 失败原因）
  busyKind: BusyKind | null;
  busySince: number | null;
}

const INITIAL: AppState = {
  runId: null, versions: {}, baseVersion: null, scenarioVersion: null, viewing: 'base', tab: 'workspace',
  selectedNodeId: null, selectedTerminalId: null, understood: { confirmed: false, text: null }, drafts: {},
  busy: false, errors: null, notices: null, runNote: null, webMessage: null, busyKind: null, busySince: null,
};

const TABS: [Tab, string][] = [['workspace', T.app.tabs.workspace], ['signoff', T.app.tabs.signoff], ['scenario', T.app.tabs.scenario]];

export default function App() {
  const [store, setStore] = useState<WorkspaceStore>(() => loadStore());
  const storeRef = useRef(store);
  storeRef.current = store;
  const [storageOk, setStorageOk] = useState(true);
  useEffect(() => { setStorageOk(saveStore(store)); }, [store]);
  const commit = (fn: (st: WorkspaceStore) => WorkspaceStore) => setStore((prev) => fn(prev));
  const isCurrent = (wsId: string | null) => storeRef.current.currentId === wsId;
  const [missing, setMissing] = useState<Set<string>>(new Set()); // 这次会话里发现后端已经没有这次运行的工作区

  const [s, setS] = useState<AppState>(INITIAL);
  const [event, setEvent] = useState<string>(T.app.defaultEvent);
  const [online, setOnline] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const patch = (p: Partial<AppState>) => setS((prev) => ({ ...prev, ...p }));
  const current = currentWorkspace(store);

  /** 取回某个工作区的一个版本；后端找不到就标出来，不静默失败。只在它仍是当前工作区时更新视图。 */
  async function loadVersion(wsId: string, runId: string, version: string) {
    try {
      const bundle = await api.getVersion(runId, version);
      if (isCurrent(wsId)) setS((prev) => ({ ...prev, runId, baseVersion: version, versions: { ...prev.versions, [version]: bundle } }));
    } catch {
      setMissing((prev) => new Set(prev).add(wsId));
    }
  }

  /** 改假设 / 批准：成功后取回新版本，记进发起它的工作区；用户这时已经切到别的工作区就不动视图。 */
  async function write(run: () => Promise<WriteResult>, after: (version: string) => Partial<AppState>,
    persist: (st: WorkspaceStore, wsId: string, version: string) => WorkspaceStore, kind: BusyKind) {
    const wsId = storeRef.current.currentId;
    const runId = s.runId;
    if (!wsId || !runId) return;
    patch({ busy: true, errors: null, notices: null, busyKind: kind, busySince: Date.now() });
    try {
      const res = await run();
      if (!res.ok || !res.version) {
        if (isCurrent(wsId)) patch({ busy: false, errors: res.errors.length ? res.errors : [T.app.noVersion] });
        return;
      }
      const version = res.version;
      commit((st) => persist(st, wsId, version));
      const bundle = await api.getVersion(runId, version);
      if (isCurrent(wsId)) setS((prev) => ({
        ...prev, ...after(version), busy: false, versions: { ...prev.versions, [version]: bundle },
        notices: res.errors.length ? res.errors : null,
      }));
    } catch (e) {
      if (isCurrent(wsId)) patch({ busy: false, errors: [String(e)] });
    }
  }

  /** 新问题 = 新工作区：马上切过去（画布换成等待状态，不再显示上一个问题的图），结果回来后记进这个工作区。 */
  async function analyzeText(text: string, withOnline: boolean) {
    const q = text.trim();
    if (!q) return;
    const { workspace } = createWorkspace(EMPTY_STORE, { event: q, online: withOnline, mockFixture: api.MOCK ? mockName : null });
    commit((st) => addWorkspace(st, workspace));
    storeRef.current = addWorkspace(storeRef.current, workspace);
    setS(INITIAL);
    setEvent(q);
    const id = workspace.id;
    try {
      const res: RunCreated = await api.createRun({ event: q, online: withOnline });
      const web = res.web?.message ?? null;
      const reason = res.discover?.abstained ? res.discover.abstain_reason : res.inspect?.no_chain ? res.inspect.no_chain_reason : null;
      if (res.ok && res.version && res.run_id) {
        const runId = res.run_id, version = res.version;
        commit((st) => recordVersion(updateWorkspace(st, id, { runId, status: 'ready', error: null }), id, version, true));
        if (isCurrent(id)) { patch({ runId, webMessage: web }); await loadVersion(id, runId, version); }
      } else if (res.ok && reason) {
        commit((st) => updateWorkspace(st, id, { runId: res.run_id, status: 'ready', note: reason }));
        if (isCurrent(id)) setS({ ...INITIAL, runId: res.run_id, runNote: reason, webMessage: web });
      } else {
        const error = res.errors.length ? res.errors.join(' / ') : T.app.noVersion;
        commit((st) => updateWorkspace(st, id, { status: 'failed', error, runId: res.run_id ?? null }));
        if (isCurrent(id)) patch({ webMessage: web });
      }
    } catch (e) {
      commit((st) => updateWorkspace(st, id, { status: 'failed', error: String(e) }));
    }
  }
  const analyze = () => analyzeText(event, online);

  /** 打开一个过去的研究：视图整份重置，再从后端取回它当前的版本。 */
  function openWorkspace(id: string, tab: Tab = 'workspace') {
    const w = storeRef.current.workspaces.find((x) => x.id === id);
    if (!w) return;
    commit((st) => switchWorkspace(st, id));
    storeRef.current = switchWorkspace(storeRef.current, id);
    setS({ ...INITIAL, runId: w.runId, runNote: w.note, tab });
    setEvent(w.event);
    setOnline(w.online);
    if (api.MOCK && w.mockFixture) { api.setMockFixture(w.mockFixture); setMockName(w.mockFixture); }
    if (w.status === 'ready' && w.runId && w.baseVersion) void loadVersion(id, w.runId, w.baseVersion);
  }

  function newResearch() {
    commit((st) => switchWorkspace(st, null));
    storeRef.current = switchWorkspace(storeRef.current, null);
    setS(INITIAL);
    setEvent('');
    setTimeout(() => inputRef.current?.focus(), 0);
  }

  // 真实模式：?run=<run_id>&v=<version> 直接打开已经录好的一次运行（不调模型），也记成一个工作区
  useEffect(() => {
    if (api.MOCK) return;
    const q = new URLSearchParams(location.search);
    const runId = q.get('run'), version = q.get('v');
    if (!runId || !version) return;
    api.getVersion(runId, version).then((bundle) => {
      const existing = storeRef.current.workspaces.find((w) => w.runId === runId);
      if (existing) { openWorkspace(existing.id); return; }
      const { workspace } = createWorkspace(EMPTY_STORE, { event: bundle.graph.user_event ?? runId, online: false });
      const ws: Ws = { ...workspace, runId, versions: [version], baseVersion: version, status: 'ready' };
      commit((st) => addWorkspace(st, ws));
      storeRef.current = addWorkspace(storeRef.current, ws);
      setEvent(ws.event);
      setS({ ...INITIAL, runId, baseVersion: version, versions: { [version]: bundle } });
    }).catch((e) => patch({ errors: [String(e)] }));
  }, []);

  // 打开页面时回到上次的工作区
  useEffect(() => {
    const w = currentWorkspace(storeRef.current);
    if (w && !new URLSearchParams(location.search).get('run')) openWorkspace(w.id);
  }, []);

  // MOCK：页头选一份 fixture，输入框换成它的事件原话
  const [mockOptions, setMockOptions] = useState<{ name: string; label: string; event: string }[]>([]);
  const [mockName, setMockName] = useState('c1');
  useEffect(() => {
    if (!api.MOCK) return;
    Promise.all(api.MOCK_FIXTURES.map(async (name) => ({ name, ...(await api.mockFixtureInfo(name)) }))).then((opts) => {
      setMockOptions(opts);
      if (!currentWorkspace(storeRef.current)) setEvent(opts.find((o) => o.name === 'c1')?.event ?? T.app.defaultEvent);
    });
  }, []);
  const pickMock = (name: string) => {
    api.setMockFixture(name);
    setMockName(name);
    setEvent(mockOptions.find((o) => o.name === name)?.event ?? event);
  };

  /** 批准一份计划：带上这份的草稿（阈值、勾选的前提、备注）和改过的理解；后端产出新版本，工作区记一条批准。 */
  const approve = (terminalId: string) => {
    const d = s.drafts[terminalId] ?? EMPTY_DRAFT;
    const b = s.baseVersion ? s.versions[s.baseVersion] : null;
    const plan = b ? planOf(b, terminalId) : null;
    const node = b?.graph.nodes.find((n) => n.id === terminalId);
    const title = plan && node ? T.ws.planTitle(nodeLabel(node), plan.direction.instrument) : terminalId;
    return write(() => api.sign(s.runId!, {
      version: s.baseVersion!, terminal_id: terminalId,
      ...(s.understood.text ? { clarified_statement: s.understood.text } : {}),
      ...(d.note.trim() ? { note: d.note.trim() } : {}),
      confirmed_claim_ids: d.confirmedClaimIds, condition_overrides: d.overrides,
    }), (version) => ({ baseVersion: version, drafts: {}, selectedTerminalId: terminalId }),
    (st, id, version) => recordApproval(st, id, { version, terminalId, title, at: Date.now() }), 'sign');
  };

  /** 撤销批准：terminal_id 为 null，本版本一份都不批（= 不交易）。 */
  const revoke = () =>
    write(() => api.sign(s.runId!, { version: s.baseVersion!, terminal_id: null, confirmed_claim_ids: [], condition_overrides: {} }),
      (version) => ({ baseVersion: version, drafts: {} }),
      (st, id, version) => recordApproval(st, id, { version, terminalId: null, title: null, at: Date.now() }), 'sign');

  const forkNow = (target: string, value: string) =>
    write(() => api.fork(s.runId!, {
      base_version: s.baseVersion!,
      op: { kind: 'change_assumption', target, value, impacts: [], new_nodes: [], new_edges: [] },
    }), (version) => ({ scenarioVersion: version, viewing: 'scenario', selectedNodeId: null }),
    (st, id, version) => recordVersion(st, id, version), 'fork');

  const reapproveHere = () => {
    const id = storeRef.current.currentId, v = s.scenarioVersion;
    if (id && v) commit((st) => recordVersion(st, id, v, true));
    patch({ baseVersion: v, scenarioVersion: null, viewing: 'base', tab: 'signoff', drafts: {}, selectedNodeId: null });
  };

  const base = s.baseVersion ? s.versions[s.baseVersion] : null;
  const scen = s.scenarioVersion ? s.versions[s.scenarioVersion] : null;
  const isMissing = !!current && missing.has(current.id);

  return (
    <div className="app">
      <header className="header">
        <strong className="brand">{T.app.brand}</strong>
        <input ref={inputRef} className="event-input" value={event} onChange={(e) => setEvent(e.target.value)}
          placeholder={T.app.eventPlaceholder} onKeyDown={(e) => e.key === 'Enter' && analyze()} />
        <button className="primary" disabled={!event.trim()} onClick={analyze}>{T.app.analyze}</button>
        <label className="online-toggle">
          <input type="checkbox" checked={online} onChange={(e) => setOnline(e.target.checked)} /> {T.app.online}
        </label>
        {s.webMessage && <span className="small web-status">{T.app.webStatus(s.webMessage)}</span>}
        <span className="spacer" />
        {base && <span className="muted small">{T.app.runInfo(s.runId, base.graph.version, scen?.graph.version)}</span>}
        <a href="#playground" className="small" style={{ color: '#aab4c8' }}>{T.app.linkPlayground}</a>
        <a href="#plan-b" className="small" style={{ color: '#aab4c8' }}>{T.app.linkPlanB}</a>
        {api.MOCK && (
          <span className="badge mock">
            {T.app.mock}
            <select className="mock-select" value={mockName} onChange={(e) => pickMock(e.target.value)} aria-label={T.app.mockAria}>
              {mockOptions.map((o) => <option key={o.name} value={o.name}>{o.label}</option>)}
            </select>
          </span>
        )}
      </header>
      <div className="app-body">
        <WorkspaceSidebar store={store} missing={missing} onOpen={(id) => openWorkspace(id)} onNew={newResearch}
          onOpenApproved={(id) => openWorkspace(id, 'signoff')} />
        <div className="ws-main">
          <nav className="tabs">
            {TABS.map(([id, label]) => (
              <button key={id} className={s.tab === id ? 'tab active' : 'tab'} disabled={!base}
                onClick={() => patch({ tab: id })}>{label}</button>
            ))}
          </nav>
          {!storageOk && <div className="banner notice">{T.ws.storageOff}</div>}
          {s.busy && s.busyKind && s.busySince && <BusyHint kind={s.busyKind} since={s.busySince} online={online} />}
          {s.errors && <div className="banner error">{s.errors.map((e) => <div key={e}>{e}</div>)}</div>}
          {s.notices && <div className="banner notice">{s.notices.map((e) => <div key={e}>{e}</div>)}</div>}
          <main className="main">
            {!base && !current && (
              <div className="empty"><p>{T.app.empty}</p><p className="small muted">{T.ws.newHint}</p></div>
            )}
            {!base && current?.status === 'analyzing' && (
              <div className="empty"><BusyHint kind="analyze" since={current.createdAt} online={current.online} center /></div>
            )}
            {!base && current?.status === 'failed' && (
              <div className="empty abstain">
                <h2>{T.ws.failedTitle}</h2>
                <p className="small">{current.error === 'interrupted' ? T.ws.interrupted : current.error}</p>
                <button className="primary" onClick={() => analyzeText(current.event, current.online)}>{T.ws.retry}</button>
              </div>
            )}
            {!base && current?.status === 'ready' && isMissing && (
              <div className="empty abstain">
                <h2>{T.ws.missingTitle}</h2>
                <p className="small">{T.ws.missingNote(current.runId ?? '')}</p>
              </div>
            )}
            {!base && current?.status === 'ready' && !isMissing && s.runNote && (
              <div className="empty abstain">
                <h2>{T.app.abstainTitle}</h2>
                <p>{s.runNote}</p>
                <p className="small muted">{T.app.abstainNote}</p>
              </div>
            )}
            {!base && current?.status === 'ready' && !isMissing && !s.runNote && (
              <div className="empty muted">{T.ws.loading}</div>
            )}
            {base && s.tab === 'workspace' && (
              <Workspace bundle={base} selectedNodeId={s.selectedNodeId} selectedTerminalId={s.selectedTerminalId}
                onSelectNode={(id) => patch({ selectedNodeId: id })} onSelectTerminal={(id) => patch({ selectedTerminalId: id })}
                onGoApprove={() => patch({ tab: 'signoff' })} />
            )}
            {base && s.tab === 'signoff' && (
              <ApproveCard bundle={base} selected={s.selectedTerminalId} onSelect={(id) => patch({ selectedTerminalId: id || null })}
                drafts={s.drafts} onDraft={(tid, d) => patch({ drafts: { ...s.drafts, [tid]: d } })}
                understood={s.understood} onUnderstood={(understood) => patch({ understood })}
                onApprove={approve} onRevoke={revoke} busy={s.busy} />
            )}
            {base && s.tab === 'scenario' && (
              <Scenario versions={s.versions} base={base} scenario={scen} viewing={s.viewing} busy={s.busy}
                selectedNodeId={s.selectedNodeId} onSelect={(id) => patch({ selectedNodeId: id })}
                onToggle={(viewing) => patch({ viewing })} onFork={forkNow} onReapproveHere={reapproveHere} />
            )}
          </main>
        </div>
      </div>
    </div>
  );
}
