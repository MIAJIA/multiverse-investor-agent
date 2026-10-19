// 多情景 playground 用的只读画布：同一套节点样式（GraphCanvas 的 LOOK），可以给节点单独上色（叠图用）。
import { Background, ReactFlow, type Edge, type Node } from '@xyflow/react';
import { useMemo } from 'react';
import { LOOK } from '../components/GraphCanvas';
import { keyClaimId, nodeConditions } from '../lookup';
import DesignNode, { type DesignData } from '../node/DesignNode';
import { demoLabel } from '../playground/demoLabels';
import { strength } from '../node/strength';
import { toFlow } from '../toFlow';
import type { VersionBundle } from '../types';
import type { Coloring } from './model';

const nodeTypes = { design: DesignNode };

export default function ScenarioCanvas({ bundle, coloring, tints, compact }: {
  bundle: VersionBundle; coloring?: Coloring; tints?: Record<string, string>; compact?: boolean;
}) {
  const { nodes, edges } = useMemo(() => {
    const { graph, excerpts } = bundle;
    const flow = toFlow(graph);
    const key = keyClaimId(bundle.proposals[0], graph); // 实验页：只标第一份计划的关键依赖
    const changed = coloring?.changed ?? [];
    const lit = (id: string) => !!tints?.[id] || coloring?.assessment[id] === 'challenged' || changed.includes(id);
    const anyColor = !!coloring || !!tints;
    const nodes: Node<DesignData>[] = flow.nodes.map((n) => {
      const { claim } = n.data;
      return {
        id: n.id, type: 'design', position: { x: n.position.x * 0.85, y: n.position.y * 0.7 },
        data: {
          claim, look: LOOK, label: demoLabel(claim, changed.includes(claim.id)), s: strength(graph, claim.id, excerpts),
          conditions: nodeConditions(graph, claim.id), isKey: claim.id === key, isChanged: changed.includes(claim.id),
          assessment: tints ? (tints[claim.id] ? undefined : anyColor ? 'unaffected' : undefined) : coloring?.assessment[claim.id],
          expanded: false, tint: tints?.[claim.id],
        },
      };
    });
    const edges: Edge[] = flow.edges.map((e) => ({
      id: e.id, source: e.source, target: e.target,
      style: {
        stroke: '#b9bfc8', strokeWidth: 1.2, strokeDasharray: e.data?.modelOnly ? '5 4' : undefined,
        opacity: anyColor && !(lit(e.source) && lit(e.target)) ? 0.25 : 1,
      },
    }));
    return { nodes, edges };
  }, [bundle, coloring, tints]);

  return (
    <div className="pg-canvas" style={compact ? { minHeight: 0 } : undefined}>
      <ReactFlow key={bundle.graph.version + JSON.stringify(coloring?.changed ?? []) + Object.keys(tints ?? {}).join()}
        nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView fitViewOptions={{ padding: 0.1 }}
        nodesDraggable={false} nodesConnectable={false} elementsSelectable={false} proOptions={{ hideAttribution: true }}>
        <Background gap={22} color="#e6e8ec" />
      </ReactFlow>
    </div>
  );
}
