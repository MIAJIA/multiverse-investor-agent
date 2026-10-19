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
  challenged, childrenOf, chain, cumulativeColoring, fullName, relativeColoring, rootOf, scenarioIds, scenarioName,
  type Versions,
} from './model';
import '../playground/playground.css';
import './scenarios.css';

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
      <ScenarioCanvas bundle={versions[cur]} coloring={versions[cur].scenario ? relativeColoring(versions[cur]) : undefined} />
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
        {versions[v].scenario && <span className="sc-count">{challenged(versions[v]).length}</span>}
      </button>
      {childrenOf(versions, v).map((c) => row(c, depth + 1))}
    </div>
  );
  return (
    <div className="sc-row">
      <nav className="sc-tree">{row(root, 0)}<div className="sc-hint">数字 = 这一层新增的受挑战前提</div></nav>
      <ScenarioCanvas bundle={versions[cur]} coloring={versions[cur].scenario ? relativeColoring(versions[cur]) : undefined} />
    </div>
  );
}

// ---- 2 怎么比较 ----------------------------------------------------------

function Overlay({ versions }: { versions: Versions }) {
  const [a, b] = scenarioIds(versions).filter((v) => versions[v].scenario!.base_version === rootOf(versions));
  const tints = useMemo(() => {
    const ca = new Set(challenged(versions[a])), cb = new Set(challenged(versions[b]));
    const out: Record<string, string> = {};
    for (const id of new Set([...ca, ...cb])) out[id] = ca.has(id) && cb.has(id) ? BOTH_COLOR : ca.has(id) ? A_COLOR : B_COLOR;
    return out;
  }, [versions, a, b]);
  return (
    <div className="sc-col">
      <div className="sc-legend">
        <span><i style={{ background: A_COLOR }} />{scenarioName(versions, a)}</span>
        <span><i style={{ background: B_COLOR }} />{scenarioName(versions, b)}</span>
        <span><i style={{ background: BOTH_COLOR }} />两个都受挑战</span>
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
          <ScenarioCanvas bundle={versions[v]} coloring={relativeColoring(versions[v])} compact />
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
      <div className="sc-note">「{fullName(versions, v)}」：只标这一层新受挑战的；相对「{scenarioName(versions, versions[v].scenario!.base_version)}」</div>
      <ScenarioCanvas bundle={versions[v]} coloring={relativeColoring(versions[v])} />
    </div>
  );
}

function Cumulative({ versions }: { versions: Versions }) {
  const v = stacked(versions);
  return (
    <div className="sc-col">
      <div className="sc-note">「{fullName(versions, v)}」：链上每一层受挑战的都标出来；相对基线。演示用前端合并，正式版要后端给</div>
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
        const n = challenged(b).length;
        return (
          <div key={v} className="sc-card">
            <div className="sc-card-name">{fullName(versions, v)}</div>
            <div className="sc-big" style={{ color: n ? A_COLOR : '#34c759' }}>{n}</div>
            <div className="sc-sub">个前提受挑战（这一层）</div>
            <div className="sc-delta">
              <span>支持度</span>
              <span style={{ color: SUPPORT[base.support_status].color }}>{base.support_status}</span>
              <span>→</span>
              <span style={{ color: SUPPORT[p.support_status].color }}>{p.support_status}</span>
            </div>
            <Badge look={GATE[p.gate]} />
          </div>
        );
      })}
      <div className="sc-card sc-base">
        <div className="sc-card-name">基线</div>
        <div className="sc-big">{root.graph.nodes.length}</div>
        <div className="sc-sub">个前提，gate {root.proposal!.gate}</div>
      </div>
    </div>
  );
}

