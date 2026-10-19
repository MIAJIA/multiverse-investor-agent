// 签字表单：可检验的判断、判定条件、期限。签的是研究判断，不是下单。
import { useState } from 'react';
import type { UserJudgment } from '../types';
import type { SignForm } from './Signoff';
import { T } from '../strings';

export default function SignDialog({ uj, busy, onCancel, onSubmit }: {
  uj: UserJudgment; busy: boolean; onCancel: () => void; onSubmit: (f: SignForm) => void;
}) {
  const [clarified, setClarified] = useState(uj.clarified_statement);
  const [criteria, setCriteria] = useState(uj.criteria ?? '');
  const [deadline, setDeadline] = useState(uj.deadline ?? '');
  return (
    <div className="modal-bg" onClick={onCancel}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3 style={{ margin: 0 }}>{T.sign.title}</h3>
        <label>{T.sign.clarified}</label>
        <textarea rows={3} value={clarified} onChange={(e) => setClarified(e.target.value)} />
        {uj.original_statement !== clarified && <div className="small muted">{T.sign.original(uj.original_statement)}</div>}
        <label>{T.sign.criteria}</label>
        <textarea rows={2} value={criteria} placeholder={T.sign.criteriaPlaceholder}
          onChange={(e) => setCriteria(e.target.value)} />
        <label>{T.sign.deadline}</label>
        <input type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} />
        <div className="actions">
          <button className="secondary" onClick={onCancel}>{T.sign.cancel}</button>
          <button className="primary" disabled={busy || !clarified.trim()}
            onClick={() => onSubmit({ clarified_statement: clarified.trim(), criteria: criteria.trim() || null, deadline: deadline || null })}>
            {T.sign.submit}
          </button>
        </div>
        <div className="sign-note" style={{ textAlign: 'right' }}>{T.sign.note}</div>
      </div>
    </div>
  );
}
