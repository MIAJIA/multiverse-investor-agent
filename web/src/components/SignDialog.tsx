// 签字表单：可检验的判断、判定条件、期限。签的是研究判断，不是下单。
import { useState } from 'react';
import type { UserJudgment } from '../types';
import type { SignForm } from './Signoff';

export default function SignDialog({ uj, busy, onCancel, onSubmit }: {
  uj: UserJudgment; busy: boolean; onCancel: () => void; onSubmit: (f: SignForm) => void;
}) {
  const [clarified, setClarified] = useState(uj.clarified_statement);
  const [criteria, setCriteria] = useState(uj.criteria ?? '');
  const [deadline, setDeadline] = useState(uj.deadline ?? '');
  return (
    <div className="modal-bg" onClick={onCancel}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3 style={{ margin: 0 }}>签字</h3>
        <label>可检验的判断</label>
        <textarea rows={3} value={clarified} onChange={(e) => setClarified(e.target.value)} />
        {uj.original_statement !== clarified && <div className="small muted">原话：{uj.original_statement}</div>}
        <label>判定条件（怎样算对、怎样算错）</label>
        <textarea rows={2} value={criteria} placeholder="例如：季度出货报告达到上面确认的阈值"
          onChange={(e) => setCriteria(e.target.value)} />
        <label>期限</label>
        <input type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} />
        <div className="actions">
          <button className="secondary" onClick={onCancel}>取消</button>
          <button className="primary" disabled={busy || !clarified.trim()}
            onClick={() => onSubmit({ clarified_statement: clarified.trim(), criteria: criteria.trim() || null, deadline: deadline || null })}>
            Sign
          </button>
        </div>
        <div className="sign-note" style={{ textAlign: 'right' }}>签的是研究判断，不是下单。</div>
      </div>
    </div>
  );
}
