// 节点视觉 A/B（/#grammar）：一个视觉通道只回答一个问题。两种做法共用同一套通道分工，只在「类型怎么认、结论什么形状」上不同。
// 数据是方案 B 预览的演示版本包（c1_multi 的 c1-v3 + 少量手改），不调后端；铅笔只弹提示。
import { Background, Controls, ReactFlow, type Edge, type Node } from '@xyflow/react';
import { useEffect, useMemo, useState } from 'react';
import { ancestors, keyClaimIds } from '../../lookup';
import { strength } from '../../node/strength';
import { demoBundle } from '../../preview/demoPlanB';
import { T } from '../../strings';
import { toFlow } from '../../toFlow';
import type { BranchKind, Claim, Fixture, VersionBundle } from '../../types';
import { demoLabel } from '../demoLabels';
import GrammarNode, { Evidence, KeyBadge, LINE, type GrammarData, type Variant } from './GrammarNode';
import { Pencil, TYPE_ICON } from './Icons';
import './grammar.css';

const nodeTypes = { g: GrammarNode };
const PICK_KEY = 'catalyst.grammar.pick';
const ROLES: Claim['role'][] = ['event', 'shock', 'intermediate', 'assumption', 'terminal'];
const KINDS: BranchKind[] = ['evidenced', 'model_only', 'hypothetical'];

function readPick(): Variant | null {
  try { const v = localStorage.getItem(PICK_KEY); return v === 'A' || v === 'B' ? v : null; } catch { return null; }
}

export default function NodeGrammar() {
  const [bundle, setBundle] = useState<VersionBundle | null>(null);
  const [variant, setVariant] = useState<Variant>(() => readPick() ?? 'A');
  const [picked, setPicked] = useState<Variant | null>(readPick);
  const [focus, setFocus] = useState<string | null>(null);
  const [hint, setHint] = useState<string | null>(null);
  useEffect(() => {
    import('../../../fixtures/c1_multi.json').then((m) => setBundle(demoBundle(m.default as unknown as Fixture)));
  }, []);
  const pick = (v: Variant) => {
    setPicked(v);
    try { localStorage.setItem(PICK_KEY, v); } catch { /* 只是记住选择，存不了就算了 */ }
  };

  const { nodes, edges } = useMemo(() => {
    if (!bundle) return { nodes: [], edges: [] };
    const { graph, excerpts } = bundle;
    const keys = new Set(keyClaimIds(bundle));
    const flow = toFlow(graph, { keyClaimIds: [...keys] });
    const lit = focus ? new Set([...ancestors(graph, focus), focus]) : null;
    const nodes: Node<GrammarData>[] = flow.nodes.map((n) => {
      const claim = n.data.claim;
      return {
        id: n.id, type: 'g', position: { x: n.position.x * 0.9, y: n.position.y * 0.72 },
        data: {
          claim, label: demoLabel(claim), variant, kind: bundle.node_kinds[claim.id] ?? 'model_only',
          s: strength(graph, claim.id, excerpts), isKey: keys.has(claim.id), dimmed: !!lit && !lit.has(claim.id),
          onEdit: (_c, label) => setHint(T.grammar.editHint(label)),
        },
      };
    });
    const edges: Edge[] = flow.edges.map((e) => {
      const kind = bundle.edge_kinds[e.id] ?? 'model_only';
      return {
        id: e.id, source: e.source, target: e.target,
        style: { stroke: '#8a919c', strokeWidth: 1.4, strokeDasharray: LINE[kind].dash, opacity: lit && !(lit.has(e.source) && lit.has(e.target)) ? 0.15 : 1 },
      };
    });
    return { nodes, edges };
  }, [bundle, variant, focus]);

  const sampleStrength = { support: 3, contra: 1, neutral: 0, modelOnly: false, noInEdges: false, slots: [] };

  return (
    <div className="gr-page">
      <header className="gr-header">
        <div>
          <h1>{T.grammar.title}</h1>
          <p>{T.grammar.intro}</p>
        </div>
        <a href="#" className="gr-back">{T.app.brand}</a>
      </header>
      <div className="gr-options">
        {(['A', 'B'] as Variant[]).map((v) => (
          <div key={v} className={`gr-option${variant === v ? ' on' : ''}`} onClick={() => setVariant(v)}>
            <div className="gr-option-top">
              <strong>{v === 'A' ? T.grammar.optA : T.grammar.optB}</strong>
              <button className={picked === v ? 'gr-pick done' : 'gr-pick'} onClick={(e) => { e.stopPropagation(); setVariant(v); pick(v); }}>
                {picked === v ? T.grammar.picked : T.grammar.pick}
              </button>
            </div>
            <span>{v === 'A' ? T.grammar.optADesc : T.grammar.optBDesc}</span>
          </div>
        ))}
      </div>
      <div className="gr-body">
        <div className="gr-canvas">
          <ReactFlow key={variant} nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView fitViewOptions={{ padding: 0.1 }}
            nodesDraggable={false} nodesConnectable={false} edgesFocusable={false} proOptions={{ hideAttribution: true }}
            onNodeClick={(_, n) => { if ((n.data as GrammarData).claim.role === 'terminal') setFocus(n.id === focus ? null : n.id); }}
            onPaneClick={() => setFocus(null)}>
            <Background gap={24} />
            <Controls showInteractive={false} />
          </ReactFlow>
          <div className="gr-float">{T.grammar.clickHint}</div>
          {hint && <div className="gr-toast" onClick={() => setHint(null)}><Pencil size={14} /> {hint}</div>}
        </div>
        <aside className="gr-legend">
          <h3>{T.grammar.legendTitle}</h3>
          <section>
            <h4>{T.grammar.qType}</h4>
            {ROLES.map((r) => {
              const Icon = TYPE_ICON[r];
              return <div key={r} className="gr-li"><span className={variant === 'A' ? 'gn-badge' : 'gr-plain-icon'}><Icon size={14} /></span>{T.grammar.type[r]}</div>;
            })}
          </section>
          <section>
            <h4>{T.grammar.qShape}</h4>
            <div className="gr-li">
              {variant === 'A' ? <span className="gr-swatch-pill" /> : <span className="gr-swatch-head" />}
              {variant === 'A' ? T.grammar.shapeA : T.grammar.shapeB}
            </div>
          </section>
          <section>
            <h4>{T.grammar.qKind}</h4>
            {KINDS.map((k) => <div key={k} className="gr-li"><span className="gr-swatch-line" style={{ borderStyle: LINE[k].border }} />{T.grammar.kind[k]}</div>)}
          </section>
          <section>
            <h4>{T.grammar.qEvidence}</h4>
            <div className="gr-li"><Evidence s={sampleStrength} /></div>
            <div className="gr-li small">{T.grammar.evidence}</div>
          </section>
          <section>
            <h4>{T.grammar.qKey}</h4>
            <div className="gr-li"><KeyBadge /></div>
            <div className="gr-li small">{T.grammar.keyLegend}</div>
          </section>
          <section>
            <h4>{T.grammar.qEdit}</h4>
            <div className="gr-li"><span className="gn-pencil static"><Pencil size={13} /></span></div>
            <div className="gr-li small">{T.grammar.edit}</div>
          </section>
          <p className="gr-removed">{T.grammar.removed}</p>
          <p className="gr-removed">{T.grammar.demo}</p>
        </aside>
      </div>
    </div>
  );
}
