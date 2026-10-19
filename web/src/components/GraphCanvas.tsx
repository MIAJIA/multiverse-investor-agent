// 只读画布：节点不可拖、不可连线；位置由 toFlow 按深度算，不进 state。
// 节点样式是 playground 里选定的组合：小卡片 + 证据圆环 + 类型淡底色 + 侧边面板 + 情景下其余退后。
import { Background, Controls, ReactFlow, useReactFlow, useStore, type Edge, type Node, type NodeChange } from '@xyflow/react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { nodeConditions } from '../lookup';
import DesignNode, { type DesignData, type Look } from '../node/DesignNode';
import { nodeLabel } from '../node/labels';
import { strength } from '../node/strength';
import { toFlow, type FlowOpts } from '../toFlow';
import { BRANCH_KIND } from '../status';
import type { BranchKind, Claim, Graph, VersionBundle } from '../types';
import { T } from '../strings';

export const LOOK: Look = { shape: 'card', strength: 'ring', color: 'role', expand: 'panel', scenario: 'dim' };

const nodeTypes = { design: DesignNode };
export const FIT = { padding: 0.12 };

/** 画布尺寸变了（窗口缩放、侧栏出现）就重新铺满。
 *  React Flow 自己靠 ResizeObserver 和 window 的 resize 事件知道容器变了；页面没有在前台渲染时（例如藏在后台的浏览器面板），
 *  这两样都可能不触发，它记下的宽度就停在旧值，fitView 和左下角的「适应视图」都会按旧宽度铺，图的右边压在右侧面板下面。
 *  所以每秒比一次容器的真实尺寸和 React Flow 记下的尺寸，不一样就补发一次 resize，让它自己重新量；量完再铺满。 */
export function FitOnResize() {
  const { fitView } = useReactFlow();
  const width = useStore((st) => st.width);
  const height = useStore((st) => st.height);
  const domNode = useStore((st) => st.domNode);
  const first = useRef(true);
  useEffect(() => {
    if (first.current) { first.current = false; return; } // 第一次由 fitView 属性负责
    const t = setTimeout(() => fitView(FIT), 80);
    return () => clearTimeout(t);
  }, [width, height, fitView]);
  useEffect(() => {
    const t = setInterval(() => {
      if (domNode && (Math.abs(domNode.clientWidth - width) > 1 || Math.abs(domNode.clientHeight - height) > 1)) {
        window.dispatchEvent(new Event('resize'));
      }
    }, 1000);
    return () => clearInterval(t);
  }, [domNode, width, height]);
  return null;
}

/** 方案 B：分支类别（后端 node_kinds / edge_kinds，只查表）和高亮的那条分支。 */
export interface BranchView {
  nodeKinds: Record<string, BranchKind>;
  edgeKinds: Record<string, BranchKind>;
  syntheticNodes?: Set<string>; // 「仅推断 · 资料为占位」的节点
  highlight?: { nodes: Set<string>; edges: Set<string> } | null;
}

export default function GraphCanvas({ bundle, opts, selectedNodeId, onSelect, branchView, labelOf = nodeLabel }: {
  bundle: Pick<VersionBundle, 'excerpts'> & { graph: Graph }; opts?: FlowOpts; selectedNodeId: string | null;
  onSelect: (id: string | null) => void; branchView?: BranchView; labelOf?: (c: Claim) => string;
}) {
  const { graph, excerpts } = bundle;
  const flow = useMemo(() => toFlow(graph, opts), [graph, opts]);
  // React Flow 量出来的节点尺寸。节点是每次从快照现算的，不存这份尺寸的话，左下角的「适应视图」算不出图的范围。
  const [measured, setMeasured] = useState<Record<string, { width: number; height: number }>>({});
  const onNodesChange = (changes: NodeChange[]) => {
    const dims = changes.filter((c) => c.type === 'dimensions' && c.dimensions);
    if (dims.length) setMeasured((prev) => {
      const next = { ...prev };
      for (const c of dims) if (c.type === 'dimensions' && c.dimensions) next[c.id] = c.dimensions;
      return next;
    });
  };
  const { nodes, edges } = useMemo(() => {
    const changed = opts?.changedTargets ?? [];
    const lit = (id: string) => opts?.assessment?.[id] === 'challenged' || changed.includes(id);
    const nodes: Node<DesignData>[] = flow.nodes.map((n) => {
      const { claim } = n.data;
      return {
        id: n.id, type: 'design',
        position: { x: n.position.x * 0.85, y: n.position.y * 0.7 }, // 新卡片比旧的矮，层距收紧
        data: {
          claim, look: LOOK, label: labelOf(claim),
          s: strength(graph, claim.id, excerpts), conditions: nodeConditions(graph, claim.id),
          isKey: n.data.isKey, isChanged: n.data.isChangedTarget, assessment: n.data.assessment, expanded: false,
          kind: branchView?.nodeKinds[claim.id], synthetic: branchView?.syntheticNodes?.has(claim.id),
          dimmed: !!branchView?.highlight && !branchView.highlight.nodes.has(claim.id),
        },
      };
    });
    const edges: Edge[] = flow.edges.map((e) => {
      const k = branchView?.edgeKinds[e.id] ? BRANCH_KIND[branchView.edgeKinds[e.id]] : null;
      const off = (opts?.assessment && !(lit(e.source) && lit(e.target))) || (branchView?.highlight && !branchView.highlight.edges.has(e.id));
      return {
        id: e.id, source: e.source, target: e.target,
        style: {
          stroke: k ? k.edge : '#b9bfc8', strokeWidth: k?.line === 'dotted' ? 1.6 : 1.2,
          strokeDasharray: k ? k.dash : e.data?.modelOnly ? '5 4' : undefined,
          opacity: off ? 0.2 : 1,
        },
      };
    });
    return { nodes, edges };
  }, [flow, graph, excerpts, opts, branchView, labelOf]);

  return (
    <div className="canvas">
      <ReactFlow
        key={graph.version + (opts?.assessment ? ':scenario' : '')}
        nodes={nodes.map((n) => ({ ...n, selected: n.id === selectedNodeId, measured: measured[n.id] }))} edges={edges} nodeTypes={nodeTypes}
        onNodesChange={onNodesChange} fitView fitViewOptions={FIT}
        nodesDraggable={false} nodesConnectable={false} edgesFocusable={false}
        onNodeClick={(_, n) => onSelect(n.id)} onPaneClick={() => onSelect(null)}
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={24} />
        <Controls showInteractive={false} fitViewOptions={FIT} />
        <FitOnResize />
      </ReactFlow>
      {flow.warnings.length > 0 && <div className="banner error">{flow.warnings.join(T.graph.warningSep)}</div>}
    </div>
  );
}
