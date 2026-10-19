// 唯一的 state：三个标签共用同一份版本缓存；所有后端调用都从这里发，写操作之后按返回的版本号重新取快照。
import { useEffect, useState } from 'react';
import * as api from './api';
import Scenario from './components/Scenario';
import Signoff, { type SignForm } from './components/Signoff';
import Workspace from './components/Workspace';
import type { ConditionOverride, RunCreated, VersionBundle, WriteResult } from './types';

type Tab = 'workspace' | 'signoff' | 'scenario';

export interface AppState {
  runId: string | null;
  versions: Record<string, VersionBundle>; // 后端原样返回的快照，按版本号存
  baseVersion: string | null; // B1 / B2 看的版本，也是 fork 的 base_version
  scenarioVersion: string | null; // 最近一次 fork 产出的版本
  viewing: 'base' | 'scenario';
  tab: Tab;
  selectedNodeId: string | null;
  signoff: { confirmedClaimIds: string[]; conditionOverrides: Record<string, ConditionOverride> };
  busy: boolean;
  errors: string[] | null; // 后端 / 校验器的拒绝理由，原样显示
  notices: string[] | null;
  runNote: string | null; // 没有图的运行：弃权或找不到因果链的理由（后端原话）
}

const INITIAL: AppState = {
  runId: null, versions: {}, baseVersion: null, scenarioVersion: null, viewing: 'base', tab: 'workspace',
  selectedNodeId: null, signoff: { confirmedClaimIds: [], conditionOverrides: {} }, busy: false, errors: null,
  notices: null, runNote: null,
};

const TABS: [Tab, string][] = [['workspace', 'B1 Research Workspace'], ['signoff', 'B2 Sign-off'], ['scenario', 'B3 Scenario Diff']];

export default function App() {
  const [s, setS] = useState<AppState>(INITIAL);
  const [event, setEvent] = useState('光子芯片采用快于预期');
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
        patch({ busy: false, errors: res.errors.length ? res.errors : ['后端没有返回版本号'] });
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

  const analyze = () =>
    write(() => api.createRun({ event }), (version) => ({
      ...INITIAL, baseVersion: version, tab: 'workspace',
    }), (res) => {
      const reason = res.discover?.abstained ? res.discover.abstain_reason
        : res.inspect?.no_chain ? res.inspect.no_chain_reason : null;
      return reason ? { ...INITIAL, runId: res.run_id, runNote: reason } : null;
    });

  // MOCK：页头选一份 fixture，输入框换成它的事件原话
  const [mockOptions, setMockOptions] = useState<{ name: string; label: string; event: string }[]>([]);
  const [mockName, setMockName] = useState('c1');
  useEffect(() => {
    if (!api.MOCK) return;
    Promise.all(api.MOCK_FIXTURES.map(async (name) => ({ name, ...(await api.mockFixtureInfo(name)) }))).then(setMockOptions);
  }, []);
  const pickMock = (name: string) => {
    api.setMockFixture(name);
    setMockName(name);
    setEvent(mockOptions.find((o) => o.name === name)?.event ?? event);
    setS(INITIAL);
  };

  const signNow = (form: SignForm) =>
    write(() => api.sign(s.runId!, {
      version: s.baseVersion!, ...form, confirmed_claim_ids: s.signoff.confirmedClaimIds,
      condition_overrides: s.signoff.conditionOverrides,
    }), (version) => ({ baseVersion: version, signoff: INITIAL.signoff }));

  const forkNow = (target: string, value: string) =>
    write(() => api.fork(s.runId!, {
      base_version: s.baseVersion!,
      op: { kind: 'change_assumption', target, value, impacts: [], new_nodes: [], new_edges: [] },
    }), (version) => ({ scenarioVersion: version, viewing: 'scenario', selectedNodeId: null }));

  const base = s.baseVersion ? s.versions[s.baseVersion] : null;
  const scen = s.scenarioVersion ? s.versions[s.scenarioVersion] : null;

  return (
    <div className="app">
      <header className="header">
        <strong className="brand">Catalyst</strong>
        <input className="event-input" value={event} onChange={(e) => setEvent(e.target.value)}
          placeholder="你相信什么会发生？" onKeyDown={(e) => e.key === 'Enter' && analyze()} />
        <button className="primary" disabled={s.busy || !event.trim()} onClick={analyze}>Analyze</button>
        <span className="spacer" />
        {s.busy && <span className="muted">处理中…</span>}
        {base && <span className="muted small">run {s.runId} · {base.graph.version}{scen ? ` → ${scen.graph.version}` : ''}</span>}
        <a href="#playground" className="small" style={{ color: '#aab4c8' }}>节点视觉 playground</a>
        {api.MOCK && (
          <span className="badge mock">
            MOCK ·{' '}
            <select className="mock-select" value={mockName} onChange={(e) => pickMock(e.target.value)} aria-label="MOCK 数据">
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
        {!base && !s.runNote && <div className="empty">输入一个事件，点 Analyze。</div>}
        {!base && s.runNote && (
          <div className="empty abstain">
            <h2>没有找到有依据的因果链</h2>
            <p>{s.runNote}</p>
            <p className="small muted">所以没有画图，也没有生成提案。找不到依据时系统选择弃权，不会为了出结果硬连一个标的。</p>
          </div>
        )}
        {base && s.tab === 'workspace' && (
          <Workspace bundle={base} selectedNodeId={s.selectedNodeId} onSelect={(id) => patch({ selectedNodeId: id })} />
        )}
        {base && s.tab === 'signoff' && (
          <Signoff bundle={base} signoff={s.signoff} busy={s.busy} onChange={(signoff) => patch({ signoff })} onSign={signNow} />
        )}
        {base && s.tab === 'scenario' && (
          <Scenario versions={s.versions} base={base} scenario={scen} viewing={s.viewing} busy={s.busy}
            selectedNodeId={s.selectedNodeId} onSelect={(id) => patch({ selectedNodeId: id })}
            onToggle={(viewing) => patch({ viewing })} onFork={forkNow} />
        )}
      </main>
    </div>
  );
}
