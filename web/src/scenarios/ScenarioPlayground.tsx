// 多情景 playground（/#scenarios）：五个设计问题，每个两种做法并排，用 fixtures/c1_multi.json 渲染。
// 视角：灵动岛 / Apple Watch（一眼看懂、原地展开）+ Robinhood（大数字、分段切换、涨跌色）。
// 这是设计探索，不调后端；「新建情景」只是交互演示，不会真的分叉。
import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { toFlow } from '../toFlow';
import type { Fixture, VersionBundle } from '../types';
import { GATE, SUPPORT } from '../status';
import Badge from '../components/Badge';
import ScenarioCanvas from './ScenarioCanvas';
import {
  childrenOf, chain, cumulativeChallenged, cumulativeColoring, fullName, layerColoring, newChallenged, rootOf,
  scenarioIds, scenarioName,
  type Versions,
} from './model';
import '../playground/playground.css';
import './scenarios.css';
import { T } from '../strings';

type Pick = 'A' | 'B';
interface Side { name: string; desc: string; render: (v: Versions) => ReactNode }
interface Ground { key: string; title: string; question: string; A: Side; B: Side }

const A_COLOR = '#ff9500';
const B_COLOR = '#007aff';
const BOTH_COLOR = '#af52de';

// ---- 1 情景列表 ----------------------------------------------------------

function Segmented({ versions }: { versions: Versions }) {
  const root = rootOf(versions);
  const ids = [root, ...scenarioIds(versions)];
  const [cur, setCur] = useState(ids[1] ?? root);
  return (
    <div className="sc-col">
      <div className="sc-seg">
        {ids.map((v) => (
          <button key={v} className={v === cur ? 'on' : ''} onClick={() => setCur(v)}>{fullName(versions, v)}</button>
        ))}
      </div>
      <ScenarioCanvas bundle={versions[cur]} coloring={versions[cur].scenario ? cumulativeColoring(versions, cur) : undefined} />
    </div>
  );
}

function Tree({ versions }: { versions: Versions }) {
  const root = rootOf(versions);
  const [cur, setCur] = useState(scenarioIds(versions)[0] ?? root);
  const row = (v: string, depth: number): ReactNode => (
    <div key={v}>
      <button className={`sc-tree-row${v === cur ? ' on' : ''}`} style={{ paddingLeft: 10 + depth * 18 }} onClick={() => setCur(v)}>
        {depth > 0 && <span className="sc-branch">└</span>}
        <span>{scenarioName(versions, v)}</span>
        {versions[v].scenario && <span className="sc-count">{newChallenged(versions, v).length}</span>}
      </button>
      {childrenOf(versions, v).map((c) => row(c, depth + 1))}
    </div>
  );
  return (
    <div className="sc-row">
      <nav className="sc-tree">{row(root, 0)}<div className="sc-hint">{T.pgScen.treeHint}</div></nav>
      <ScenarioCanvas bundle={versions[cur]} coloring={versions[cur].scenario ? cumulativeColoring(versions, cur) : undefined} />
    </div>
  );
}

// ---- 2 怎么比较 ----------------------------------------------------------

function Overlay({ versions }: { versions: Versions }) {
  const [a, b] = scenarioIds(versions).filter((v) => versions[v].scenario!.base_version === rootOf(versions));
  const tints = useMemo(() => {
    const ca = new Set(cumulativeChallenged(versions[a])), cb = new Set(cumulativeChallenged(versions[b]));
    const out: Record<string, string> = {};
    for (const id of new Set([...ca, ...cb])) out[id] = ca.has(id) && cb.has(id) ? BOTH_COLOR : ca.has(id) ? A_COLOR : B_COLOR;
    return out;
  }, [versions, a, b]);
  return (
    <div className="sc-col">
      <div className="sc-legend">
        <span><i style={{ background: A_COLOR }} />{scenarioName(versions, a)}</span>
        <span><i style={{ background: B_COLOR }} />{scenarioName(versions, b)}</span>
        <span><i style={{ background: BOTH_COLOR }} />{T.pgScen.bothChallenged}</span>
      </div>
      <ScenarioCanvas bundle={versions[rootOf(versions)]} tints={tints} />
    </div>
  );
}

