// 画布节点（应用和 playground 共用）：同一份数据，按 Look 的五个维度画成不同样子。
import { Handle, Position, type Node, type NodeProps } from '@xyflow/react';
import type { AssessmentStatus, Claim, Condition } from '../types';
import './node.css';
import { Bars, Ring } from './StrengthGlyph';
import type { Strength } from './strength';

export interface Look {
  shape: 'pill' | 'card';
  strength: 'ring' | 'bars';
  color: 'state' | 'role';
  expand: 'inline' | 'panel';
  scenario: 'dim' | 'path';
}

export interface DesignData extends Record<string, unknown> {
  claim: Claim;
  label: string;
  look: Look;
  s: Strength;
  conditions: Condition[];
  isKey: boolean;
  isChanged: boolean;
  assessment?: AssessmentStatus;
  expanded: boolean;
}

const ROLE_TINT: Record<Claim['role'], string> = {
  event: 'var(--pg-blue-bg)', assumption: 'var(--pg-green-bg)', intermediate: 'var(--pg-green-bg)',
  terminal: 'var(--pg-purple-bg)', shock: 'var(--pg-orange-bg)',
};

function Target() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" aria-label="关键依赖">
      <circle cx="7" cy="7" r="6" fill="none" stroke="var(--pg-orange)" strokeWidth="1.4" />
      <circle cx="7" cy="7" r="3" fill="none" stroke="var(--pg-orange)" strokeWidth="1.4" />
      <circle cx="7" cy="7" r="0.9" fill="var(--pg-orange)" />
    </svg>
  );
}

export default function DesignNode({ data, selected }: NodeProps<Node<DesignData>>) {
  const { claim, label, look, s, isKey, isChanged, assessment, expanded, conditions } = data;
  const challenged = assessment === 'challenged';
  const receded = assessment && !challenged && !isChanged && look.scenario === 'dim';
  const glyph = look.strength === 'ring' ? <Ring s={s} size={expanded ? 30 : 22} /> : <Bars s={s} />;
  const ticker = claim.instruments.length > 0 && <span className="pg-ticker">{claim.instruments.join(' ')}</span>;

  const bg = challenged ? 'var(--pg-orange-bg)' : look.color === 'role' ? ROLE_TINT[claim.role] : 'var(--pg-surface)';
  const border = challenged || isKey ? 'var(--pg-orange)' : isChanged ? 'var(--pg-blue)' : 'var(--pg-line)';
  const style = {
    background: bg,
    borderColor: border,
    borderWidth: challenged || isKey || isChanged ? 2 : 1,
    borderStyle: s.modelOnly || claim.role === 'shock' ? 'dashed' : 'solid',
    opacity: receded ? 0.32 : 1,
    outline: selected ? '2px solid var(--pg-blue)' : undefined,
    outlineOffset: 3,
  } as const;

  const meta = s.noInEdges ? '没有入边证据' : s.modelOnly ? '仅模型推断'
    : `正方 ${s.support}${s.contra ? ` · 反方 ${s.contra}` : ''}${s.neutral ? ` · 背景 ${s.neutral}` : ''}`;

  if (expanded) {
    const deadline = conditions.map((c) => c.deadline).sort()[0];
    return (
      <div className="pg-node pg-expanded" style={{ ...style, opacity: 1 }}>
        <Handle type="target" position={Position.Top} className="pg-handle" />
        <div className="pg-row">
          {glyph}
          <div style={{ minWidth: 0 }}>
            <div className="pg-title">{label} {isKey && <Target />}</div>
            <div className="pg-sub">{claim.statement}</div>
          </div>
          {ticker}
        </div>
        <div className="pg-facts">
          {!s.noInEdges && !s.modelOnly && <span><i className="pg-dot" style={{ background: 'var(--pg-green)' }} />正方 {s.support}</span>}
          {s.contra > 0 && <span><i className="pg-dot" style={{ background: 'var(--pg-red)' }} />反方 {s.contra}</span>}
          {s.neutral > 0 && <span><i className="pg-dot" style={{ background: 'var(--pg-muted)' }} />背景 {s.neutral}</span>}
          {(s.noInEdges || s.modelOnly) && <span>{meta}</span>}
          {deadline && <span>截止 {deadline}</span>}
          {challenged && <span style={{ color: 'var(--pg-orange)' }}>情景下受挑战</span>}
          {isChanged && <span style={{ color: 'var(--pg-blue)' }}>改动的假设</span>}
        </div>
        <Handle type="source" position={Position.Bottom} className="pg-handle" />
      </div>
    );
  }

  return (
    <div className={`pg-node ${look.shape === 'pill' ? 'pg-pill' : 'pg-card'}`} style={style}>
      <Handle type="target" position={Position.Top} className="pg-handle" />
      <div className="pg-row">
        {glyph}
        <span className="pg-title">{label}</span>
        {isKey && <Target />}
        {isChanged && <span className="pg-edit" title="改动的假设">✎</span>}
        {ticker}
      </div>
      {look.shape === 'card' && <div className="pg-meta">{meta}</div>}
      <Handle type="source" position={Position.Bottom} className="pg-handle" />
    </div>
  );
}
