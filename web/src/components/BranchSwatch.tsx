// 分支类别的缩略：B2 结论列表的行首竖条、B1 结论卡片和 B3 计划对比上的标签。样式全部来自 status.ts 的 BRANCH_KIND。
import { BRANCH_KIND, SYNTHETIC_EVIDENCE_TAG } from '../status';
import type { BranchKind } from '../types';
import { T } from '../strings';

/** 行首竖条：实色 / 虚线 / 斜线灰紫，和画布上的节点同一套视觉。 */
export function BranchBar({ kind }: { kind: BranchKind }) {
  const k = BRANCH_KIND[kind];
  return (
    <span
      className="branch-bar"
      aria-label={k.label}
      title={k.label}
      style={{
        borderColor: k.border,
        borderStyle: k.line,
        background: kind === 'evidenced' ? k.border : k.bg,
        backgroundImage: k.pattern,
      }}
    />
  );
}

/** 标签：有资料支持默认不加字；仅推断写「仅推断」（占位资料再加「· 资料为占位」）；假设写醒目的「假设 · 未观测」。 */
export function BranchTag({ kind, synthetic = false }: { kind: BranchKind; synthetic?: boolean }) {
  const k = BRANCH_KIND[kind];
  if (!k.tag) return null;
  const text = kind === 'model_only' && synthetic ? `${k.tag} · ${SYNTHETIC_EVIDENCE_TAG}` : k.tag;
  return (
    <span className={`branch-tag ${kind}`} style={{ color: k.color, background: k.bg, borderColor: k.border }}>
      {text}
    </span>
  );
}

/** 假设分支的计划卡片顶部横幅。 */
export function HypotheticalBanner({ what }: { what?: string }) {
  const k = BRANCH_KIND.hypothetical;
  return (
    <div className="branch-banner" style={{ color: k.title, background: k.bg, backgroundImage: k.pattern, borderColor: k.border }}>
      <BranchTag kind="hypothetical" /> {T.branchBanner(what)}
    </div>
  );
}
