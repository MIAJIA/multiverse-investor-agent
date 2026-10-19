// 画布节点（应用和 playground 共用）：同一份数据，按 Look 的五个维度画成不同样子。
import { Handle, Position, type Node, type NodeProps } from '@xyflow/react';
import { BranchTag } from '../components/BranchSwatch';
import { BRANCH_KIND } from '../status';
import type { AssessmentStatus, BranchKind, Claim, Condition } from '../types';
import './node.css';
import { Bars, Ring } from './StrengthGlyph';
import type { Strength } from './strength';
import { T } from '../strings';

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
  tint?: string; // 叠图时按情景上色（#rrggbb）；有 tint 时盖过 assessment 的颜色
  kind?: BranchKind; // 方案 B：节点所属分支的类别（后端 node_kinds），决定底纹、线型、标签
  synthetic?: boolean; // 仅推断是因为资料为占位
  dimmed?: boolean; // 高亮另一条分支时，这个节点退后
}

const ROLE_TINT: Record<Claim['role'], string> = {
  event: 'var(--pg-blue-bg)', assumption: 'var(--pg-green-bg)', intermediate: 'var(--pg-green-bg)',
  terminal: 'var(--pg-purple-bg)', shock: 'var(--pg-orange-bg)',
};

function Target() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" aria-label={T.node.keyDependency}>
      <circle cx="7" cy="7" r="6" fill="none" stroke="var(--pg-orange)" strokeWidth="1.4" />
      <circle cx="7" cy="7" r="3" fill="none" stroke="var(--pg-orange)" strokeWidth="1.4" />
      <circle cx="7" cy="7" r="0.9" fill="var(--pg-orange)" />
    </svg>
  );
}

export default function DesignNode({ data, selected }: NodeProps<Node<DesignData>>) {
  const { claim, label, look, s, isKey, isChanged, assessment, expanded, conditions, tint, kind, synthetic, dimmed } = data;
  const k = kind ? BRANCH_KIND[kind] : null;
  const challenged = assessment === 'challenged';
  const receded = assessment && !challenged && !isChanged && look.scenario === 'dim';
  const glyph = look.strength === 'ring' ? <Ring s={s} size={expanded ? 30 : 22} /> : <Bars s={s} />;
  const ticker = claim.instruments.length > 0 && <span className="pg-ticker">{claim.instruments.join(' ')}</span>;

  const bg = tint ? `${tint}1f` : challenged ? 'var(--pg-orange-bg)' : look.color === 'role' ? ROLE_TINT[claim.role] : 'var(--pg-surface)';
  const border = tint ? tint : challenged || isKey ? 'var(--pg-orange)' : isChanged ? 'var(--pg-blue)' : 'var(--pg-line)';
  // 有分支类别时：底色、底纹、线型、标题色都按 BRANCH_KIND；关键依赖仍是橙框
  const kindBg = k && kind !== 'evidenced' ? k.bg : bg;
  const style = {
    background: k && !tint && !challenged ? kindBg : bg,
    backgroundImage: k && !tint && !challenged ? k.pattern : undefined,
    borderColor: k && !tint && !challenged && !isKey ? (kind === 'evidenced' ? border : k.border) : border,
    borderWidth: tint || challenged || isKey || isChanged || kind === 'hypothetical' ? 2 : 1,
    borderStyle: k ? k.line : s.modelOnly || claim.role === 'shock' ? 'dashed' : 'solid',
    color: k?.title,
    opacity: receded || dimmed ? 0.32 : 1,
    outline: selected ? '2px solid var(--pg-blue)' : undefined,
    outlineOffset: 3,
  } as const;

  const meta = s.noInEdges ? T.node.noInEdges : s.modelOnly ? T.node.modelOnly
    : [T.node.support(s.support), s.contra ? T.node.contra(s.contra) : '', s.neutral ? T.node.background(s.neutral) : ''].filter(Boolean).join(T.node.sep);

  if (expanded) {
    const deadline = conditions.map((c) => c.deadline).sort()[0];
    return (
      <div className="pg-node pg-expanded" style={{ ...style, opacity: 1 }}>
        <Handle type="target" position={Position.Top} className="pg-handle" />
        <div className="pg-row">
          {glyph}
          <div style={{ minWidth: 0 }}>
            {kind && kind !== 'evidenced' && <BranchTag kind={kind} synthetic={synthetic} />}
            <div className="pg-title">{label} {isKey && <Target />}</div>
            <div className="pg-sub">{claim.statement}</div>
          </div>
          {ticker}
        </div>
        <div className="pg-facts">
          {!s.noInEdges && !s.modelOnly && <span><i className="pg-dot" style={{ background: 'var(--pg-green)' }} />{T.node.support(s.support)}</span>}
          {s.contra > 0 && <span><i className="pg-dot" style={{ background: 'var(--pg-red)' }} />{T.node.contra(s.contra)}</span>}
          {s.neutral > 0 && <span><i className="pg-dot" style={{ background: 'var(--pg-muted)' }} />{T.node.background(s.neutral)}</span>}
          {(s.noInEdges || s.modelOnly) && <span>{meta}</span>}
          {deadline && <span>{T.node.deadline(deadline)}</span>}
          {challenged && <span style={{ color: 'var(--pg-orange)' }}>{T.node.challengedInScenario}</span>}
          {isChanged && <span style={{ color: 'var(--pg-blue)' }}>{T.changedTarget}</span>}
        </div>
        <Handle type="source" position={Position.Bottom} className="pg-handle" />
      </div>
    );
  }

  return (
    <div className={`pg-node ${look.shape === 'pill' ? 'pg-pill' : 'pg-card'}`} style={style}>
      <Handle type="target" position={Position.Top} className="pg-handle" />
      {kind && kind !== 'evidenced' && <div className="pg-tagline"><BranchTag kind={kind} synthetic={synthetic} /></div>}
      <div className="pg-row">
        {glyph}
        <span className="pg-title">{label}</span>
        {isKey && <Target />}
        {isChanged && <span className="pg-edit" title={T.changedTarget}>✎</span>}
        {ticker}
      </div>
      {look.shape === 'card' && <div className="pg-meta">{meta}</div>}
      <Handle type="source" position={Position.Bottom} className="pg-handle" />
    </div>
  );
}