function DotMap({ b, coloring }: { b: VersionBundle; coloring?: ReturnType<typeof relativeColoring> }) {
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
          <DotMap b={versions[v]} coloring={versions[v].scenario ? relativeColoring(versions[v]) : undefined} />
          <div className="sc-card-name">{fullName(versions, v)}</div>
        </div>
      ))}
      <div className="sc-legend" style={{ gridColumn: '1 / -1' }}>
        <span><i style={{ background: A_COLOR }} />受挑战</span><span><i style={{ background: B_COLOR }} />改动的假设</span>
        <span><i style={{ background: '#d1d5db' }} />未变</span><span>每个点是一个节点，位置和画布一致</span>
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
      <ScenarioCanvas bundle={versions[f.from]} coloring={versions[f.from].scenario ? relativeColoring(versions[f.from]) : undefined} />
      <div className={`sc-island${open ? ' open' : ''}`}>
        {!open ? (
          <button className="sc-island-pill" onClick={() => setOpen(true)}>＋ 假如…<span>在「{fullName(versions, f.from)}」上</span></button>
        ) : f.done ? (
          <div className="sc-island-body"><div>已演示：会从「{fullName(versions, f.from)}」分出「{f.name || f.value.slice(0, 10)}」</div>
            <button onClick={() => { setOpen(false); f.setDone(false); }}>好</button></div>
        ) : (
          <div className="sc-island-body">
            <div style={{ color: '#9aa1ab', fontSize: 12 }}>在「{fullName(versions, f.from)}」上再假如一次</div>
            <div className="sc-island-row">
              <select value={f.target} onChange={(e) => f.setTarget(e.target.value)}>
                {f.graph.nodes.map((n) => <option key={n.id} value={n.id}>{n.statement.slice(0, 16)}</option>)}
              </select>
            </div>
            <input placeholder="改成什么，例如：开放推迟两周" value={f.value} onChange={(e) => f.setValue(e.target.value)} />
            <input placeholder={f.value ? `情景名（默认：${f.value.slice(0, 10)}）` : '情景名'} value={f.name} onChange={(e) => f.setName(e.target.value)} />
            <div className="sc-island-row">
              <button onClick={() => setOpen(false)}>取消</button>
              <button className="go" disabled={!f.value.trim()} onClick={() => f.setDone(true)}>分叉</button>
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
      <ScenarioCanvas bundle={versions[f.from]} coloring={versions[f.from].scenario ? relativeColoring(versions[f.from]) : undefined} />
      <aside className="sc-form">
        <label>从哪个版本出发</label>
        <select value={f.from} onChange={(e) => f.setFrom(e.target.value)}>
          {f.ids.map((v) => <option key={v} value={v}>{fullName(versions, v)}</option>)}
        </select>
        <label>改哪个节点</label>
        <select value={f.target} onChange={(e) => f.setTarget(e.target.value)}>
          {f.graph.nodes.map((n) => <option key={n.id} value={n.id}>{n.statement.slice(0, 16)}</option>)}
        </select>
        <label>改成</label>
        <input value={f.value} placeholder="开放推迟两周" onChange={(e) => f.setValue(e.target.value)} />
        <label>情景名</label>
        <input value={f.name} placeholder={f.value.slice(0, 10) || '默认取上面这句话'} onChange={(e) => f.setName(e.target.value)} />
        <button className="pg-pick" disabled={!f.value.trim()} onClick={() => f.setDone(true)}>分叉</button>
        {f.done && <div className="sc-hint">已演示：会从「{fullName(versions, f.from)}」分出「{f.name || f.value.slice(0, 10)}」</div>}
      </aside>
    </div>
  );
}

// ---- 页面 ----------------------------------------------------------------

