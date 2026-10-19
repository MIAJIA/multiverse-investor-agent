// B2 Sign-off：逐条确认假设 + 提案卡（可改进场 / 退出条件的阈值与截止）+ 签字。
// 证据状态和用户状态是两列：Confirm 表示「我认这条假设和它的失效条件」，不是「证据成立」。
import { useState } from 'react';
import { nodeConditions } from '../lookup';
import { EVIDENCE, ROLE } from '../status';
import { depths } from '../toFlow';
import type { ConditionOverride, VersionBundle } from '../types';
import Badge from './Badge';
import ProposalCard from './ProposalCard';
import SignDialog from './SignDialog';

export interface SignForm {
  clarified_statement: string;
  criteria: string | null;
  deadline: string | null;
}

type Draft = { confirmedClaimIds: string[]; conditionOverrides: Record<string, ConditionOverride> };

export default function Signoff({ bundle, signoff, busy, onChange, onSign }: {
  bundle: VersionBundle; signoff: Draft; busy: boolean; onChange: (d: Draft) => void; onSign: (f: SignForm) => void;
}) {
  const [open, setOpen] = useState(false);
  const { graph, proposal } = bundle;
  const d = depths(graph);
  const rows = graph.nodes.filter((n) => n.role !== 'event').sort((a, b) => d.get(a.id)! - d.get(b.id)!);
  const signed = proposal?.user_judgment.confirmed ?? false;
  // 签过之后以后端返回的提案为准；签之前是还没提交的勾选
  const confirmed = new Set(signed ? proposal!.user_judgment.confirmed_claim_ids : signoff.confirmedClaimIds);

  const toggle = (id: string) =>
    onChange({ ...signoff, confirmedClaimIds: confirmed.has(id) ? [...confirmed].filter((x) => x !== id) : [...confirmed, id] });
  const override = (id: string, o: ConditionOverride | null) => {
    const next = { ...signoff.conditionOverrides };
    if (o) next[id] = o;
    else delete next[id];
    onChange({ ...signoff, conditionOverrides: next });
  };

  return (
    <div className="page">
      <h2>我签哪几条？ <span className="small muted">{confirmed.size} / {rows.length} confirmed · {graph.version}</span></h2>
      <div className="cols">
        <table className="assumptions">
          <thead>
            <tr><th>假设</th><th>失效条件</th><th>证据状态</th><th>用户状态</th></tr>
          </thead>
          <tbody>
            {rows.map((n) => (
              <tr key={n.id}>
                <td>
                  <div className="small" style={{ color: ROLE[n.role].color }}>{ROLE[n.role].label}</div>
                  {n.statement}
                </td>
                <td className="small">
                  {nodeConditions(graph, n.id).map((c) => <div key={c.id}>{c.rule}（截止 {c.deadline}）</div>)}
                  {nodeConditions(graph, n.id).length === 0 && <span className="muted">—</span>}
                </td>
                <td><Badge look={EVIDENCE[n.evidence_status]} /></td>
                <td>
                  <label className="small">
                    <input type="checkbox" checked={confirmed.has(n.id)} disabled={signed} onChange={() => toggle(n.id)} />{' '}
                    {confirmed.has(n.id) ? 'Confirmed' : 'Not started'}
                  </label>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div>
          {proposal ? (
            <>
              <ProposalCard proposal={proposal} graph={graph}
                overrides={signed ? undefined : signoff.conditionOverrides} onOverride={signed ? undefined : override} />
              <button className="primary" disabled={busy || signed} onClick={() => setOpen(true)}>
                {signed ? '已签' : 'Sign'}
              </button>
              <div className="sign-note">签的是研究判断，不是下单。这里没有执行按钮。</div>
            </>
          ) : <p className="muted">这个版本没有提案。</p>}
        </div>
      </div>
      {open && proposal && (
        <SignDialog uj={proposal.user_judgment} busy={busy} onCancel={() => setOpen(false)}
          onSubmit={(f) => { setOpen(false); onSign(f); }} />
      )}
    </div>
  );
}
