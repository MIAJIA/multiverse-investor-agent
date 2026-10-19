// 方案 B 视觉预览用的演示数据：取 c1_multi 的 c1-v3（加了「代工停产」冲击）真实版本包——三份计划、分支、类别都是后端
// 给的；只有一处手改：把 LITE 分支和共用主干改成「有资料支持」，因为 fixture 用的是占位资料包，真实数据里没有这一类。
import type { Fixture, VersionBundle } from '../types';

export const DEMO_SUBTITLE = 'C1 + scenario "foundry outage"';
export const DEMO_NOTE = 'Demo data: "Backed by sources" on the LITE branch and the shared trunk was set by hand; everything else comes from the back end';

const DEMO_EVIDENCED = 'c1.term.laser_vendor';

export function demoBundle(fx: Fixture): VersionBundle {
  const b = structuredClone(fx.versions['c1-v3']);
  const lite = b.branches.find((x) => x.terminal_id === DEMO_EVIDENCED)!;
  lite.kind = 'evidenced';
  lite.synthetic_evidence = false;
  for (const br of b.branches) br.trunk = 'evidenced';
  const others = new Set(b.branches.filter((x) => x.terminal_id !== DEMO_EVIDENCED).flatMap((x) => x.own_node_ids));
  for (const n of b.graph.nodes) {
    if (!others.has(n.id) && b.node_kinds[n.id] !== 'hypothetical') b.node_kinds[n.id] = 'evidenced';
  }
  for (const e of b.graph.edges) b.edge_kinds[e.id] = b.node_kinds[e.to];
  return b;
}
