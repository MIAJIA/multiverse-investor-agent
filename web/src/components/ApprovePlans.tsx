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
  if (!current || !uj) return <p className="muted">这个版本没有计划。</p>;

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
        <span className="small muted">我们把你的想法理解为</span>
        {editing ? (
          <>
            <input className="understood-input" defaultValue={understood.text ?? uj.clarified_statement}
              onBlur={(e) => { onUnderstood({ confirmed: true, text: e.target.value.trim() || null }); setEditing(false); }} autoFocus />
          </>
        ) : (
          <span className="understood-text">「{understood.text ?? uj.clarified_statement}」</span>
        )}
        {understood.confirmed ? <span className="ok">✓ 对</span> : (
          <button className="secondary" onClick={() => onUnderstood({ ...understood, confirmed: true })}>✓ 对</button>
        )}
        {!editing && <button className="link" onClick={() => setEditing(true)}>改一下</button>}
        {uj.original_statement !== uj.clarified_statement && <span className="small muted">原话：{uj.original_statement}</span>}
      </div>

      <div className="conclusions" role="listbox" aria-label="结论">
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
                <span className="c-title">{labelOf(t)} <span className="mono">{p.direction.instrument}</span> {p.direction.side === 'long' ? '看多' : '看空'}
                  {b && <BranchTag kind={b.kind} synthetic={b.synthetic_evidence} />}</span>
                <span className="c-sub">你需要相信：{ps.length === 0 ? '与其他结论共用全部前提'
                  : ps.slice(0, 3).map((id) => labelOf(node(id))).join('、') + (ps.length > 3 ? ` 等 ${ps.length} 个` : '')}</span>
              </span>
              <Badge look={GATE[p.gate]} />
              <span className="c-state">
                {p.user_judgment.confirmed && <span className="ok">✓ 已批准</span>}
                {p.approval_reset && <span className="warn">前提已改动，请重新批准</span>}
                {p.rival_changed && !p.approval_reset && <span className="small muted">另一份计划受了影响，值得再看一眼</span>}
              </span>
            </button>
          );
        })}
      </div>
      <p className="small muted">一份都不批准也是一个决定。</p>

      <div className="plan-area">
        {branch?.kind === 'hypothetical' && <HypotheticalBanner what={shock ? labelOf(shock) : undefined} />}
        <ProposalCard proposal={current} graph={graph} planB overrides={draft.overrides}
          onOverride={(id, o) => {
            const next = { ...draft.overrides };
            if (o) next[id] = o; else delete next[id];
            setDraft({ overrides: next });
          }} />
        <div className="premises">
          <div className="small muted">你需要相信的前提（可选勾选，不勾也能批准）</div>
          {premises(current).map((id) => (
            <label key={id} className="small">
              <input type="checkbox" checked={draft.confirmedClaimIds.includes(id)}
                onChange={(e) => setDraft({
                  confirmedClaimIds: e.target.checked ? [...draft.confirmedClaimIds, id] : draft.confirmedClaimIds.filter((x) => x !== id),
                })} /> {node(id).statement}
            </label>
          ))}
        </div>
        <input className="note" placeholder="备注（可选）" value={draft.note} onChange={(e) => setDraft({ note: e.target.value })} />
        <div className="approve-row">
          {isApproved ? (
            <><span className="ok">✓ 已批准这份计划</span><button className="secondary" disabled={busy} onClick={onRevoke}>撤销批准</button></>
          ) : (
            <button className="primary" disabled={busy || needUnderstood} onClick={approve}>批准这份计划</button>
          )}
          {needUnderstood && <span className="small warn">先确认上面那句理解</span>}
          {missing > 0 && !isApproved && <span className="small muted">还有 {missing} 个阈值需要你确认（不确认也能批准，进场判定会保持「先别动」）</span>}
        </div>
        <div className="small muted">
          {approved ? <>本版本已批准：{labelOf(node(approved.terminal_id!))}{!isApproved && <> · <button className="link" onClick={onRevoke}>撤销批准</button></>}</>
            : '本版本没有批准任何计划（= 不交易）'}
          <span style={{ marginLeft: 16 }}>批准的是一份计划，不是下单。</span>
        </div>
      </div>

      {askReplace && approved && (
        <div className="modal-bg" onClick={() => setAskReplace(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <p>批准这份会撤销对「{labelOf(node(approved.terminal_id!))}」的批准。同一个版本只能批准一份。</p>
            <div className="actions">
              <button className="secondary" onClick={() => setAskReplace(null)}>取消</button>
              <button className="primary" onClick={() => { onApprove(askReplace); setAskReplace(null); }}>批准并撤销另一份</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
