// 通用节点卡：颜色和文案全部来自 status.ts。
import { Handle, Position, type Node, type NodeProps } from '@xyflow/react';
import { ASSESSMENT, CHANGED_TARGET, EVIDENCE, KEY_DEPENDENCY, ROLE } from '../status';
import type { ClaimNodeData } from '../toFlow';

export default function ClaimNode({ data, selected }: NodeProps<Node<ClaimNodeData>>) {
  const { claim, assessment, isKey, isChangedTarget, evidenceCount } = data;
  const role = ROLE[claim.role];
  const a = assessment ? ASSESSMENT[assessment] : null;
  // 改动的假设不涂灰：它在 assessment 里是 unaffected，但它就是这次情景改的东西
  const greyed = a && assessment !== 'challenged' && !isChangedTarget;
  const border = a && !isChangedTarget ? a.color : role.color;
  const ev = EVIDENCE[claim.evidence_status];
  return (
    <div
      className={`claim-node${selected ? ' selected' : ''}${isKey ? ' key' : ''}`}
      style={{
        borderColor: border,
        borderStyle: claim.role === 'shock' || a?.border === 'dashed' ? 'dashed' : 'solid',
        borderWidth: assessment === 'challenged' ? 3 : 2,
        background: greyed ? a!.bg : '#fff',
        boxShadow: isKey ? `0 0 0 4px ${KEY_DEPENDENCY.bg}, 0 0 14px ${KEY_DEPENDENCY.color}` : undefined,
      }}
    >
      <Handle type="target" position={Position.Top} />
      <div className="claim-top">
        <span className="role" style={{ color: role.color }}>{role.label}</span>
        {a && !isChangedTarget && <span className="assess" style={{ color: a.color }}>{a.mark} {a.label}</span>}
        {isChangedTarget && <span className="assess" style={{ color: CHANGED_TARGET.color }}>✎ {CHANGED_TARGET.label}</span>}
      </div>
      <div className="claim-text">{claim.statement}</div>
      {claim.instruments.length > 0 && <div className="instruments">{claim.instruments.join(' · ')}</div>}
      <div className="claim-foot" style={{ color: ev.color }}>
        {ev.label} · {evidenceCount} 条引用
      </div>
      {isKey && <div className="check-first" style={{ color: KEY_DEPENDENCY.color }}>{KEY_DEPENDENCY.label}</div>}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