const GROUNDS: Ground[] = [
  { key: 'list', title: '情景列表', question: '好几个情景放在哪、怎么切换？',
    A: { name: '分段胶囊', desc: '一排胶囊，像 Robinhood 的 1D / 1W / 1M；叠加的写成「A › + 停产」', render: (v) => <Segmented versions={v} /> },
    B: { name: '版本树', desc: '左边一棵小树，看得出谁从谁长出来；数字是这一层受挑战的个数', render: (v) => <Tree versions={v} /> } },
  { key: 'compare', title: '怎么比较', question: '两个情景（都从基线出发）怎么一起看？',
    A: { name: '一张图叠色', desc: '在基线上按情景上色：橙 = A，蓝 = B，紫 = 两个都受挑战', render: (v) => <Overlay versions={v} /> },
    B: { name: '左右并排', desc: '两张小图并排，各自按自己的情景着色', render: (v) => <SideBySide versions={v} /> } },
  { key: 'stack', title: '叠加后的着色', question: '在 A 上再改一处，颜色以谁为准？',
    A: { name: '相对上一层', desc: '只亮这一层新受挑战的（后端现在给的就是这个）', render: (v) => <Relative versions={v} /> },
    B: { name: '相对基线（累计）', desc: '一路叠下来受挑战的全亮（需要后端新增「对基线」的结果）', render: (v) => <Cumulative versions={v} /> } },
  { key: 'summary', title: '情景摘要', question: '不点进去，怎么一眼看出每个情景的影响？',
    A: { name: '大数字卡片', desc: 'Robinhood 式：一个大数字 + 支持度怎么变 + gate', render: (v) => <BigNumber versions={v} /> },
    B: { name: '表盘点阵', desc: 'Apple Watch 式：每个情景一个缩略点阵，形状就是这张图', render: (v) => <WatchFaces versions={v} /> } },
  { key: 'create', title: '新建情景', question: '在当前看的情景上「再假如一次」，入口长什么样？',
    A: { name: '灵动岛', desc: '底部一颗「＋ 假如…」胶囊，点开原地展开成小表单；默认在当前情景上叠加', render: (v) => <Island versions={v} /> },
    B: { name: '侧边表单', desc: '右侧固定表单，明确选「从哪个版本出发」，可以起名', render: (v) => <SideForm versions={v} /> } },
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
  if (!fx) return <div className="pg">加载 fixture…</div>;
  const g = GROUNDS[active];
  const summary = GROUNDS.map((x, i) => `${i + 1}${picks[x.key] ?? '?'} ${x.title}：${picks[x.key] ? x[picks[x.key]].name : '未选'}`).join('；');
  const versions = fx.versions;

  return (
    <div className="pg">
      <header className="pg-head">
        <a href="#" className="pg-back">← 回到应用</a>
        <a href="#playground" className="pg-back">节点视觉 playground</a>
        <strong>多情景 playground</strong>
        <nav className="pg-nav">
          {GROUNDS.map((x, i) => (
            <button key={x.key} className={i === active ? 'on' : ''} onClick={() => setActive(i)}>
              {i + 1} {x.title}{picks[x.key] ? ` · ${picks[x.key]}` : ''}
            </button>
          ))}
        </nav>
      </header>
      <div className="pg-q">
        <h2>{active + 1}. {g.question}</h2>
        <span className="pg-note">数据：fixtures/c1_multi.json（{chain(versions, Object.keys(versions).at(-1)!).length} 层）。情景名是演示用的，后端还没有 name 字段。这一页不调后端。</span>
      </div>
      <div className="pg-ab">
        {(['A', 'B'] as Pick[]).map((p) => (
          <section key={p} className={`pg-option${picks[g.key] === p ? ' picked' : ''}`}>
            <div className="pg-option-head">
              <div><strong>{p}　{g[p].name}</strong><div className="pg-sub">{g[p].desc}</div></div>
              <button className="pg-pick" onClick={() => choose(g.key, p)}>{picks[g.key] === p ? '✓ 已选' : '选这个'}</button>
            </div>
            <div className="pg-pane" key={`${g.key}-${p}`}>{g[p].render(versions)}</div>
          </section>
        ))}
      </div>
      <footer className="pg-foot">
        <span>你的选择：{summary}</span>
        <button className="pg-pick" onClick={() => navigator.clipboard?.writeText(summary)}>复制</button>
      </footer>
    </div>
  );
}