function SideBySide({ versions }: { versions: Versions }) {
  const [a, b] = scenarioIds(versions).filter((v) => versions[v].scenario!.base_version === rootOf(versions));
  return (
    <div className="sc-row">
      {[a, b].map((v) => (
        <div key={v} className="sc-col sc-half">
          <div className="sc-half-title">{scenarioName(versions, v)}</div>
          <ScenarioCanvas bundle={versions[v]} coloring={cumulativeColoring(versions, v)} compact />
        </div>
      ))}
    </div>
  );
}

// ---- 3 叠加后的着色 ------------------------------------------------------

function stacked(versions: Versions) {
  return scenarioIds(versions).find((v) => versions[v].scenario!.base_version !== rootOf(versions))!;
}

function Relative({ versions }: { versions: Versions }) {
  const v = stacked(versions);
  return (
    <div className="sc-col">
      <div className="sc-note">{T.pgScen.relativeNote(fullName(versions, v), scenarioName(versions, versions[v].scenario!.base_version))}</div>
      <ScenarioCanvas bundle={versions[v]} coloring={layerColoring(versions, v)} />
    </div>
  );
}

function Cumulative({ versions }: { versions: Versions }) {
  const v = stacked(versions);
  return (
    <div className="sc-col">
      <div className="sc-note">{T.pgScen.cumulativeNote(fullName(versions, v))}</div>
      <ScenarioCanvas bundle={versions[v]} coloring={cumulativeColoring(versions, v)} />
    </div>
  );
}

// ---- 4 情景摘要 ----------------------------------------------------------

function BigNumber({ versions }: { versions: Versions }) {
  const root = versions[rootOf(versions)];
  return (
    <div className="sc-cards">
      {scenarioIds(versions).map((v) => {
        const b = versions[v], p = b.proposal!, base = versions[b.scenario!.base_version].proposal!;
        const n = cumulativeChallenged(b).length, added = newChallenged(versions, v).length;
        return (
          <div key={v} className="sc-card">
            <div className="sc-card-name">{fullName(versions, v)}</div>
            <div className="sc-big" style={{ color: n ? A_COLOR : '#34c759' }}>{n}</div>
            <div className="sc-sub">{T.pgScen.bigSub(added)}</div>
            <div className="sc-delta">
              <span>{T.pgScen.support}</span>
              <span style={{ color: SUPPORT[base.support_status].color }}>{base.support_status}</span>
              <span>→</span>
              <span style={{ color: SUPPORT[p.support_status].color }}>{p.support_status}</span>
            </div>
            <Badge look={GATE[p.gate]} />
          </div>
        );
      })}
      <div className="sc-card sc-base">
        <div className="sc-card-name">{T.pgScen.baseline}</div>
        <div className="sc-big">{root.graph.nodes.length}</div>
        <div className="sc-sub">{T.pgScen.baseSub(root.proposal!.gate)}</div>
      </div>
    </div>
  );
}

function DotMap({ b, coloring }: { b: VersionBundle; coloring?: ReturnType<typeof cumulativeColoring> }) {
  const { nodes } = toFlow(b.graph);
  const xs = nodes.map((n) => n.position.x), ys = nodes.map((n) => n.position.y);
  const w = Math.max(...xs) - Math.min(...xs) || 1, h = Math.max(...ys) - Math.min(...ys) || 1;
  return (
    <svg viewBox="-8 -8 116 76" className="sc-dots" aria-hidden="true">
      {nodes.map((n) => {
        const x = ((n.position.x - Math.min(...xs)) / w) * 100, y = ((n.position.y - Math.min(...ys)) / h) * 60;
        const c = coloring?.changed.includes(n.id) ? B_COLOR : coloring?.assessment[n.id] === 'challenged' ? A_COLOR : '#d1d5db';
        return <circle key={n.id} cx={x} cy={y} r="6" fill={c} />;
      })}
    </svg>
  );
}

function WatchFaces({ versions }: { versions: Versions }) {
  return (
    <div className="sc-cards">
      {[rootOf(versions), ...scenarioIds(versions)].map((v) => (
        <div key={v} className="sc-face">
          <DotMap b={versions[v]} coloring={versions[v].scenario ? cumulativeColoring(versions, v) : undefined} />
          <div className="sc-card-name">{fullName(versions, v)}</div>
        </div>
      ))}
      <div className="sc-legend" style={{ gridColumn: '1 / -1' }}>
        <span><i style={{ background: A_COLOR }} />{T.pgScen.legendChallenged}</span><span><i style={{ background: B_COLOR }} />{T.pgScen.legendChanged}</span>
        <span><i style={{ background: '#d1d5db' }} />{T.pgScen.legendUnchanged}</span><span>{T.pgScen.legendDots}</span>
      </div>
    </div>
  );
}

