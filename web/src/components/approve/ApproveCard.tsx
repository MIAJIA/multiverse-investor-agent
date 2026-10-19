// B2 精简版 B：OpenEvidence 答案卡。顶部一排胶囊切换结论（像 Robinhood 的 1D / 1W）；下面只有一张卡：大标题 + 前提（带引用）+ 信号；底部是批准胶囊。
import { BRANCH_KIND, GATE } from '../../status';
import { T } from '../../strings';
import { EMPTY_DRAFT } from '../ApprovePlans';
import { BranchTag } from '../BranchSwatch';
import { approveModel, type ApproveProps } from './model';
import { ApproveIsland, PlanDetail, UnderstoodPill } from './Pieces';

export default function ApproveCard(props: ApproveProps) {
  const { bundle, onSelect, drafts, onDraft, understood, onUnderstood, onApprove, onRevoke, busy } = props;
  const m = approveModel(props);
  if (!m.uj) return <p className="ap-muted">{T.approve.noPlans}</p>;
  const plan = m.current ?? m.approved ?? m.rows[0];
  const b = m.branchOf(plan);
  const shock = b?.own_node_ids.map(m.node).find((n) => n.role === 'shock');
  const needIdea = m.uj.requires_user_confirmation && !understood.confirmed;
  return (
    <div className="ap-page">
      <UnderstoodPill text={m.uj.clarified_statement} needed={m.uj.requires_user_confirmation}
        understood={understood} onUnderstood={onUnderstood} />
      <div className="ap-seg" role="tablist">
        {m.rows.map((p) => {
          const k = m.branchOf(p)?.kind;
          return (
            <button key={p.terminal_id} role="tab" aria-selected={p === plan} className={p === plan ? 'on' : ''}
              onClick={() => onSelect(p.terminal_id!)}>
              {k && <i className="ap-seg-dot" style={{ borderColor: BRANCH_KIND[k].border, borderStyle: BRANCH_KIND[k].line, background: k === 'evidenced' ? BRANCH_KIND[k].border : BRANCH_KIND[k].bg, backgroundImage: BRANCH_KIND[k].pattern }} />}
              {m.title(p)}
              {p.user_judgment.confirmed && <span className="ap-check">✓</span>}
              {p.approval_reset && <span className="ap-warn-dot" />}
            </button>
          );
        })}
      </div>
      <article className={`ap-card${b?.kind === 'hypothetical' ? ' hypo' : ''}`}>
        <div className="ap-card-top">
          <div>
            <div className="ap-card-big">{T.liteCard.headline(plan.direction.side, plan.direction.instrument)}</div>
            <div className="ap-sub">{m.title(plan)} · {T.liteCard.horizon(plan.direction.horizon_days)}
              {b && b.kind !== 'evidenced' && <> <BranchTag kind={b.kind} synthetic={b.synthetic_evidence} /></>}</div>
          </div>
          {plan.approval_reset ? <span className="ap-state warn">{T.approve.approvalReset}</span>
            : <span className="ap-gate" style={{ color: GATE[plan.gate].color, background: GATE[plan.gate].bg }}>{GATE[plan.gate].label}</span>}
        </div>
        {plan.direction.note && <p className="ap-thesis">{plan.direction.note}</p>}
        {plan.rival_changed && !plan.approval_reset && <div className="ap-row-note">{T.approve.rivalChanged}</div>}
        <PlanDetail bundle={bundle} plan={plan} premises={m.premises(plan)} labelOf={(id) => m.labelOf(m.node(id))}
          hypoWhat={b?.kind === 'hypothetical' ? (shock ? m.labelOf(shock) : '') : null}
          draft={drafts[plan.terminal_id!] ?? EMPTY_DRAFT} onDraft={(d) => onDraft(plan.terminal_id!, d)} />
      </article>
      <ApproveIsland plan={plan} title={m.title(plan)} busy={busy} needIdea={needIdea}
        isApproved={m.approved?.terminal_id === plan.terminal_id}
        approvedTitle={m.approved && m.approved.terminal_id !== plan.terminal_id ? m.title(m.approved) : null}
        draft={drafts[plan.terminal_id!] ?? EMPTY_DRAFT} onDraft={(d) => onDraft(plan.terminal_id!, d)}
        onApprove={() => onApprove(plan.terminal_id!)} onRevoke={onRevoke} />
    </div>
  );
}
