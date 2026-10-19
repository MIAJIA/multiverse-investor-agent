// 只读画布：节点不可拖、不可连线；位置由 toFlow 按深度算，不进 state。
import { Background, Controls, ReactFlow } from '@xyflow/react';
import { useMemo } from 'react';
import { toFlow, type FlowOpts } from '../toFlow';
import type { Graph } from '../types';
import ClaimNode from './ClaimNode';

const nodeTypes = { claim: ClaimNode };

export default function GraphCanvas({ graph, opts, selectedNodeId, onSelect }: {
  graph: Graph; opts?: FlowOpts; selectedNodeId: string | null; onSelect: (id: string | null) => void;
}) {
  const flow = useMemo(() => toFlow(graph, opts), [graph, opts]);
  const nodes = flow.nodes.map((n) => ({ ...n, selected: n.id === selectedNodeId }));
  return (
    <div className="canvas">
      <ReactFlow
        key={graph.version + (opts?.assessment ? ':scenario' : '')}
        nodes={nodes} edges={flow.edges} nodeTypes={nodeTypes} fitView
        nodesDraggable={false} nodesConnectable={false} edgesFocusable={false}
        onNodeClick={(_, n) => onSelect(n.id)} onPaneClick={() => onSelect(null)}
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={24} />
        <Controls showInteractive={false} />
      </ReactFlow>
      {flow.warnings.length > 0 && <div className="banner error">{flow.warnings.join('；')}</div>}
    </div>
  );
}
