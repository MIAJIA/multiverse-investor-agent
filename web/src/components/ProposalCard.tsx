// 提案卡：status 和 gate 两个徽章分开；进场标「且」，退出显式标 exit_logic。没有执行按钮。
import { EXIT_LOGIC, GATE, PROPOSAL_STATUS, SUPPORT } from '../status';
import type { Condition, ConditionOverride, Graph, TradeProposal } from '../types';
import Badge from './Badge';
import ConditionRow from './ConditionRow';

export default function ProposalCard({ proposal, graph, overrides, onOverride, compact }: {
  proposal: TradeProposal; graph: Graph; compact?: boolean;
  overrides?: Record<string, ConditionOverride>; onOverride?: (id: string, o: ConditionOverride | null) => void;
}) {
  const { direction: d, user_judgment: uj, key_dependency: kd } = proposal;
  const name = (id: string | null) => graph.nodes.find((n) => n.id === id)?.statement ?? id;
  const kdClaim = kd?.claim_id ?? graph.conditions.find((c) => c.id === kd?.condition_id)?.claim_id ?? null;
  const rows = (cs: Condition[], joiner: string) =>
    cs.map((c, i) => (
      <div key={c.id}>
        {i > 0 && <div className="joiner">{joiner}</div>}
        <div className="small muted">{name(c.claim_id)}</div>
        <ConditionRow c={c} override={overrides?.[c.id]} onOverride={onOverride && ((o) => onOverride(c.id, o))} />
      </div>
    ));
  return (
    <div className="proposal">
      <h3>{d.side === 'long' ? '看多' : '看空'} {d.instrument}{d.horizon_days ? ` · ${d.horizon_days} 天` : ''}</h3>
      {d.note && <div className="small muted">{d.note}</div>}
      <div className="row big-badges" style={{ marginTop: 8 }}>
        <Badge look={PROPOSAL_STATUS[proposal.status]} title="status" />
        <Badge look={GATE[proposal.gate]} title="gate" />
        <Badge look={SUPPORT[proposal.support_status]} title="support_status" />
        {uj.confirmed && <span className="signed">✓ 已签</span>}
      </div>
      {kd && (
        <p className="small key-why">关键依赖：{name(kdClaim)} — {kd.why}</p>
      )}
      {!compact && (
        <>
          <h4>进场条件（全部满足才进入复核：且）</h4>
          {rows(proposal.entry_conditions, '且')}
          <h4>退出条件 · <Badge look={EXIT_LOGIC[proposal.exit_logic]} /></h4>
          {rows(proposal.exit_conditions, proposal.exit_logic === 'ANY' ? '或' : '且')}
          <h4>研究判断</h4>
          <p className="small">{uj.clarified_statement}</p>
          {uj.requires_user_confirmation && uj.original_statement !== uj.clarified_statement && (
            <p className="small muted">原话：{uj.original_statement}（改写过，需要你确认）</p>
          )}
          {uj.confirmed && (
            <p className="small">已确认的假设：{uj.confirmed_claim_ids.map(name).join('；') || '无'}
              {uj.criteria && <><br />判定条件：{uj.criteria}</>}{uj.deadline && <><br />期限：{uj.deadline}</>}</p>
          )}
        </>
      )}
      <div className="small muted mono">graph {proposal.graph_version} · {proposal.meta.proposal_version} · approval_required</div>
    </div>
  );
}
