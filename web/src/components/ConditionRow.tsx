// 一条 Condition：大字是规则，小字露出字段；「可核实」和「已满足」是两个徽章。
// editable 时可以改阈值（数值条件）和截止；改了只记在待提交的 overrides 里，判定仍以后端为准。
import { EVALUATION, VERIFICATION } from '../status';
import type { Condition, ConditionOverride } from '../types';
import Badge from './Badge';

export default function ConditionRow({ c, override, onOverride, highlightMissing }: {
  c: Condition; override?: ConditionOverride; onOverride?: (o: ConditionOverride | null) => void;
  highlightMissing?: boolean; // 方案 B 的批准页：阈值为 null 的数值条件高亮「需要你确认」
}) {
  const threshold = override && 'threshold' in override ? override.threshold : c.threshold;
  const deadline = override?.deadline ?? c.deadline;
  const set = (o: ConditionOverride) => onOverride?.({ ...override, ...o });
  const missing = highlightMissing && c.kind === 'numeric' && threshold == null;
  return (
    <div className={`condition${missing ? ' need-confirm' : ''}`}>
      {missing && <div className="need-confirm-tag">需要你确认：资料里没有可依据的阈值</div>}
      <div className="cond-rule">{c.rule}</div>
      <div className="cond-fields small">
        <span>{c.kind} · {c.predicate}</span>
        <span>{c.series ?? c.source ?? '—'}</span>
        <span>起点 {c.anchor}</span>
        <span>
          截止{' '}
          {onOverride ? (
            <input type="date" value={deadline} onChange={(e) => set({ deadline: e.target.value })} />
          ) : c.deadline}
        </span>
        {c.kind === 'numeric' && (
          <span>
            阈值 {c.comparator ?? ''}{' '}
            {onOverride ? (
              <input type="number" className="threshold" placeholder="你来定" value={threshold ?? ''}
                onChange={(e) => set({ threshold: e.target.value === '' ? null : Number(e.target.value) })} />
            ) : threshold ?? <em>你来定</em>}
          </span>
        )}
      </div>
      {c.threshold_note && (c.kind === 'numeric' || c.threshold === null) && <div className="small muted">{c.threshold_note}</div>}
      <div className="cond-badges">
        <Badge look={VERIFICATION[c.verification_status]} title="verification_status" />
        <Badge look={EVALUATION[c.evaluation_status]} title="evaluation_status" />
        {override && (
          <span className="small edited">
            已修改，签字后由后端重算{' '}
            <button className="link" onClick={() => onOverride?.(null)}>撤销</button>
          </span>
        )}
      </div>
      <div className="small muted mono">{c.id}</div>
    </div>
  );
}
