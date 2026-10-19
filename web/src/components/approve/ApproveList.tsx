// B2 精简版 A：Robinhood 式。一个大标题 + 一行一个结论（名字、标的、一个状态）；点一行原地展开计划；底部是批准胶囊。
import { GATE } from '../../status';
import { T } from '../../strings';
import { EMPTY_DRAFT } from '../ApprovePlans';
import { BranchBar, BranchTag } from '../BranchSwatch';
import { approveModel, type ApproveProps } from './model';
import { ApproveIsland, PlanDetail, UnderstoodPill } from './Pieces';

export default function ApproveList(props: ApproveProps) {
  const { bundle, onSelect, drafts, onDraft, understood, onUnderstood, onApprove, onRevoke, busy } = props;
  const m = approveModel(props);
  if (!m.uj) return <p className="ap-muted">{T.approve.noPlans}</p>;
  const needIdea = m.uj.requires_user_confirmation && !understood.confirmed;
  return (
    <div className="ap-page">
      <UnderstoodPill text={m.uj.clarified_statement} needed={m.uj.requires_user_confirmation}
        understood={understood} onUnderstood={onUnderstood} />
      <h1 className="ap-headline">{m.approved ? T.lite.headlineApproved(m.title(m.approved)) : T.lite.headlineNone(m.rows.length)}</h1>
      <p className="ap-sub">{m.approved ? T.lite.subApproved : T.lite.subNone}</p>
      <div className="ap-rows">
        {m.rows.map((p) => {
          const b = m.branchOf(p);
          const open = m.current?.terminal_id === p.terminal_id;
          const shock = b?.own_node_ids.map(m.node).find((n) => n.role === 'shock');
          return (
            <div key={p.terminal_id} className={`ap-row-wrap${open ? ' open' : ''}${b?.kind === 'hypothetical' ? ' hypo' : ''}`}>
              <button className="ap-row" onClick={() => onSelect(open ? '' : p.terminal_id!)}>
                {b && <BranchBar kind={b.kind} />}
                <span className="ap-row-main">
                  <span className="ap-row-title">{m.title(p)}</span>
                  <span className="ap-row-sub">{T.liteList.direction(p.direction.instrument, p.direction.side)}
                    {b && b.kind !== 'evidenced' && <BranchTag kind={b.kind} synthetic={b.synthetic_evidence} />}</span>
                </span>
                {p.approval_reset ? <span className="ap-state warn">{T.approve.approvalReset}</span>
                  : p.user_judgment.confirmed ? <span className="ap-state ok">{T.approve.approved}</span>
                  : <span className="ap-gate" style={{ color: GATE[p.gate].color, background: GATE[p.gate].bg }}>{GATE[p.gate].label}</span>}
              </button>
              {p.rival_changed && !p.approval_reset && <div className="ap-row-note">{T.approve.rivalChanged}</div>}
              {open && (
                <PlanDetail bundle={bundle} plan={p} premises={m.premises(p)} labelOf={(id) => m.labelOf(m.node(id))}
                  hypoWhat={b?.kind === 'hypothetical' ? (shock ? m.labelOf(shock) : '') : null}
                  draft={drafts[p.terminal_id!] ?? EMPTY_DRAFT} onDraft={(d) => onDraft(p.terminal_id!, d)} />
              )}
            </div>
          );
        })}
      </div>
      {m.current && (
        <ApproveIsland plan={m.current} title={m.title(m.current)} busy={busy} needIdea={needIdea}
          isApproved={m.approved?.terminal_id === m.current.terminal_id}
          approvedTitle={m.approved && m.approved.terminal_id !== m.current.terminal_id ? m.title(m.approved) : null}
          draft={drafts[m.current.terminal_id!] ?? EMPTY_DRAFT} onDraft={(d) => onDraft(m.current!.terminal_id!, d)}
          onApprove={() => onApprove(m.current!.terminal_id!)} onRevoke={onRevoke} />
      )}
    </div>
  );
}
