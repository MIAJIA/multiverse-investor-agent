// 方案 B 视觉预览（/#plan-b）：B1 三类分支 + 点结论高亮整条分支；B2 批准计划。
// 数据是演示的（见 demoPlanB.ts），不调后端；批准 / 撤销只改这一页的内存。后端交付后，正式 B1 / B2 复用这里的组件。
import { useEffect, useMemo, useState } from 'react';
import ApproveCard from '../components/approve/ApproveCard';
import { EMPTY_DRAFT, type PlanDraft, type Understood } from '../components/approve/model';
import Badge from '../components/Badge';
import { BranchTag } from '../components/BranchSwatch';
import GraphCanvas, { type BranchView } from '../components/GraphCanvas';
import NodePanel from '../components/NodePanel';
import { ancestors, keyClaimId } from '../lookup';
import { demoLabel } from '../playground/demoLabels';
import { BRANCH_KIND, GATE } from '../status';
import type { Fixture, PlanBBundle } from '../types';
import { DEMO_NOTE, DEMO_SUBTITLE, demoBundle } from './demoPlanB';
import { T } from '../strings';

type Tab = 'b1' | 'b2';

export default function PlanBPreview() {
  const [bundle, setBundle] = useState<PlanBBundle | null>(null);
  const [tab, setTab] = useState<Tab>('b1');
  const [terminal, setTerminal] = useState<string | null>(null);
  const [nodeId, setNodeId] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, PlanDraft>>({});
  const [understood, setUnderstood] = useState<Understood>({ confirmed: false, text: null });
  const [afterFork, setAfterFork] = useState(false);
  useEffect(() => {
    import('../../fixtures/c1_multi.json').then((m) => setBundle(demoBundle(m.default as unknown as Fixture)));
  }, []);

  const view = useMemo<BranchView | undefined>(() => {
    if (!bundle) return undefined;
    const b = terminal ? bundle.branches.find((x) => x.terminal_id === terminal) : null;
    const nodes = b ? new Set([...b.own_node_ids, ...ancestors(bundle.graph, b.terminal_id)]) : null;
    return {
      nodeKinds: bundle.node_kinds, edgeKinds: bundle.edge_kinds,
      syntheticNodes: new Set(bundle.branches.filter((x) => x.synthetic_evidence).flatMap((x) => x.own_node_ids)),
      highlight: nodes ? { nodes, edges: new Set(bundle.graph.edges.filter((e) => nodes.has(e.from) && nodes.has(e.to)).map((e) => e.id)) } : null,
    };
  }, [bundle, terminal]);

  if (!bundle || !view) return <div className="page">{T.preview.loading}</div>;
  const g = bundle.graph;
  const node = (id: string) => g.nodes.find((n) => n.id === id)!;
  const plan = terminal ? bundle.proposals.find((p) => p.terminal_id === terminal) : null;
  const branch = terminal ? bundle.branches.find((b) => b.terminal_id === terminal) : null;
  // 演示 B3 回来后的样子：已批准的那份被分叉撤销（approval_reset），其余标 rival_changed。真实数据由后端写这两个字段。
  const shown: PlanBBundle = afterFork ? {
    ...bundle,
    proposals: bundle.proposals.map((p) => p.user_judgment.confirmed
      ? { ...p, approval_reset: true, user_judgment: { ...p.user_judgment, confirmed: false } }
      : { ...p, rival_changed: bundle.proposals.some((q) => q.user_judgment.confirmed) }),
  } : bundle;

  const setApproved = (tid: string | null) => {
    setAfterFork(false);
    setBundle({
      ...bundle,
      proposals: bundle.proposals.map((p) => {
        const d = drafts[p.terminal_id!] ?? EMPTY_DRAFT;
        const on = p.terminal_id === tid;
        return {
          ...p, approval_reset: false, rival_changed: false,
          entry_conditions: on ? p.entry_conditions.map((c) => ({ ...c, ...d.overrides[c.id] })) : p.entry_conditions,
          user_judgment: {
            ...p.user_judgment, confirmed: on, note: on ? d.note || null : null,
            confirmed_claim_ids: on ? d.confirmedClaimIds : [],
            clarified_statement: understood.text ?? p.user_judgment.clarified_statement,
          },
        };
      }),
    });
  };

  return (
    <div className="app">
      <header className="header">
        <a href="#" className="small" style={{ color: '#aab4c8' }}>{T.preview.back}</a>
        <strong className="brand">{T.preview.title}</strong>
        <span className="small" style={{ color: '#aab4c8' }}>{g.version} · {DEMO_SUBTITLE}</span>
        <span className="spacer" />
        <span className="badge mock">{DEMO_NOTE}</span>
      </header>
      <nav className="tabs">
        <button className={tab === 'b1' ? 'tab active' : 'tab'} onClick={() => setTab('b1')}>{T.preview.tabB1}</button>
        <button className={tab === 'b2' ? 'tab active' : 'tab'} onClick={() => setTab('b2')}>{T.preview.tabB2}</button>
        <span className="spacer" />
        <label className="small muted" style={{ alignSelf: 'center' }}>
          <input type="checkbox" checked={afterFork} onChange={(e) => setAfterFork(e.target.checked)} /> {T.preview.afterFork}
        </label>
      </nav>
      <main className="main">
        {tab === 'b1' && (
          <div className="split">
            <div className="col">
              <div className="legend">
                {(['evidenced', 'model_only', 'hypothetical'] as const).map((k) => (
                  <span key={k} className="legend-item">
                    <span className="legend-node" style={{
                      borderColor: BRANCH_KIND[k].border, borderStyle: BRANCH_KIND[k].line,
                      background: k === 'evidenced' ? '#e6f4ec' : BRANCH_KIND[k].bg, backgroundImage: BRANCH_KIND[k].pattern,
                    }} />{BRANCH_KIND[k].label}
                  </span>
                ))}
                <span className="small muted">{T.preview.highlightHint}</span>
              </div>
              <GraphCanvas bundle={{ graph: g, excerpts: bundle.excerpts }} branchView={view} labelOf={demoLabel}
                opts={{ keyClaimId: keyClaimId(plan ?? bundle.proposals[0], g) }}
                selectedNodeId={nodeId ?? terminal}
                onSelect={(id) => {
                  if (id && node(id).role === 'terminal') { setTerminal(id); setNodeId(null); }
                  else { setNodeId(id); if (!id) setTerminal(null); }
                }} />
            </div>
            {plan && branch && !nodeId ? (
              <aside className="panel">
                <h3>{demoLabel(node(plan.terminal_id!))} <BranchTag kind={branch.kind} synthetic={branch.synthetic_evidence} /></h3>
                <p className="small">{T.preview.direction(plan.direction.side)} <b>{plan.direction.instrument}</b> · {plan.direction.note}</p>
                <div className="row"><Badge look={GATE[plan.gate]} />{plan.user_judgment.confirmed && <span className="ok small">{T.preview.approved}</span>}</div>
                <p className="small">{T.preview.youNeedToBelieve(branch.own_node_ids.filter((id) => id !== plan.terminal_id).map((id) => demoLabel(node(id))))}</p>
                {plan.key_dependency && <p className="small key-why">{T.preview.checkFirst(plan.key_dependency.why)}</p>}
                <button className="primary" onClick={() => setTab('b2')}>{T.preview.goApprove}</button>
              </aside>
            ) : nodeId ? (
              <NodePanel bundle={bundle} nodeId={nodeId} />
            ) : (
              <aside className="panel">
                <p className="muted">{T.preview.intro}</p>
                {bundle.branches.map((b) => (
                  <p key={b.terminal_id} className="small">
                    <button className="link" onClick={() => setTerminal(b.terminal_id)}>{demoLabel(node(b.terminal_id))}</button>{' '}
                    <BranchTag kind={b.kind} synthetic={b.synthetic_evidence} />{b.kind === 'evidenced' && <span className="muted">{BRANCH_KIND.evidenced.label}</span>}
                  </p>
                ))}
                <p className="small muted">{T.preview.legend}</p>
              </aside>
            )}
          </div>
        )}
        {tab === 'b2' && (
          (() => {
            const p = {
              bundle: shown, selected: terminal, onSelect: (id: string) => setTerminal(id || null), labelOf: demoLabel,
              drafts, onDraft: (tid: string, d: PlanDraft) => setDrafts({ ...drafts, [tid]: d }),
              understood, onUnderstood: setUnderstood,
              onApprove: (tid: string) => setApproved(tid), onRevoke: () => setApproved(null), busy: false,
            };
            return <ApproveCard {...p} />;
          })()
        )}
      </main>
    </div>
  );
}
