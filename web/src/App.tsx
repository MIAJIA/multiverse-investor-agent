// 唯一的 state：三个标签共用同一份版本缓存；所有后端调用都从这里发，写操作之后按返回的版本号重新取快照。
// 方案 B：一个版本有几份计划（每个结论一份）；B2 批准其中一份或撤销（sign，terminal_id 为 null）。
import { useEffect, useState } from 'react';
import * as api from './api';
import { EMPTY_DRAFT, type PlanDraft, type Understood } from './components/ApprovePlans';
import ApproveList from './components/approve/ApproveList';
import Scenario from './components/Scenario';
import Workspace from './components/Workspace';
import type { RunCreated, VersionBundle, WriteResult } from './types';
import { T } from './strings';

type Tab = 'workspace' | 'signoff' | 'scenario';

export interface AppState {
  runId: string | null;
  versions: Record<string, VersionBundle>; // 后端原样返回的快照，按版本号存
  baseVersion: string | null; // B1 / B2 看的版本，也是 fork 的 base_version
  scenarioVersion: string | null; // 最近一次 fork 产出的版本
  viewing: 'base' | 'scenario';
  tab: Tab;
  selectedNodeId: string | null;
  selectedTerminalId: string | null; // B1 高亮的结论 = B2 选中的那一行
  understood: Understood; // 「你的想法」确认；同一次运行里一直有效
  drafts: Record<string, PlanDraft>; // 按 terminal 存还没提交的输入；当前版本变了就清空
  busy: boolean;
  errors: string[] | null; // 后端 / 校验器的拒绝理由，原样显示
  notices: string[] | null;
  runNote: string | null; // 没有图的运行：弃权或找不到因果链的理由（后端原话）
  webMessage: string | null; // 上一次建 run 返回的 web.message（联网：开，拿到 N 段 / 失败原因）
}

const INITIAL: AppState = {
  runId: null, versions: {}, baseVersion: null, scenarioVersion: null, viewing: 'base', tab: 'workspace',
  selectedNodeId: null, selectedTerminalId: null, understood: { confirmed: false, text: null }, drafts: {},
  busy: false, errors: null, notices: null, runNote: null, webMessage: null,
};

const TABS: [Tab, string][] = [['workspace', T.app.tabs.workspace], ['signoff', T.app.tabs.signoff], ['scenario', T.app.tabs.scenario]];

