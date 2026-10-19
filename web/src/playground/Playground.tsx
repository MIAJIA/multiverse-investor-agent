// 节点视觉 playground：五个维度，每个维度两种做法并排，用真实 fixture 渲染。打开方式：/#playground
// 每次只变一个维度，其余维度用你已经选过的（没选过就用 A）。
import { Background, ReactFlow, type Edge, type Node } from '@xyflow/react';
import { useEffect, useMemo, useState } from 'react';
import { changedTargets, keyClaimId, nodeConditions } from '../lookup';
import { toFlow } from '../toFlow';
import type { Fixture, VersionBundle } from '../types';
import DesignNode, { type DesignData, type Look } from '../node/DesignNode';
import { demoLabel } from './demoLabels';
import { strength } from '../node/strength';
import { Bars, Ring } from '../node/StrengthGlyph';
import './playground.css';
import { T } from '../strings';

type Key = keyof Look;
type Pick = 'A' | 'B';

interface Option { value: Look[Key]; name: string; desc: string }
interface Ground { key: Key; title: string; question: string; scenario?: boolean; select?: string; A: Option; B: Option }

const GROUNDS: Ground[] = [
  {
    key: 'shape', ...T.pgNode.shape, A: { value: 'pill', ...T.pgNode.shape.A }, B: { value: 'card', ...T.pgNode.shape.B },
  },
  {
    key: 'strength', ...T.pgNode.strength, A: { value: 'ring', ...T.pgNode.strength.A }, B: { value: 'bars', ...T.pgNode.strength.B },
  },
  {
    key: 'color', ...T.pgNode.color, A: { value: 'state', ...T.pgNode.color.A }, B: { value: 'role', ...T.pgNode.color.B },
  },
  {
    key: 'expand', ...T.pgNode.expand, select: 'c1.laser_demand',
    A: { value: 'inline', ...T.pgNode.expand.A }, B: { value: 'panel', ...T.pgNode.expand.B },
  },
  {
    key: 'scenario', ...T.pgNode.scenario, scenario: true,
    A: { value: 'dim', ...T.pgNode.scenario.A }, B: { value: 'path', ...T.pgNode.scenario.B },
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
  const key = keyClaimId(bundle.proposals[0], bundle.graph); // 演示页：只标第一份计划的关键依赖

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
          claim, look, label: demoLabel(claim, changed.includes(claim.id)),
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
                <div className="pg-title">{demoLabel(sel, changed.includes(sel.id))}</div></div>
              <p className="pg-sub">{sel.statement}</p>
              <p className="pg-sub">{s.noInEdges ? T.node.noInEdges : s.modelOnly ? T.node.modelOnly : T.pgNode.supportContra(s.support, s.contra)}</p>
              {nodeConditions(bundle.graph, sel.id).map((c) => <p key={c.id} className="pg-sub">{T.node.deadline(c.deadline)}</p>)}
            </>
          ) : <p className="pg-sub">{T.pg.clickNode}</p>}
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

  if (!fx) return <div className="pg">{T.pg.loading}</div>;
  const g = GROUNDS[active];
  const base = Object.values(fx.versions).find((b) => !b.scenario)!;
  const scen = Object.values(fx.versions).find((b) => b.scenario) ?? base;
  const bundle = g.scenario ? scen : base;
  const summary = GROUNDS.map((x, i) => T.pg.summaryItem(i + 1, picks[x.key], x.title, picks[x.key] ? x[picks[x.key]!].name : null)).join(T.pg.summarySep);

  return (
    <div className="pg">
      <header className="pg-head">
        <a href="#" className="pg-back">{T.pg.back}</a>
        <a href="#scenarios" className="pg-back">{T.pgNode.linkScenarios}</a>
        <strong>{T.pgNode.title}</strong>
        <nav className="pg-nav">
          {GROUNDS.map((x, i) => (
            <button key={x.key} className={i === active ? 'on' : ''} onClick={() => setActive(i)}>
              {T.pg.navItem(i + 1, x.title, picks[x.key])}
            </button>
          ))}
        </nav>
      </header>
      <div className="pg-q">
        <h2>{T.pg.question(active + 1, g.question)}</h2>
        <span className="pg-note">{T.pgNode.note(!!g.scenario)}</span>
      </div>
      <div className="pg-ab">
        {(['A', 'B'] as Pick[]).map((p) => (
          <section key={p} className={`pg-option${picks[g.key] === p ? ' picked' : ''}`}>
            <div className="pg-option-head">
              <div><strong>{T.pg.optionTitle(p, g[p].name)}</strong><div className="pg-sub">{g[p].desc}</div></div>
              <button className="pg-pick" onClick={() => choose(g.key, p)}>{picks[g.key] === p ? T.pg.picked : T.pg.pick}</button>
            </div>
            <Pane key={`${g.key}-${p}-${JSON.stringify(picks)}`} bundle={bundle} scenario={!!g.scenario}
              look={lookFor(picks, [g.key, g[p].value])} initial={g.select} />
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
