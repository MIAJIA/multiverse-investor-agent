// B2 精简版的三个共用件：
// - UnderstoodPill：顶部一颗胶囊，「你的想法」确认；点「改一下」原地展开（灵动岛）。
// - ApproveIsland：底部黑色胶囊，批准 / 改批 / 撤销；点开原地展开出备注和确认，不用弹窗。
// - PlanDetail：像 OpenEvidence 的答案卡：前提是带引用数的小标签，点开看原文；信号一行一条，需要确认的阈值原地填。
import { useState } from 'react';
import { nodeEvidence } from '../../lookup';
import { Ring } from '../../node/StrengthGlyph';
import { strength } from '../../node/strength';
import { EVALUATION } from '../../status';
import { T } from '../../strings';
import type { Condition, PlanBBundle, TradeProposal } from '../../types';
import type { PlanDraft, Understood } from '../ApprovePlans';
import { BranchTag } from '../BranchSwatch';
import ProposalCard from '../ProposalCard';
import { missingThresholds } from './model';
import './approve.css';

export function UnderstoodPill({ text, needed, understood, onUnderstood }: {
  text: string; needed: boolean; understood: Understood; onUnderstood: (u: Understood) => void;
}) {
  const [editing, setEditing] = useState(false);
  const shown = understood.text ?? text;
  if (editing) {
    return (
      <div className="ap-idea open">
        <span className="ap-idea-lead">{T.lite.yourIdea}</span>
        <input className="ap-idea-input" defaultValue={shown} autoFocus
          onKeyDown={(e) => e.key === 'Enter' && (e.target as HTMLInputElement).blur()}
          onBlur={(e) => { onUnderstood({ confirmed: true, text: e.target.value.trim() || null }); setEditing(false); }} />
        <button className="ap-chip-btn" onMouseDown={(e) => e.preventDefault()} onClick={() => setEditing(false)}>{T.lite.done}</button>
      </div>
    );
  }
  return (
    <div className={`ap-idea${understood.confirmed ? ' ok' : ''}`}>
      <span className="ap-idea-lead">{T.lite.yourIdea}</span>
      <span className="ap-idea-text">{shown}</span>
      {understood.confirmed ? <span className="ap-check">✓</span> : needed && (
        <button className="ap-chip-btn primary" onClick={() => onUnderstood({ ...understood, confirmed: true })}>{T.lite.confirmIdea}</button>
      )}
      <button className="ap-link" onClick={() => setEditing(true)}>{T.lite.editIdea}</button>
    </div>
  );
}

export function ApproveIsland({ plan, title, approvedTitle, isApproved, needIdea, draft, onDraft, onApprove, onRevoke, busy }: {
  plan: TradeProposal; title: string; approvedTitle: string | null; isApproved: boolean; needIdea: boolean;
  draft: PlanDraft; onDraft: (d: PlanDraft) => void; onApprove: () => void; onRevoke: () => void; busy: boolean;
}) {
  const [open, setOpen] = useState(false);
  const missing = missingThresholds(plan, draft);
  if (isApproved) {
    return (
      <div className="ap-island"><div className="ap-pill done">
        <span>{T.lite.islandApproved(title)}</span>
        <button className="ap-pill-btn" disabled={busy} onClick={onRevoke}>{T.lite.islandRevoke}</button>
      </div></div>
    );
  }
  if (!open) {
    return (
      <div className="ap-island">
        <button className={`ap-pill${needIdea ? ' muted' : ''}`} disabled={busy || needIdea} onClick={() => setOpen(true)}>
          {approvedTitle ? T.lite.islandReplace(approvedTitle) : T.lite.islandApprove(title)}
        </button>
        {needIdea && <div className="ap-island-hint">{T.lite.islandNeedIdea}</div>}
      </div>
    );
  }
  return (
    <div className="ap-island">
      <div className="ap-pill-open">
        <div className="ap-pill-title">{approvedTitle ? T.lite.islandReplace(approvedTitle) : T.lite.islandApprove(title)}</div>
        {missing > 0 && <div className="ap-pill-hint">{T.lite.islandMissing(missing)}</div>}
        <input className="ap-pill-input" placeholder={T.lite.islandNote} value={draft.note}
          onChange={(e) => onDraft({ ...draft, note: e.target.value })} />
        <div className="ap-pill-row">
          <span className="ap-pill-hint">{T.lite.islandNotOrder}</span>
          <button className="ap-pill-btn" onClick={() => setOpen(false)}>{T.lite.islandCancel}</button>
          <button className="ap-pill-btn go" disabled={busy} onClick={() => { onApprove(); setOpen(false); }}>{T.lite.islandConfirm}</button>
        </div>
      </div>
    </div>
  );
}