// ---- 5 新建情景 ----------------------------------------------------------

function useCreate(versions: Versions) {
  const ids = [rootOf(versions), ...scenarioIds(versions)];
  const [from, setFrom] = useState(ids[1] ?? ids[0]);
  const graph = versions[from].graph;
  const [target, setTarget] = useState(graph.nodes[0].id);
  const [value, setValue] = useState('');
  const [name, setName] = useState('');
  const [done, setDone] = useState(false);
  return { ids, from, setFrom, graph, target, setTarget, value, setValue, name, setName, done, setDone };
}

function Island({ versions }: { versions: Versions }) {
  const f = useCreate(versions);
  const [open, setOpen] = useState(false);
  return (
    <div className="sc-col sc-rel">
      <ScenarioCanvas bundle={versions[f.from]} coloring={versions[f.from].scenario ? cumulativeColoring(versions, f.from) : undefined} />
      <div className={`sc-island${open ? ' open' : ''}`}>
        {!open ? (
          <button className="sc-island-pill" onClick={() => setOpen(true)}>{T.pgScen.islandPill}<span>{T.pgScen.islandOn(fullName(versions, f.from))}</span></button>
        ) : f.done ? (
          <div className="sc-island-body"><div>{T.pgScen.demoDone(fullName(versions, f.from), f.name || f.value.slice(0, 10))}</div>
            <button onClick={() => { setOpen(false); f.setDone(false); }}>{T.pgScen.ok}</button></div>
        ) : (
          <div className="sc-island-body">
            <div style={{ color: '#9aa1ab', fontSize: 12 }}>{T.pgScen.islandLead(fullName(versions, f.from))}</div>
            <div className="sc-island-row">
              <select value={f.target} onChange={(e) => f.setTarget(e.target.value)}>
                {f.graph.nodes.map((n) => <option key={n.id} value={n.id}>{n.statement.slice(0, 16)}</option>)}
              </select>
            </div>
            <input placeholder={T.pgScen.valuePlaceholder} value={f.value} onChange={(e) => f.setValue(e.target.value)} />
            <input placeholder={T.pgScen.namePlaceholder(f.value)} value={f.name} onChange={(e) => f.setName(e.target.value)} />
            <div className="sc-island-row">
              <button onClick={() => setOpen(false)}>{T.pgScen.cancel}</button>
              <button className="go" disabled={!f.value.trim()} onClick={() => f.setDone(true)}>{T.pgScen.fork}</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function SideForm({ versions }: { versions: Versions }) {
  const f = useCreate(versions);
  return (
    <div className="sc-row">
      <ScenarioCanvas bundle={versions[f.from]} coloring={versions[f.from].scenario ? cumulativeColoring(versions, f.from) : undefined} />
      <aside className="sc-form">
        <label>{T.pgScen.fromVersion}</label>
        <select value={f.from} onChange={(e) => f.setFrom(e.target.value)}>
          {f.ids.map((v) => <option key={v} value={v}>{fullName(versions, v)}</option>)}
        </select>
        <label>{T.pgScen.whichNode}</label>
        <select value={f.target} onChange={(e) => f.setTarget(e.target.value)}>
          {f.graph.nodes.map((n) => <option key={n.id} value={n.id}>{n.statement.slice(0, 16)}</option>)}
        </select>
        <label>{T.pgScen.changeTo}</label>
        <input value={f.value} placeholder={T.pgScen.sidePlaceholder} onChange={(e) => f.setValue(e.target.value)} />
        <label>{T.pgScen.name}</label>
        <input value={f.name} placeholder={f.value.slice(0, 10) || T.pgScen.nameDefault} onChange={(e) => f.setName(e.target.value)} />
        <button className="pg-pick" disabled={!f.value.trim()} onClick={() => f.setDone(true)}>{T.pgScen.fork}</button>
        {f.done && <div className="sc-hint">{T.pgScen.demoDone(fullName(versions, f.from), f.name || f.value.slice(0, 10))}</div>}
      </aside>
    </div>
  );
}

// ---- 页面 ----------------------------------------------------------------

const GROUNDS: Ground[] = [
  { key: 'list', ...T.pgScen.list,
    A: { ...T.pgScen.list.A, render: (v) => <Segmented versions={v} /> }, B: { ...T.pgScen.list.B, render: (v) => <Tree versions={v} /> } },
  { key: 'compare', ...T.pgScen.compare,
    A: { ...T.pgScen.compare.A, render: (v) => <Overlay versions={v} /> }, B: { ...T.pgScen.compare.B, render: (v) => <SideBySide versions={v} /> } },
  { key: 'stack', ...T.pgScen.stack,
    A: { ...T.pgScen.stack.A, render: (v) => <Relative versions={v} /> }, B: { ...T.pgScen.stack.B, render: (v) => <Cumulative versions={v} /> } },
  { key: 'summary', ...T.pgScen.summary,
    A: { ...T.pgScen.summary.A, render: (v) => <BigNumber versions={v} /> }, B: { ...T.pgScen.summary.B, render: (v) => <WatchFaces versions={v} /> } },
  { key: 'create', ...T.pgScen.create,
    A: { ...T.pgScen.create.A, render: (v) => <Island versions={v} /> }, B: { ...T.pgScen.create.B, render: (v) => <SideForm versions={v} /> } },
];

const STORE = 'catalyst.scenarios.picks';

export default function ScenarioPlayground() {
  const [fx, setFx] = useState<Fixture | null>(null);
  const [active, setActive] = useState(0);
  const [picks, setPicks] = useState<Record<string, Pick>>(() => {
    try { return JSON.parse(localStorage.getItem(STORE) ?? '{}'); } catch { return {}; }
  });
  useEffect(() => {
    import('../../fixtures/c1_multi.json').then((m) => setFx(m.default as unknown as Fixture));
  }, []);
  const choose = (k: string, p: Pick) => {
    const next = { ...picks, [k]: p };
    setPicks(next);
    try { localStorage.setItem(STORE, JSON.stringify(next)); } catch { /* 不记住也能用 */ }
  };
  if (!fx) return <div className="pg">{T.pg.loading}</div>;
  const g = GROUNDS[active];
  const summary = GROUNDS.map((x, i) => T.pg.summaryItem(i + 1, picks[x.key], x.title, picks[x.key] ? x[picks[x.key]].name : null)).join(T.pg.summarySep);
  const versions = fx.versions;

  return (
    <div className="pg">
      <header className="pg-head">
        <a href="#" className="pg-back">{T.pg.back}</a>
        <a href="#playground" className="pg-back">{T.pgScen.linkNode}</a>
        <strong>{T.pgScen.title}</strong>
        <nav className="pg-nav">
          {GROUNDS.map((x, i) => (
            <button key={x.key} className={i === active ? 'on' : ''} onClick={() => setActive(i)}>
              {T.pg.navItem(i + 1, x.title, picks[x.key])}
            </button>
          ))}
        </nav>
      </header>
      <div className="pg-q">
        <h2>{active + 1}. {g.question}</h2>
        <span className="pg-note">{T.pgScen.note(chain(versions, Object.keys(versions).at(-1)!).length)}</span>
      </div>
      <div className="pg-ab">
        {(['A', 'B'] as Pick[]).map((p) => (
          <section key={p} className={`pg-option${picks[g.key] === p ? ' picked' : ''}`}>
            <div className="pg-option-head">
              <div><strong>{T.pg.optionTitle(p, g[p].name)}</strong><div className="pg-sub">{g[p].desc}</div></div>
              <button className="pg-pick" onClick={() => choose(g.key, p)}>{picks[g.key] === p ? T.pg.picked : T.pg.pick}</button>
            </div>
            <div className="pg-pane" key={`${g.key}-${p}`}>{g[p].render(versions)}</div>
          </section>
        ))}
      </div>
      <footer className="pg-foot">
        <span>{T.pg.yourPicks(summary)}</span>
        <button className="pg-pick" onClick={() => navigator.clipboard?.writeText(summary)}>{T.pg.copy}</button>
      </footer>
    </div>
  );
}
