// 方案 B 的 B2「批准计划」：理解确认 + 结论列表 + 选中的计划 + 批准 / 撤销批准。
// 不发请求：批准、撤销都交给父组件（真实后端是 sign，terminal_id 为 null 表示撤销）。
import { useState } from 'react';
import { nodeLabel } from '../node/labels';
import { GATE } from '../status';
import { toFlow } from '../toFlow';
import type { Claim, ConditionOverride, PlanBBundle, TradeProposal } from '../types';
import Badge from './Badge';
import { BranchBar, BranchTag, HypotheticalBanner } from './BranchSwatch';
import ProposalCard from './ProposalCard';
import { T } from '../strings';

export interface PlanDraft {
  overrides: Record<string, ConditionOverride>;
  confirmedClaimIds: string[];
  note: string;
}

export const EMPTY_DRAFT: PlanDraft = { overrides: {}, confirmedClaimIds: [], note: '' };

export interface Understood {
  confirmed: boolean;
  text: string | null; // 用户改过的说法；null = 沿用后端的 clarified_statement
}

export default function ApprovePlans({
  bundle, selected, onSelect, drafts, onDraft, understood, onUnderstood, onApprove, onRevoke, busy,
  labelOf = nodeLabel,
}: {
  bundle: PlanBBundle;
  selected: string | null;
  onSelect: (terminalId: string) => void;
  drafts: Record<string, PlanDraft>;
  onDraft: (terminalId: string, d: PlanDraft) => void;
  understood: Understood;
  onUnderstood: (u: Understood) => void;
  onApprove: (terminalId: string) => void;
  onRevoke: () => void;
  busy: boolean;
  labelOf?: (c: Claim) => string;
}) {
  const { graph, proposals, branches } = bundle;
  const node = (id: string) => graph.nodes.find((n) => n.id === id)!;
  // 列表按画布上终点的左右顺序排（纯展示），不依赖后端数组顺序
  const order = new Map(toFlow(graph).nodes.map((n) => [n.id, n.position.x]));
  const rows = [...proposals].sort((a, b) => (order.get(a.terminal_id!) ?? 0) - (order.get(b.terminal_id!) ?? 0));
  const approved = proposals.find((p) => p.user_judgment.confirmed) ?? null;
  const current = rows.find((p) => p.terminal_id === selected) ?? approved ?? rows[0];
  const branchOf = (p: TradeProposal) => branches.find((b) => b.terminal_id === p.terminal_id);
  const premises = (p: TradeProposal) => (branchOf(p)?.own_node_ids ?? []).filter((id) => id !== p.terminal_id);
  const uj = proposals[0]?.user_judgment; // 后端保证同一版本几份计划的这一句相同
  const [editing, setEditing] = useState(false);
  const [askReplace, setAskReplace] = useState<string | null>(null);
  if (!current || !uj) return <p className="muted">{T.approve.noPlans}</p>;

  const draft = drafts[current.terminal_id!] ?? EMPTY_DRAFT;
  const setDraft = (d: Partial<PlanDraft>) => onDraft(current.terminal_id!, { ...draft, ...d });
  const branch = branchOf(current);
  const needUnderstood = uj.requires_user_confirmation && !understood.confirmed;
  const missing = [...current.entry_conditions, ...current.exit_conditions]
    .filter((c) => c.kind === 'numeric' && c.threshold == null && draft.overrides[c.id]?.threshold == null).length;
  const shock = branch?.own_node_ids.map(node).find((n) => n.role === 'shock');
  const isApproved = approved?.terminal_id === current.terminal_id;

  const approve = () => {
    if (approved && !isApproved) setAskReplace(current.terminal_id!);
    else onApprove(current.terminal_id!);
  };

  return (
    <div className="page approve">
      <div className="understood">
        <span className="small muted">{T.approve.understoodLead}</span>
        {editing ? (
          <>
            <input className="understood-input" defaultValue={understood.text ?? uj.clarified_statement}
              onBlur={(e) => { onUnderstood({ confirmed: true, text: e.target.value.trim() || null }); setEditing(false); }} autoFocus />
          </>
        ) : (
          <span className="understood-text">{T.approve.quoted(understood.text ?? uj.clarified_statement)}</span>
        )}
        {understood.confirmed ? <span className="ok">{T.approve.yes}</span> : (
          <button className="secondary" onClick={() => onUnderstood({ ...understood, confirmed: true })}>{T.approve.yes}</button>
        )}
        {!editing && <button className="link" onClick={() => setEditing(true)}>{T.approve.edit}</button>}
        {uj.original_statement !== uj.clarified_statement && <span className="small muted">{T.approve.original(uj.original_statement)}</span>}
      </div>

      <div className="conclusions" role="listbox" aria-label={T.approve.listAria}>
        {rows.map((p) => {
          const b = branchOf(p);
          const t = node(p.terminal_id!);
          const ps = premises(p);
          return (
            <button key={p.terminal_id} role="option" aria-selected={p === current}
              className={`conclusion${p === current ? ' on' : ''}${b?.kind === 'hypothetical' ? ' hypo' : ''}`}
              onClick={() => onSelect(p.terminal_id!)}>
              {b && <BranchBar kind={b.kind} />}
              <span className="c-main">
                <span className="c-title">{labelOf(t)} <span className="mono">{p.direction.instrument}</span> {T.approve.side(p.direction.side)}
                  {b && <BranchTag kind={b.kind} synthetic={b.synthetic_evidence} />}</span>
                <span className="c-sub">{T.approve.youNeedToBelieve(ps.slice(0, 3).map((id) => labelOf(node(id))), ps.length)}</span>
              </span>
              <Badge look={GATE[p.gate]} />
              <span className="c-state">
                {p.user_judgment.confirmed && <span className="ok">{T.approve.approved}</span>}
                {p.approval_reset && <span className="warn">{T.approve.approvalReset}</span>}
                {p.rival_changed && !p.approval_reset && <span className="small muted">{T.approve.rivalChanged}</span>}
              </span>
            </button>
          );
        })}
      </div>
      <p className="small muted">{T.approve.noneIsADecision}</p>

      <div className="plan-area">
        {branch?.kind === 'hypothetical' && <HypotheticalBanner what={shock ? labelOf(shock) : undefined} />}
        <ProposalCard proposal={current} graph={graph} planB overrides={draft.overrides}
          onOverride={(id, o) => {
            const next = { ...draft.overrides };
            if (o) next[id] = o; else delete next[id];
            setDraft({ overrides: next });
          }} />
        <div className="premises">
          <div className="small muted">{T.approve.premisesHint}</div>
          {premises(current).map((id) => (
            <label key={id} className="small">
              <input type="checkbox" checked={draft.confirmedClaimIds.includes(id)}
                onChange={(e) => setDraft({
                  confirmedClaimIds: e.target.checked ? [...draft.confirmedClaimIds, id] : draft.confirmedClaimIds.filter((x) => x !== id),
                })} /> {node(id).statement}
            </label>
          ))}
        </div>
        <input className="note" placeholder={T.approve.notePlaceholder} value={draft.note} onChange={(e) => setDraft({ note: e.target.value })} />
        <div className="approve-row">
          {isApproved ? (
            <><span className="ok">{T.approve.approvedThis}</span><button className="secondary" disabled={busy} onClick={onRevoke}>{T.approve.revoke}</button></>
          ) : (
            <button className="primary" disabled={busy || needUnderstood} onClick={approve}>{T.approve.approveThis}</button>
          )}
          {needUnderstood && <span className="small warn">{T.approve.confirmUnderstoodFirst}</span>}
          {missing > 0 && !isApproved && <span className="small muted">{T.approve.missingThresholds(missing)}</span>}
        </div>
        <div className="small muted">
          {approved ? <>{T.approve.approvedInVersion(labelOf(node(approved.terminal_id!)))}{!isApproved && <>{T.approve.sep}<button className="link" onClick={onRevoke}>{T.approve.revoke}</button></>}</>
            : T.approve.noneApproved}
          <span style={{ marginLeft: 16 }}>{T.approve.notAnOrder}</span>
        </div>
      </div>

      {askReplace && approved && (
        <div className="modal-bg" onClick={() => setAskReplace(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <p>{T.approve.replaceQuestion(labelOf(node(approved.terminal_id!)))}</p>
            <div className="actions">
              <button className="secondary" onClick={() => setAskReplace(null)}>{T.approve.cancel}</button>
              <button className="primary" onClick={() => { onApprove(askReplace); setAskReplace(null); }}>{T.approve.replaceConfirm}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
