// 草稿原因：双击画布空白处出现。写下发生了什么，从底部圆点拖到受影响的已有节点；每条连线选「推高 / 压低」。
// 确认后由上层发 add_shock。连线规则在 edits.ts 的 canLink（只能从草稿连到已有节点）。
import { Handle, Position, type Node, type NodeProps } from '@xyflow/react';
import type { DraftLink, Sign } from '../edits';
import { T } from '../strings';
import { CloudBolt } from './Icons';

export interface DraftData extends Record<string, unknown> {
  text: string;
  links: DraftLink[];
  labelOf: (id: string) => string;
  busy: boolean;
  frozen: boolean; // 已提交、后端在重算：只读显示，新版本回来前一直留在图上
  onText: (t: string) => void;
  onSign: (to: string, sign: Sign) => void;
  onRemove: (to: string) => void;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function DraftNode({ data }: NodeProps<Node<DraftData>>) {
  const { text, links, labelOf, busy, frozen } = data;
  const missing = !text.trim() ? T.edit.needText : links.length === 0 ? T.edit.needLink : null;
  return (
    <div className={`gn gn-b cn-draft${frozen ? ' frozen' : ''}`} onDoubleClick={(e) => e.stopPropagation()}>
      <div className="gn-head"><CloudBolt size={13} /><span>{T.edit.draftTitle}</span>
        {frozen && <><span className="spacer" /><span className="cn-flag mine">{T.pending.flag}</span></>}</div>
      {frozen ? (
        <>
          <div className="gn-title">{text}</div>
          <div className="cn-links">{links.map((l) => (
            <div key={l.to} className="cn-link"><span className="cn-link-name">→ {labelOf(l.to)}</span>
              <span className="cn-muted">{l.sign === '+' ? T.edit.up : T.edit.down}</span></div>
          ))}</div>
          <div className="cn-muted">{T.pending.cause}</div>
        </>
      ) : <>
      <textarea className="nodrag nopan" autoFocus rows={2} value={text} placeholder={T.edit.draftPlaceholder}
        onChange={(e) => data.onText(e.target.value)} onKeyDown={(e) => e.key === 'Escape' && data.onCancel()} />
      <div className="cn-links nodrag nopan">
        {links.length === 0 && <span className="cn-muted">{T.edit.noLinks}</span>}
        {links.map((l) => (
          <div key={l.to} className="cn-link">
            <span className="cn-link-name" title={labelOf(l.to)}>→ {labelOf(l.to)}</span>
            <span className="cn-seg">
              <button className={l.sign === '+' ? 'on' : ''} onClick={() => data.onSign(l.to, '+')}>{T.edit.up}</button>
              <button className={l.sign === '-' ? 'on' : ''} onClick={() => data.onSign(l.to, '-')}>{T.edit.down}</button>
            </span>
            <button className="cn-x" title={T.edit.remove} onClick={() => data.onRemove(l.to)}>×</button>
          </div>
        ))}
      </div>
      <div className="cn-muted cn-drag">{T.edit.dragHint} ↓</div>
      <div className="cn-edit-row nodrag">
        <button className="cn-btn" onClick={data.onCancel}>{T.edit.cancel}</button>
        <button className="cn-btn go" disabled={!!missing || busy} title={missing ?? undefined} onClick={data.onConfirm}>{T.edit.confirmCause}</button>
      </div>
      </>}
      <Handle type="source" position={Position.Bottom} className="cn-source" isConnectable={!frozen} />
    </div>
  );
}