function Signal({ c, tag, draft, onDraft }: { c: Condition; tag: string; draft: PlanDraft; onDraft: (d: PlanDraft) => void }) {
  const [edit, setEdit] = useState(false);
  const ov = draft.overrides[c.id];
  const threshold = ov && 'threshold' in ov ? ov.threshold : c.threshold;
  const missing = c.kind === 'numeric' && threshold == null;
  return (
    <li className="ap-signal">
      <span className="ap-dot" style={{ background: EVALUATION[c.evaluation_status].color }} title={EVALUATION[c.evaluation_status].label} />
      <span className="ap-signal-tag">{tag}</span>
      <span className="ap-signal-text">{c.rule}</span>
      <span className="ap-signal-date">{c.deadline}</span>
      {missing && !edit && <button className="ap-need" onClick={() => setEdit(true)}>{T.lite.needConfirm} · {T.lite.setThreshold}</button>}
      {(edit || (ov && 'threshold' in ov)) && (
        <span className="ap-threshold">
          {c.comparator}
          <input type="number" autoFocus={edit} value={threshold ?? ''} placeholder={T.condition.youDecide}
            onChange={(e) => onDraft({ ...draft, overrides: { ...draft.overrides, [c.id]: { ...ov, threshold: e.target.value === '' ? null : Number(e.target.value) } } })} />
        </span>
      )}
    </li>
  );
}

export function PlanDetail({ bundle, plan, premises, labelOf, hypoWhat, draft, onDraft }: {
  bundle: PlanBBundle; plan: TradeProposal; premises: string[]; labelOf: (id: string) => string; hypoWhat: string | null;
  draft: PlanDraft; onDraft: (d: PlanDraft) => void;
}) {
  const [openPremise, setOpenPremise] = useState<string | null>(null);
  const [more, setMore] = useState(false);
  const ev = openPremise ? nodeEvidence(bundle.graph, openPremise, bundle.excerpts) : null;
  const refs = ev ? [...ev.supporting, ...ev.contradicting, ...ev.background] : [];
  return (
    <div className="ap-detail">
      {hypoWhat !== null && (
        <div className="ap-hypo"><BranchTag kind="hypothetical" /> {T.lite.hypoWith(hypoWhat)}</div>
      )}
      <div className="ap-section">{T.lite.believe}</div>
      <div className="ap-premises">
        {premises.length === 0 && <span className="ap-muted">{T.lite.sharedPremises}</span>}
        {premises.map((id) => {
          const s = strength(bundle.graph, id, bundle.excerpts);
          const n = s.support + s.contra + s.neutral;
          return (
            <button key={id} className={`ap-premise${openPremise === id ? ' on' : ''}`} onClick={() => setOpenPremise(openPremise === id ? null : id)}>
              <Ring s={s} size={16} /> {labelOf(id)}
              <sup className={n ? 'ap-cite' : 'ap-cite none'}>{n ? T.lite.citations(n) : T.lite.noCitations}</sup>
            </button>
          );
        })}
      </div>
      {openPremise && (
        <ol className="ap-sources">
          {refs.length === 0 && <li className="ap-muted">{T.panel.modelOnly}</li>}
          {refs.map((r) => (
            <li key={r.edge.id + r.ref.excerpt_id} className={`ap-source ${r.ref.stance}`}>
              <div className="ap-quote">{r.excerpt?.text ?? T.panel.excerptMissing}</div>
              <div className="ap-muted">{r.excerpt?.source ?? r.ref.source_id} · {r.excerpt?.date ?? T.panel.unknownDate}
                {r.ref.stance === 'contradicts' && r.ref.rebuttal ? ` · ${T.panel.rebuttal(r.ref.rebuttal)}` : ''}</div>
            </li>
          ))}
        </ol>
      )}
      <div className="ap-section">{T.lite.watch}</div>
      <ul className="ap-signals">
        {plan.entry_conditions.map((c) => <Signal key={c.id} c={c} tag={T.lite.entry} draft={draft} onDraft={onDraft} />)}
        {plan.exit_conditions.map((c) => <Signal key={c.id} c={c} tag={T.lite.exit} draft={draft} onDraft={onDraft} />)}
      </ul>
      <button className="ap-link" onClick={() => setMore(!more)}>{more ? T.lite.less : T.lite.more}</button>
      {more && (
        <div className="ap-more">
          <ProposalCard proposal={plan} graph={bundle.graph} planB overrides={draft.overrides}
            onOverride={(id, o) => {
              const next = { ...draft.overrides };
              if (o) next[id] = o; else delete next[id];
              onDraft({ ...draft, overrides: next });
            }} />
          <div className="ap-section">{T.lite.premisesOptional}</div>
          {premises.map((id) => (
            <label key={id} className="ap-check-row">
              <input type="checkbox" checked={draft.confirmedClaimIds.includes(id)}
                onChange={(e) => onDraft({
                  ...draft, confirmedClaimIds: e.target.checked ? [...draft.confirmedClaimIds, id] : draft.confirmedClaimIds.filter((x) => x !== id),
                })} /> {labelOf(id)}
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
