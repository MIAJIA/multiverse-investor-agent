// 右侧面板：详情 · 证据 · 条件。证据 = 入边的 evidence，按 excerpt_id 找片段原文。
import { keyClaimId, nodeConditions, nodeEvidence } from '../lookup';
import { ASSESSMENT, EVIDENCE, ROLE } from '../status';
import type { AssessmentStatus, VersionBundle } from '../types';
import Badge from './Badge';
import ConditionRow from './ConditionRow';
import { T } from '../strings';

type Ref = ReturnType<typeof nodeEvidence>['supporting'][number];

function EvidenceCard({ r }: { r: Ref }) {
  return (
    <div className={`evidence ${r.ref.stance}`}>
      <div className="small muted">
        {r.excerpt?.source ?? r.ref.source_id} · {r.excerpt?.date ?? T.panel.unknownDate} · <span className="mono">{r.ref.excerpt_id}</span> · {r.ref.tier}
      </div>
      <div className="quote">{r.excerpt?.text ?? T.panel.excerptMissing}</div>
      <div className="small">{T.panel.targets(r.ref.supports)}</div>
      {r.ref.stance === 'neutral' && <div className="small muted">{T.panel.neutral}</div>}
      {r.ref.stance === 'contradicts' && (
        <div className="small rebuttal">{r.ref.rebuttal ? T.panel.rebuttal(r.ref.rebuttal) : T.panel.noRebuttal}</div>
      )}
      <div className="small muted">{T.panel.viaEdge(r.edge.id)}</div>
    </div>
  );
}

export default function NodePanel({ bundle, nodeId, assessment, reason }: {
  bundle: VersionBundle; nodeId: string; assessment?: AssessmentStatus; reason?: string;
}) {
  const { graph, excerpts } = bundle;
  const claim = graph.nodes.find((n) => n.id === nodeId);
  if (!claim) return null;
  const ev = nodeEvidence(graph, nodeId, excerpts);
  const conds = nodeConditions(graph, nodeId);
  // 方案 B：几份计划各有关键依赖；列出把这个节点当关键依赖的那几份
  const keyPlans = bundle.proposals.filter((p) => keyClaimId(p, graph) === nodeId);
  const outEdges = graph.edges.filter((e) => e.from === nodeId);
  const name = (id: string) => graph.nodes.find((n) => n.id === id)?.statement ?? id;

  return (
    <aside className="panel">
      <section>
        <h3>{T.panel.details}</h3>
        <div className="small" style={{ color: ROLE[claim.role].color }}>{ROLE[claim.role].label} · <span className="mono">{claim.id}</span></div>
        <p className="statement">{claim.statement}</p>
        {claim.original_statement !== claim.statement && <p className="small muted">{T.panel.original(claim.original_statement)}</p>}
        <div className="row">
          <Badge look={EVIDENCE[claim.evidence_status]} title="evidence_status" />
          {assessment && <Badge look={ASSESSMENT[assessment]} title="scenario assessment" />}
          {claim.time_bucket && <span className="small muted">{claim.time_bucket}</span>}
        </div>
        {reason && <p className="small">{T.panel.reason(reason)}</p>}
        {keyPlans.map((p) => <p key={p.terminal_id} className="small key-why">{T.panelPlan.whyFirstFor(p.direction.instrument, p.key_dependency!.why)}</p>)}
        {ev.inEdges.map((e) => (
          <p key={e.id} className="small">{T.panel.inEdge(name(e.from), e.mechanism, e.model_only)}</p>
        ))}
        {outEdges.map((e) => <p key={e.id} className="small muted">{T.panel.outEdge(name(e.to), e.mechanism)}</p>)}
      </section>
      <section>
        <h3>{T.panel.evidence} <span className="small muted">{T.panel.evidenceCounts(ev.supporting.length, ev.contradicting.length, ev.background.length)}</span></h3>
        {ev.inEdges.length === 0 && <p className="small muted">{T.panel.noInEdges}</p>}
        {ev.modelOnly && <p className="small muted">{T.panel.modelOnly}</p>}
        {ev.supporting.map((r) => <EvidenceCard key={r.edge.id + r.ref.excerpt_id} r={r} />)}
        {ev.contradicting.map((r) => <EvidenceCard key={r.edge.id + r.ref.excerpt_id} r={r} />)}
        {ev.background.length > 0 && <div className="small muted" style={{ marginTop: 8 }}>{T.panel.background}</div>}
        {ev.background.map((r) => <EvidenceCard key={r.edge.id + r.ref.excerpt_id} r={r} />)}
      </section>
      <section>
        <h3>{T.panel.whatProvesWrong}</h3>
        {conds.length === 0 && <p className="small muted">{T.panel.noConditions}</p>}
        {conds.map((c) => <ConditionRow key={c.id} c={c} />)}
      </section>
    </aside>
  );
}
