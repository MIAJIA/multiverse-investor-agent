// 节点视觉 playground：五个维度，每个维度两种做法并排，用真实 fixture 渲染。打开方式：/#playground
// 每次只变一个维度，其余维度用你已经选过的（没选过就用 A）。
import { Background, ReactFlow, type Edge, type Node } from '@xyflow/react';
import { useEffect, useMemo, useState } from 'react';
import { changedTargets, keyClaimId, nodeConditions } from '../lookup';
import { toFlow } from '../toFlow';
import type { Fixture, VersionBundle } from '../types';
import DesignNode, { type DesignData, type Look } from '../node/DesignNode';
import { shortLabel } from '../node/labels';
import { strength } from '../node/strength';
import { Bars, Ring } from '../node/StrengthGlyph';
import './playground.css';

type Key = keyof Look;
type Pick = 'A' | 'B';

interface Option { value: Look[Key]; name: string; desc: string }
interface Ground { key: Key; title: string; question: string; scenario?: boolean; select?: string; A: Option; B: Option }

const GROUNDS: Ground[] = [
  {
    key: 'shape', title: '节点形态', question: '节点平时长什么样？',
    A: { value: 'pill', name: '胶囊', desc: '一行短标题 + 证据符号，像灵动岛收起的样子' },
    B: { value: 'card', name: '小卡片', desc: '两行：短标题，下面一行小字写正方几条、反方几条' },
  },
  {
    key: 'strength', title: '证据强弱', question: '怎么一眼看出证据强不强、有没有反方？',
    A: { value: 'ring', name: '圆环', desc: '3 格圆环，亮几格 = 几条引用，反方是红格（像 Activity 圆环）' },
    B: { value: 'bars', name: '信号格', desc: '3 根信号格 = 正方引用条数，反方是右上角的红色数字（像手机信号）' },
  },
  {
    key: 'color', title: '颜色', question: '颜色用来表示什么？',
    A: { value: 'state', name: '只表示状态', desc: '平时全是白底，只有关键依赖、反方、受挑战才有颜色' },
    B: { value: 'role', name: '类型 + 状态', desc: '事件蓝、假设绿、终点紫的淡底色，状态再叠一层描边' },
  },
  {
    key: 'expand', title: '点开节点', question: '点一个节点，信息出现在哪？', select: 'c1.laser_demand',
    A: { value: 'inline', name: '原地展开', desc: '节点自己变大，像灵动岛展开；视线不用离开' },
    B: { value: 'panel', name: '侧边面板', desc: '节点不变，信息出现在右边的面板里（现在的做法）' },
  },
  {
    key: 'scenario', title: '情景着色（B3）', question: '改了一个假设之后，怎么看出哪里受影响？', scenario: true,
    A: { value: 'dim', name: '其余退后', desc: '受挑战的亮起来，没受影响的变淡' },
    B: { value: 'path', name: '标出传导路径', desc: '受挑战的亮起来，传导的连线标橙，其余保持原样' },
  },
];

const DEFAULT: Look = { shape: 'pill', strength: 'ring', color: 'state', expand: 'inline', scenario: 'dim' };
const STORE = 'catalyst.playground.picks';
const nodeTypes = { design: DesignNode };

function loadPicks(): Partial<Record<Key, Pick>> {
  try {
    return JSON.parse(localStorage.getItem(STORE) ?? '{}');
  } catch {
    return {};
  }
}

function lookFor(picks: Partial<Record<Key, Pick>>, override?: [Key, Look[Key]]): Look {
  const look = { ...DEFAULT } as Record<Key, string>;
  for (const g of GROUNDS) if (picks[g.key]) look[g.key] = g[picks[g.key]!].value;
  if (override) look[override[0]] = override[1];
  return look as unknown as Look;
}