export default function App() {
  const [s, setS] = useState<AppState>(INITIAL);
  const [event, setEvent] = useState<string>(T.app.defaultEvent);
  const [online, setOnline] = useState(false);
  const patch = (p: Partial<AppState>) => setS((prev) => ({ ...prev, ...p }));

  /** 发一个写操作；成功后取回新版本并存进缓存。 */
  async function write(run: () => Promise<RunCreated | WriteResult>,
    after: (version: string, bundle: VersionBundle, runId: string) => Partial<AppState>,
    onNoVersion?: (res: RunCreated) => Partial<AppState> | null) {
    patch({ busy: true, errors: null, notices: null });
    try {
      const res = await run();
      const noVersion = res.ok && !res.version && onNoVersion?.(res as RunCreated);
      if (noVersion) {
        setS((prev) => ({ ...prev, ...noVersion, busy: false }));
        return;
      }
      const runId = ('run_id' in res ? res.run_id : null) ?? s.runId;
      if (!res.ok || !res.version || !runId) {
        patch({ busy: false, errors: res.errors.length ? res.errors : [T.app.noVersion] });
        return;
      }
      const bundle = await api.getVersion(runId, res.version);
      setS((prev) => ({
        ...prev, ...after(res.version!, bundle, runId), runId, busy: false,
        versions: { ...prev.versions, [res.version!]: bundle }, notices: res.errors.length ? res.errors : null,
      }));
    } catch (e) {
      patch({ busy: false, errors: [String(e)] });
    }
  }

  const analyze = () => {
    let web: string | null = null;
    return write(() => api.createRun({ event, online }).then((res) => { web = res.web?.message ?? null; return res; }),
      (version) => ({ ...INITIAL, baseVersion: version, tab: 'workspace', webMessage: web }),
      (res) => {
        const reason = res.discover?.abstained ? res.discover.abstain_reason
          : res.inspect?.no_chain ? res.inspect.no_chain_reason : null;
        return reason ? { ...INITIAL, runId: res.run_id, runNote: reason, webMessage: res.web?.message ?? null } : null;
      });
  };

  // MOCK：页头选一份 fixture，输入框换成它的事件原话
  const [mockOptions, setMockOptions] = useState<{ name: string; label: string; event: string }[]>([]);
  const [mockName, setMockName] = useState('c1');
  useEffect(() => {
    if (!api.MOCK) return;
    Promise.all(api.MOCK_FIXTURES.map(async (name) => ({ name, ...(await api.mockFixtureInfo(name)) }))).then((opts) => {
      setMockOptions(opts);
      setEvent(opts.find((o) => o.name === 'c1')?.event ?? T.app.defaultEvent);
    });
  }, []);
  const pickMock = (name: string) => {
    api.setMockFixture(name);
    setMockName(name);
    setEvent(mockOptions.find((o) => o.name === name)?.event ?? event);
    setS(INITIAL);
  };

  /** 批准一份计划：带上这份的草稿（阈值、勾选的前提、备注）和改过的理解；后端产出新版本。 */
  const approve = (terminalId: string) => {
    const d = s.drafts[terminalId] ?? EMPTY_DRAFT;
    return write(() => api.sign(s.runId!, {
      version: s.baseVersion!, terminal_id: terminalId,
      ...(s.understood.text ? { clarified_statement: s.understood.text } : {}),
      ...(d.note.trim() ? { note: d.note.trim() } : {}),
      confirmed_claim_ids: d.confirmedClaimIds, condition_overrides: d.overrides,
    }), (version) => ({ baseVersion: version, drafts: {}, selectedTerminalId: terminalId }));
  };

  /** 撤销批准：terminal_id 为 null，本版本一份都不批（= 不交易）。 */
  const revoke = () =>
    write(() => api.sign(s.runId!, { version: s.baseVersion!, terminal_id: null, confirmed_claim_ids: [], condition_overrides: {} }),
      (version) => ({ baseVersion: version, drafts: {} }));

  const forkNow = (target: string, value: string) =>
    write(() => api.fork(s.runId!, {
      base_version: s.baseVersion!,
      op: { kind: 'change_assumption', target, value, impacts: [], new_nodes: [], new_edges: [] },
    }), (version) => ({ scenarioVersion: version, viewing: 'scenario', selectedNodeId: null }));

  const reapproveHere = () => patch({
    baseVersion: s.scenarioVersion, scenarioVersion: null, viewing: 'base', tab: 'signoff', drafts: {}, selectedNodeId: null,
  });

  const base = s.baseVersion ? s.versions[s.baseVersion] : null;
  const scen = s.scenarioVersion ? s.versions[s.scenarioVersion] : null;

  return (
    <div className="app">
      <header className="header">
        <strong className="brand">{T.app.brand}</strong>
        <input className="event-input" value={event} onChange={(e) => setEvent(e.target.value)}
          placeholder={T.app.eventPlaceholder} onKeyDown={(e) => e.key === 'Enter' && analyze()} />
        <button className="primary" disabled={s.busy || !event.trim()} onClick={analyze}>{T.app.analyze}</button>
        <label className="online-toggle">
          <input type="checkbox" checked={online} onChange={(e) => setOnline(e.target.checked)} /> {T.app.online}
        </label>
        {s.webMessage && <span className="small web-status">{T.app.webStatus(s.webMessage)}</span>}
        <span className="spacer" />
        {s.busy && <span className="muted">{T.app.busy}</span>}
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
      <nav className="tabs">
        {TABS.map(([id, label]) => (
          <button key={id} className={s.tab === id ? 'tab active' : 'tab'} disabled={!base}
            onClick={() => patch({ tab: id })}>{label}</button>
        ))}
      </nav>
      {s.errors && <div className="banner error">{s.errors.map((e) => <div key={e}>{e}</div>)}</div>}
      {s.notices && <div className="banner notice">{s.notices.map((e) => <div key={e}>{e}</div>)}</div>}
      <main className="main">
        {!base && !s.runNote && <div className="empty">{T.app.empty}</div>}
        {!base && s.runNote && (
          <div className="empty abstain">
            <h2>{T.app.abstainTitle}</h2>
            <p>{s.runNote}</p>
            <p className="small muted">{T.app.abstainNote}</p>
          </div>
        )}
        {base && s.tab === 'workspace' && (
          <Workspace bundle={base} selectedNodeId={s.selectedNodeId} selectedTerminalId={s.selectedTerminalId}
            onSelectNode={(id) => patch({ selectedNodeId: id })} onSelectTerminal={(id) => patch({ selectedTerminalId: id })}
            onGoApprove={() => patch({ tab: 'signoff' })} />
        )}
        {base && s.tab === 'signoff' && (
          <ApproveList bundle={base} selected={s.selectedTerminalId} onSelect={(id) => patch({ selectedTerminalId: id || null })}
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
  );
}
