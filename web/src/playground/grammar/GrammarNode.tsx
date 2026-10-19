// 「一个通道只回答一个问题」的节点：白底；类型 = 符号（A 只有徽章，B 符号 + 类型字）；结论 = 另一种形状；
// 分支类别 = 边框线型；证据 = 底部一行字；先查 = 一个橙色小标；能改 = 铅笔按钮。没有底色、底纹、彩色边框。
import { Handle, Position, type Node, type NodeProps } from '@xyflow/react';
import type { Strength } from '../../node/strength';
import { T } from '../../strings';
import type { BranchKind, Claim } from '../../types';
import { Pencil, Search, TYPE_ICON } from './Icons';

export type Variant = 'A' | 'B';

export interface GrammarData extends Record<string, unknown> {
  claim: Claim;
  label: string;
  variant: Variant;
  kind: BranchKind;
  s: Strength;
  isKey: boolean;
  dimmed: boolean;
  onEdit: (claim: Claim, label: string) => void;
}

export const LINE: Record<BranchKind, { border: string; dash?: string }> = {
  evidenced: { border: 'solid' },
  model_only: { border: 'dashed', dash: '6 4' },
  hypothetical: { border: 'dotted', dash: '1.5 3.5' },
};

export function Evidence({ s }: { s: Strength }) {
  if (s.noInEdges) return <span className="gn-ev muted">{T.grammar.root}</span>;
  if (s.modelOnly) return <span className="gn-ev muted">{T.grammar.modelOnly}</span>;
  if (!s.support && !s.contra) return <span className="gn-ev muted">{T.grammar.noEvidence}</span>;
  return (
    <span className="gn-ev">
      {T.grammar.support(s.support)}
      {s.contra > 0 && <> · <b className="gn-contra">{T.grammar.contra(s.contra)}</b></>}
    </span>
  );
}

export function KeyBadge() {
  return <span className="gn-key"><Search size={11} />{T.grammar.key}</span>;
}

export default function GrammarNode({ data, selected }: NodeProps<Node<GrammarData>>) {
  const { claim, label, variant, kind, s, isKey, dimmed, onEdit } = data;
  const Icon = TYPE_ICON[claim.role];
  const terminal = claim.role === 'terminal';
  const editable = claim.role === 'assumption';
  const ticker = claim.instruments[0];
  const style = {
    borderStyle: LINE[kind].border,
    opacity: dimmed ? 0.25 : 1,
    outline: selected ? '2px solid #2f6fed' : undefined,
    outlineOffset: 3,
  } as const;
  const edit = editable && (
    <button className="gn-pencil" title={T.grammar.edit} onClick={(e) => { e.stopPropagation(); onEdit(claim, label); }}>
      <Pencil size={13} />
    </button>
  );

  if (variant === 'A') {
    return (
      <div className={`gn gn-a${terminal ? ' gn-a-terminal' : ''}`} style={style}>
        <Handle type="target" position={Position.Top} className="gn-handle" />
        <span className="gn-badge" title={T.grammar.type[claim.role]}><Icon size={15} /></span>
        <div className="gn-body">
          <div className="gn-title">{label}</div>
          <div className="gn-foot"><Evidence s={s} />{isKey && <KeyBadge />}</div>
        </div>
        {terminal && ticker && <span className="gn-ticker">{ticker.length > 10 ? `${ticker.slice(0, 10)}…` : ticker}</span>}
        {edit}
        <Handle type="source" position={Position.Bottom} className="gn-handle" />
      </div>
    );
  }

  return (
    <div className={`gn gn-b${terminal ? ' gn-b-terminal' : ''}`} style={style}>
      <Handle type="target" position={Position.Top} className="gn-handle" />
      <div className="gn-head">
        <Icon size={13} /><span>{T.grammar.type[claim.role]}</span>
        {terminal && ticker && <span className="gn-head-ticker">{ticker.length > 12 ? `${ticker.slice(0, 12)}…` : ticker}</span>}
        <span className="spacer" />
        {edit}
      </div>
      <div className="gn-title">{label}</div>
      <div className="gn-foot"><Evidence s={s} />{isKey && <KeyBadge />}</div>
      <Handle type="source" position={Position.Bottom} className="gn-handle" />
    </div>
  );
}