function Pane({ bundle, look, scenario, initial }: {
  bundle: VersionBundle; look: Look; scenario: boolean; initial?: string;
}) {
  const [selected, setSelected] = useState<string | null>(initial ?? null);
  const sc = scenario ? bundle.scenario : null;
  const changed = changedTargets(sc);
  const key = keyClaimId(bundle.proposal, bundle.graph);

  const { nodes, edges } = useMemo(() => {
    const flow = toFlow(bundle.graph);
    const lit = (id: string) => sc?.assessment[id] === 'challenged' || changed.includes(id);
    const nodes: Node<DesignData>[] = flow.nodes.map((n) => {
      const claim = n.data.claim;
      const expanded = look.expand === 'inline' && selected === claim.id;
      return {
        // 新节点比原来的卡片矮，层距收紧，fitView 才能把节点放大到看得清
        id: n.id, type: 'design', zIndex: expanded ? 10 : 0,
        position: { x: n.position.x * 0.85, y: n.position.y * (look.shape === 'pill' ? 0.55 : 0.7) },
        data: {
          claim, look, label: shortLabel(claim.id, claim.statement, changed.includes(claim.id)),
          s: strength(bundle.graph, claim.id, bundle.excerpts), conditions: nodeConditions(bundle.graph, claim.id),
          isKey: claim.id === key, isChanged: changed.includes(claim.id), assessment: sc?.assessment[claim.id], expanded,
        },
      };
    });
    const edges: Edge[] = flow.edges.map((e) => {
      const path = sc && look.scenario === 'path' && lit(e.source) && sc.assessment[e.target] === 'challenged';
      const faded = sc && look.scenario === 'dim' && !(lit(e.source) && lit(e.target));
      return {
        id: e.id, source: e.source, target: e.target,
        style: {
          stroke: path ? 'var(--pg-orange)' : 'var(--pg-edge)', strokeWidth: path ? 2.5 : 1.2,
          strokeDasharray: e.data?.modelOnly ? '5 4' : undefined, opacity: faded ? 0.25 : 1,
        },
      };
    });
    return { nodes, edges };
  }, [bundle, look, sc, selected, key, changed.join()]);

  const sel = selected ? bundle.graph.nodes.find((n) => n.id === selected) : null;
  const s = sel ? strength(bundle.graph, sel.id, bundle.excerpts) : null;
  return (
    <div className="pg-pane">
      <div className="pg-canvas">
        <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView fitViewOptions={{ padding: 0.12 }}
          nodesDraggable={false} nodesConnectable={false} proOptions={{ hideAttribution: true }}
          onNodeClick={(_, n) => setSelected(n.id === selected ? null : n.id)} onPaneClick={() => setSelected(null)}>
          <Background gap={22} color="var(--pg-grid)" />
        </ReactFlow>
      </div>
      {look.expand === 'panel' && (
        <aside className="pg-side">
          {sel && s ? (
            <>
              <div className="pg-row">{look.strength === 'ring' ? <Ring s={s} size={30} /> : <Bars s={s} />}
                <div className="pg-title">{shortLabel(sel.id, sel.statement, changed.includes(sel.id))}</div></div>
              <p className="pg-sub">{sel.statement}</p>
              <p className="pg-sub">{s.noInEdges ? '没有入边证据' : s.modelOnly ? '仅模型推断' : `正方 ${s.support} · 反方 ${s.contra}`}</p>
              {nodeConditions(bundle.graph, sel.id).map((c) => <p key={c.id} className="pg-sub">截止 {c.deadline}</p>)}
            </>
          ) : <p className="pg-sub">点一个节点</p>}
        </aside>
      )}
    </div>
  );
}

export default function Playground() {
  const [fx, setFx] = useState<Fixture | null>(null);
  const [picks, setPicks] = useState<Partial<Record<Key, Pick>>>(loadPicks);
  const [active, setActive] = useState(0);
  useEffect(() => {
    import('../../fixtures/c1.json').then((m) => setFx(m.default as unknown as Fixture));
  }, []);
  const choose = (k: Key, p: Pick) => {
    const next = { ...picks, [k]: p };
    setPicks(next);
    try { localStorage.setItem(STORE, JSON.stringify(next)); } catch { /* 无痕模式等：不记住也能用 */ }
  };

  if (!fx) return <div className="pg">加载 fixture…</div>;
  const g = GROUNDS[active];
  const base = Object.values(fx.versions).find((b) => !b.scenario)!;
  const scen = Object.values(fx.versions).find((b) => b.scenario) ?? base;
  const bundle = g.scenario ? scen : base;
  const summary = GROUNDS.map((x, i) => `${i + 1}${picks[x.key] ?? '?'} ${x.title}：${picks[x.key] ? x[picks[x.key]!].name : '未选'}`).join('；');

  return (
    <div className="pg">
      <header className="pg-head">
        <a href="#" className="pg-back">← 回到应用</a>
        <strong>节点视觉 playground</strong>
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
        <span className="pg-note">每次只变这一项，其余用你已选的（没选的用 A）。短标题是演示用的，正式版需要后端给 label 字段。数据：fixture c1{g.scenario ? '，情景 c1-v2' : ''}。</span>
      </div>
      <div className="pg-ab">
        {(['A', 'B'] as Pick[]).map((p) => (
          <section key={p} className={`pg-option${picks[g.key] === p ? ' picked' : ''}`}>
            <div className="pg-option-head">
              <div><strong>{p}　{g[p].name}</strong><div className="pg-sub">{g[p].desc}</div></div>
              <button className="pg-pick" onClick={() => choose(g.key, p)}>{picks[g.key] === p ? '✓ 已选' : '选这个'}</button>
            </div>
            <Pane key={`${g.key}-${p}-${JSON.stringify(picks)}`} bundle={bundle} scenario={!!g.scenario}
              look={lookFor(picks, [g.key, g[p].value])} initial={g.select} />
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
