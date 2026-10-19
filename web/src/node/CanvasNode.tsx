// 应用画布上的节点（节点视觉 B：符号 + 类型字；结论顶部深色标题栏）。一个视觉通道只回答一个问题：
// 类型 = 第一行符号和字；分支类别 = 边框线型；证据 = 底部一行字；先查 = 橙色小标；能改 = 铅笔；
// 情景（改过之后）= 一枚状态小标（你改的 / 受影响 / 暂时到不了），没受影响的变淡；结论上标「需重新批准」。
// 点铅笔，节点的说法就地变成输入框，确认后由上层发 change_assumption。
import { Handle, Position, type Node, type NodeProps } from '@xyflow/react';
import { useState } from 'react';
import { Evidence, KeyBadge, LINE } from '../playground/grammar/GrammarNode';
import { T } from '../strings';
import type { AssessmentStatus, BranchKind, Claim } from '../types';
import { Pencil, TYPE_ICON } from './Icons';
import type { Strength } from './strength';
import './canvas-node.css';

export interface CanvasData extends Record<string, unknown> {
  claim: Claim;
  label: string;
  s: Strength;
  kind?: BranchKind;
  isKey: boolean;
  dimmed: boolean;
  assessment?: AssessmentStatus;
  changed: boolean; // 这一版本里用户改的节点（或加的原因）
  reapprove: boolean; // 结论：这份计划的前提变了，要重新批准
  canEdit: boolean; // 显示铅笔（非结论节点；选中时或是前提假设时）
  editing: boolean;
  editText?: string; // 编辑框的初始文字（后端拒绝后带回用户写的）
  pendingText?: string; // 已提交、后端在重算：先显示用户的新说法
  busy: boolean;
  onEditStart?: () => void;
  onEditCommit?: (text: string) => void;
  onEditCancel?: () => void;
}

function EditBox({ initial, busy, onCommit, onCancel }: { initial: string; busy: boolean; onCommit: (t: string) => void; onCancel: () => void }) {
  const [text, setText] = useState(initial);
  const ok = !!text.trim();
  return (
    <div className="cn-edit nodrag nopan" onClick={(e) => e.stopPropagation()} onDoubleClick={(e) => e.stopPropagation()}>
      <textarea autoFocus value={text} rows={3} placeholder={T.edit.placeholder} onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Escape') onCancel();
          if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && ok) onCommit(text);
        }} />
      <div className="cn-edit-row">
        <button className="cn-btn" onClick={onCancel}>{T.edit.cancel}</button>
        <button className="cn-btn go" disabled={!ok || busy} onClick={() => onCommit(text)}>{T.edit.confirm}</button>
      </div>
    </div>
  );
}

export default function CanvasNode({ data, selected }: NodeProps<Node<CanvasData>>) {
  const { claim, label, s, kind, isKey, dimmed, assessment, changed, reapprove, canEdit, editing, busy, editText, pendingText } = data;
  const Icon = TYPE_ICON[claim.role];
  const terminal = claim.role === 'terminal';
  const ticker = claim.instruments[0];
  const faded = dimmed || (assessment === 'unaffected' && !changed);
  const style = {
    borderStyle: kind ? LINE[kind].border : 'solid',
    opacity: faded && !editing ? 0.3 : 1,
    outline: changed || pendingText ? '2px solid #2f6fed' : selected ? '2px solid #2f6fed80' : undefined,
    outlineOffset: 3,
  } as const;
  const flag = pendingText ? <span className="cn-flag mine">{T.pending.flag}</span>
    : changed ? <span className="cn-flag mine">{T.edit.yourEdit}</span>
    : assessment === 'challenged' ? <span className="cn-flag hit">{T.edit.challenged}</span>
    : assessment === 'unresolved' ? <span className="cn-flag">{T.edit.unresolved}</span> : null;

  return (
    <div className={`gn gn-b cn${terminal ? ' gn-b-terminal' : ''}${editing ? ' cn-editing' : ''}`} style={style}>
      <Handle type="target" position={Position.Top} className="gn-handle cn-target" />
      <div className="gn-head">
        <Icon size={13} /><span>{T.grammar.type[claim.role]}</span>
        {terminal && ticker && <span className="gn-head-ticker">{ticker.length > 12 ? `${ticker.slice(0, 12)}…` : ticker}</span>}
        <span className="spacer" />
        {canEdit && !editing && (
          <button className="gn-pencil nodrag" title={T.edit.pencil} disabled={busy}
            onClick={(e) => { e.stopPropagation(); data.onEditStart?.(); }}>
            <Pencil size={13} />
          </button>
        )}
      </div>
      {editing
        ? <EditBox initial={editText ?? claim.statement} busy={busy} onCommit={(t) => data.onEditCommit?.(t)} onCancel={() => data.onEditCancel?.()} />
        : pendingText ? <div className="gn-title" title={pendingText}>{pendingText}</div>
        : <div className="gn-title" title={claim.statement}>{label}</div>}
      <div className="gn-foot">
        <Evidence s={s} />
        {isKey && <KeyBadge />}
        {flag}
        {terminal && reapprove && <span className="cn-flag redo">{T.edit.reapprove}</span>}
      </div>
      <Handle type="source" position={Position.Bottom} className="gn-handle" isConnectable={false} />
    </div>
  );
}
