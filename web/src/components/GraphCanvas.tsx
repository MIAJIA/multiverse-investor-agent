// 只读画布：节点不可拖、不可连线；位置由 toFlow 按深度算，不进 state。
// 节点样式是 playground 里选定的组合：小卡片 + 证据圆环 + 类型淡底色 + 侧边面板 + 情景下其余退后。
import { Background, Controls, ReactFlow, type Edge, type Node } from '@xyflow/react';
import { useMemo } from 'react';
import { nodeConditions } from '../lookup';
import DesignNode, { type DesignData, type Look } from '../node/DesignNode';
import { shortLabel } from '../node/labels';
import { strength } from '../node/strength';
import { toFlow, type FlowOpts } from '../toFlow';
import type { VersionBundle } from '../types';

export const LOOK: Look = { shape: 'card', strength: 'ring', color: 'role', expand: 'panel', scenario: 'dim' };

const nodeTypes = { design: DesignNode };

export default function GraphCanvas({ bundle, opts, selectedNodeId, onSelect }: {
  bundle: VersionBundle; opts?: FlowOpts; selectedNodeId: string | null; onSelect: (id: string | null) => void;
}) {
  const { graph, excerpts } = bundle;
  const flow = useMemo(() => toFlow(graph, opts), [graph, opts]);
  const { nodes, edges } = useMemo(() => {
    const changed = opts?.changedTargets ?? [];
    const lit = (id: string) => opts?.assessment?.[id] === 'challenged' || changed.includes(id);
    const nodes: Node<DesignData>[] = flow.nodes.map((n) => {
      const { claim } = n.data;
      return {
        id: n.id, type: 'design',
        position: { x: n.position.x * 0.85, y: n.position.y * 0.7 }, // 新卡片比旧的矮，层距收紧
        data: {
          claim, look: LOOK, label: shortLabel(claim.id, claim.statement, changed.includes(claim.id)),
          s: strength(graph, claim.id, excerpts), conditions: nodeConditions(graph, claim.id),
          isKey: n.data.isKey, isChanged: n.data.isChangedTarget, assessment: n.data.assessment, expanded: false,
        },
      };
    });
    const edges: Edge[] = flow.edges.map((e) => ({
      id: e.id, source: e.source, target: e.target,
      style: {
        stroke: '#b9bfc8', strokeWidth: 1.2, strokeDasharray: e.data?.modelOnly ? '5 4' : undefined,
        opacity: opts?.assessment && !(lit(e.source) && lit(e.target)) ? 0.25 : 1,
      },
    }));
    return { nodes, edges };
  }, [flow, graph, excerpts, opts]);

  return (
    <div className="canvas">
      <ReactFlow
        key={graph.version + (opts?.assessment ? ':scenario' : '')}
        nodes={nodes.map((n) => ({ ...n, selected: n.id === selectedNodeId }))} edges={edges} nodeTypes={nodeTypes}
        fitView fitViewOptions={{ padding: 0.12 }}
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
