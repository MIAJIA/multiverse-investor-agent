// B1 Research Workspace（方案 B）：只读画布，三类分支按后端的 node_kinds / edge_kinds 着色；
// 点一个结论高亮它的整条分支（独有部分 + 祖先），右侧显示这份计划的摘要；点其他节点看证据。
import { useMemo } from 'react';
import { ancestors, branchOf, keyClaimIds, planOf } from '../lookup';
import { T } from '../strings';
import type { VersionBundle } from '../types';
import { BranchTag } from './BranchSwatch';
import GraphCanvas, { type BranchView } from './GraphCanvas';
import NodePanel from './NodePanel';
import PlanSummary from './PlanSummary';
import { nodeLabel } from '../node/labels';

export function branchViewOf(bundle: VersionBundle, terminalId: string | null): BranchView {
  const b = branchOf(bundle, terminalId);
  const nodes = b ? new Set([...b.own_node_ids, ...ancestors(bundle.graph, b.terminal_id)]) : null;
  return {
    nodeKinds: bundle.node_kinds, edgeKinds: bundle.edge_kinds,
    syntheticNodes: new Set(bundle.branches.filter((x) => x.synthetic_evidence).flatMap((x) => x.own_node_ids)),
    highlight: nodes
      ? { nodes, edges: new Set(bundle.graph.edges.filter((e) => nodes.has(e.from) && nodes.has(e.to)).map((e) => e.id)) }
      : null,
  };
}

export default function Workspace({ bundle, selectedNodeId, selectedTerminalId, onSelectNode, onSelectTerminal, onGoApprove }: {
  bundle: VersionBundle; selectedNodeId: string | null; selectedTerminalId: string | null;
  onSelectNode: (id: string | null) => void; onSelectTerminal: (id: string | null) => void; onGoApprove: () => void;
}) {
  const view = useMemo(() => branchViewOf(bundle, selectedTerminalId), [bundle, selectedTerminalId]);
  const opts = useMemo(() => ({ keyClaimIds: keyClaimIds(bundle) }), [bundle]);
  const node = (id: string) => bundle.graph.nodes.find((n) => n.id === id);
  const plan = planOf(bundle, selectedTerminalId);
  return (
    <div className="split">
      <div className="col">
        <div className="legend"><span className="small muted">{T.b1.highlightHint}</span></div>
        <GraphCanvas bundle={bundle} opts={opts} branchView={view} selectedNodeId={selectedNodeId ?? selectedTerminalId}
          onSelect={(id) => {
            if (id && node(id)?.role === 'terminal') { onSelectTerminal(id); onSelectNode(null); }
            else { onSelectNode(id); if (!id) onSelectTerminal(null); }
          }} />
      </div>
      {selectedNodeId ? (
        <NodePanel bundle={bundle} nodeId={selectedNodeId} />
      ) : plan ? (
        <PlanSummary graph={bundle.graph} plan={plan} branch={branchOf(bundle, plan.terminal_id)} onGoApprove={onGoApprove} />
      ) : (
        <aside className="panel">
          <p className="muted">{T.b1.intro(bundle.branches.length)}</p>
          {bundle.branches.map((b) => (
            <p key={b.terminal_id} className="small">
              <button className="link" onClick={() => onSelectTerminal(b.terminal_id)}>{nodeLabel(node(b.terminal_id)!)}</button>{' '}
              <BranchTag kind={b.kind} synthetic={b.synthetic_evidence} />
            </p>
          ))}
          <p className="small muted">{T.b1.legend}</p>
        </aside>
      )}
    </div>
  );
}
