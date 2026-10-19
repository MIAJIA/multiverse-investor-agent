// 右侧面板：详情 · 证据 · 条件。证据 = 入边的 evidence，按 excerpt_id 找片段原文。
import { nodeConditions, nodeEvidence } from '../lookup';
import { ASSESSMENT, EVIDENCE, ROLE } from '../status';
import type { AssessmentStatus, VersionBundle } from '../types';
import Badge from './Badge';
import ConditionRow from './ConditionRow';

type Ref = ReturnType<typeof nodeEvidence>['supporting'][number];

function EvidenceCard({ r }: { r: Ref }) {
  return (
    <div className={`evidence ${r.ref.stance}`}>
      <div className="small muted">
        {r.excerpt?.source ?? r.ref.source_id} · {r.excerpt?.date ?? '日期未知'} · <span className="mono">{r.ref.excerpt_id}</span> · {r.ref.tier}
      </div>
      <div className="quote">{r.excerpt?.text ?? '（资料包里找不到这个片段）'}</div>
      <div className="small">针对：{r.ref.supports}</div>
      {r.ref.stance === 'neutral' && <div className="small muted">背景信息：不支持也不反驳</div>}
      {r.ref.stance === 'contradicts' && (
        <div className="small rebuttal">{r.ref.rebuttal ? `回应：${r.ref.rebuttal}` : '没有回应：接受这条反驳'}</div>
      )}
      <div className="small muted">经由边 {r.edge.id}</div>
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
  const kd = bundle.proposal?.key_dependency;
  const isKey = kd?.claim_id === nodeId || conds.some((c) => c.id === kd?.condition_id);
  const outEdges = graph.edges.filter((e) => e.from === nodeId);
  const name = (id: string) => graph.nodes.find((n) => n.id === id)?.statement ?? id;

  return (
    <aside className="panel">
      <section>
        <h3>详情</h3>
        <div className="small" style={{ color: ROLE[claim.role].color }}>{ROLE[claim.role].label} · <span className="mono">{claim.id}</span></div>
        <p className="statement">{claim.statement}</p>
        {claim.original_statement !== claim.statement && <p className="small muted">原话：{claim.original_statement}</p>}
        <div className="row">
          <Badge look={EVIDENCE[claim.evidence_status]} title="evidence_status" />
          {assessment && <Badge look={ASSESSMENT[assessment]} title="scenario assessment" />}
          {claim.time_bucket && <span className="small muted">{claim.time_bucket}</span>}
        </div>
        {reason && <p className="small">理由：{reason}</p>}
        {isKey && <p className="small key-why">为什么先查这一步：{kd!.why}</p>}
        {ev.inEdges.map((e) => (
          <p key={e.id} className="small">← {name(e.from)}：{e.mechanism}{e.model_only ? '（仅模型推断）' : ''}</p>
        ))}
        {outEdges.map((e) => <p key={e.id} className="small muted">→ {name(e.to)}：{e.mechanism}</p>)}
      </section>
      <section>
        <h3>证据 <span className="small muted">Supporting {ev.supporting.length} · Contradicting {ev.contradicting.length}{ev.background.length ? ` · 背景 ${ev.background.length}` : ''}</span></h3>
        {ev.inEdges.length === 0 && <p className="small muted">证据只挂在边上，这个节点没有入边。</p>}
        {ev.modelOnly && <p className="small muted">仅模型推断：入边没有引用任何资料。</p>}
        {ev.supporting.map((r) => <EvidenceCard key={r.edge.id + r.ref.excerpt_id} r={r} />)}
        {ev.contradicting.map((r) => <EvidenceCard key={r.edge.id + r.ref.excerpt_id} r={r} />)}
        {ev.background.length > 0 && <div className="small muted" style={{ marginTop: 8 }}>背景</div>}
        {ev.background.map((r) => <EvidenceCard key={r.edge.id + r.ref.excerpt_id} r={r} />)}
      </section>
      <section>
        <h3>什么会证明我错？</h3>
        {conds.length === 0 && <p className="small muted">这个节点上没有条件。</p>}
        {conds.map((c) => <ConditionRow key={c.id} c={c} />)}
      </section>
    </aside>
  );
}
