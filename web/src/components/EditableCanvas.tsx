// B1 画布：所有修改都在图上做。
// - 改节点：点节点上的铅笔，说法就地变成输入框，确认 → onChangeNode（上层发 change_assumption）
// - 加原因：双击空白处或点「＋ 加一个原因」出现草稿节点，从它底部的圆点拖到已有节点，每条线选推高 / 压低，确认 → onAddCause（add_shock）
// 只能从草稿连到已有节点（edits.ts 的 canLink）；其他拖拽一律连不上。删节点、插中间、改连线都不支持。
import {
  Background, Controls, ReactFlow, ReactFlowProvider, useReactFlow,
  type Connection, type Edge, type Node, type NodeChange,
} from '@xyflow/react';
import { useMemo, useRef, useState } from 'react';
import { addShockOp, canLink, freshCauseId, type DraftLink, type Sign } from '../edits';
import CanvasNode, { type CanvasData } from '../node/CanvasNode';
import DraftNode, { type DraftData } from '../node/DraftNode';
import { nodeLabel } from '../node/labels';
import { strength } from '../node/strength';
import { BRANCH_KIND } from '../status';
import { T } from '../strings';
import { toFlow } from '../toFlow';
import type { AssessmentStatus, Op, VersionBundle } from '../types';
import { FIT, FitOnResize, type BranchView } from './GraphCanvas';

const nodeTypes = { canvas: CanvasNode, draft: DraftNode };

export interface ScenarioMarks {
  assessment: Record<string, AssessmentStatus>;
  edited: string[];
  reapprove: Set<string>; // 需要重新批准的结论 id
}

interface Draft { id: string; text: string; links: DraftLink[]; position: { x: number; y: number } }

export interface EditableCanvasProps {
  bundle: VersionBundle;
  branchView: BranchView;
  keyIds: string[];
  marks: ScenarioMarks | null;
  selectedNodeId: string | null;
  busy: boolean;
  onSelect: (id: string | null) => void;
  onChangeNode: (target: string, value: string) => void;
  onAddCause: (op: Op) => void;
}

function Inner({ bundle, branchView, keyIds, marks, selectedNodeId, busy, onSelect, onChangeNode, onAddCause }: EditableCanvasProps) {
  const { graph, excerpts } = bundle;
  const rf = useReactFlow();
  const wrap = useRef<HTMLDivElement>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [measured, setMeasured] = useState<Record<string, { width: number; height: number }>>({});
  const flow = useMemo(() => toFlow(graph, { keyClaimIds: keyIds }), [graph, keyIds]);
  const label = (id: string) => { const n = graph.nodes.find((x) => x.id === id); return n ? nodeLabel(n) : id; };

  const startDraft = (position: { x: number; y: number }) => {
    if (busy) return;
    setEditingId(null);
    setDraft((d) => d ?? { id: freshCauseId(graph), text: '', links: [], position });
  };
  const centerDraft = () => {
    const r = wrap.current?.getBoundingClientRect();
    if (r) startDraft(rf.screenToFlowPosition({ x: r.right - 300, y: r.top + 56 })); // 右上角，尽量不压住已有节点
  };

  const nodes = useMemo(() => {
    const keys = new Set(keyIds);
    const out: Node[] = flow.nodes.map((n): Node<CanvasData> => {
      const claim = n.data.claim;
      const terminal = claim.role === 'terminal';
      return {
        id: n.id, type: 'canvas', position: { x: n.position.x, y: n.position.y * 0.72 },
        selected: n.id === selectedNodeId, measured: measured[n.id], zIndex: n.id === editingId ? 10 : 0,
        data: {
          claim, label: nodeLabel(claim), s: strength(graph, claim.id, excerpts), kind: branchView.nodeKinds[claim.id],
          isKey: keys.has(claim.id),
          dimmed: !marks && !!branchView.highlight && !branchView.highlight.nodes.has(claim.id),
          assessment: marks?.assessment[claim.id], changed: !!marks?.edited.includes(claim.id),
          reapprove: !!marks?.reapprove.has(claim.id),
          canEdit: !terminal && !draft && (claim.role === 'assumption' || n.id === selectedNodeId),
          editing: n.id === editingId, busy,
          onEditStart: () => { setEditingId(n.id); onSelect(n.id); },
          onEditCancel: () => setEditingId(null),
          onEditCommit: (text) => { setEditingId(null); onChangeNode(n.id, text.trim()); },
        },
      };
    });
    if (draft) {
      out.push({
        id: draft.id, type: 'draft', position: draft.position, draggable: true, measured: measured[draft.id], zIndex: 20,
        data: {
          text: draft.text, links: draft.links, labelOf: label, busy,
          onText: (text) => setDraft((d) => d && { ...d, text }),
          onSign: (to: string, sign: Sign) => setDraft((d) => d && { ...d, links: d.links.map((l) => (l.to === to ? { ...l, sign } : l)) }),
          onRemove: (to: string) => setDraft((d) => d && { ...d, links: d.links.filter((l) => l.to !== to) }),
          onCancel: () => setDraft(null),
          onConfirm: () => { onAddCause(addShockOp(draft.id, draft.text, draft.links)); setDraft(null); },
        } satisfies DraftData,
      });
    }
    return out;
  }, [flow, graph, excerpts, branchView, keyIds, marks, selectedNodeId, editingId, draft, busy, measured]);

  const edges = useMemo(() => {
    const out: Edge[] = flow.edges.map((e) => {
      const k = branchView.edgeKinds[e.id] ? BRANCH_KIND[branchView.edgeKinds[e.id]] : null;
      const off = marks
        ? marks.assessment[e.target] === 'unaffected' || (!marks.assessment[e.target] && !marks.edited.includes(e.source))
        : !!branchView.highlight && !branchView.highlight.edges.has(e.id);
      return {
        id: e.id, source: e.source, target: e.target,
        style: { stroke: '#8a919c', strokeWidth: 1.4, strokeDasharray: k?.dash, opacity: off ? 0.2 : 1 },
      };
    });
    for (const l of draft?.links ?? []) {
      out.push({
        id: `${draft!.id}->${l.to}`, source: draft!.id, target: l.to, animated: true,
        label: l.sign === '+' ? T.edit.up : T.edit.down,
        style: { stroke: '#2f6fed', strokeWidth: 2 }, labelStyle: { fill: '#2f6fed', fontWeight: 600 },
      });
    }
    return out;
  }, [flow, branchView, marks, draft]);

  const onNodesChange = (changes: NodeChange[]) => {
    for (const c of changes) {
      if (c.type === 'dimensions' && c.dimensions) { const dims = c.dimensions; setMeasured((p) => ({ ...p, [c.id]: dims })); }
      if (c.type === 'position' && c.position && draft && c.id === draft.id) { const pos = c.position; setDraft((d) => d && { ...d, position: pos }); }
    }
  };
  const valid = (c: Connection | Edge) => !!draft && canLink(graph, draft.id, draft.links, c.source, c.target);

  return (
    <div className="canvas" ref={wrap} onDoubleClick={(e) => {
      if ((e.target as Element).classList.contains('react-flow__pane')) startDraft(rf.screenToFlowPosition({ x: e.clientX, y: e.clientY }));
    }}>
      <ReactFlow
        key={graph.version}
        nodes={nodes} edges={edges} nodeTypes={nodeTypes} onNodesChange={onNodesChange}
        fitView fitViewOptions={FIT} zoomOnDoubleClick={false}
        nodesDraggable={false} nodesConnectable={!!draft} edgesFocusable={false}
        isValidConnection={valid}
        onConnect={(c) => { if (valid(c)) setDraft((d) => d && { ...d, links: [...d.links, { to: c.target!, sign: '+' }] }); }}
        onNodeClick={(_, n) => { if (n.type === 'canvas') onSelect(n.id); }}
        onPaneClick={() => { if (!editingId) onSelect(null); }}
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={24} />
        <Controls showInteractive={false} fitViewOptions={FIT} />
        <FitOnResize />
      </ReactFlow>
      <div className="canvas-tools">
        <button className="secondary" disabled={busy || !!draft} onClick={centerDraft}>{T.edit.addCause}</button>
        <span className="small muted">{T.edit.addHint}</span>
      </div>
    </div>
  );
}

export default function EditableCanvas(props: EditableCanvasProps) {
  return <ReactFlowProvider><Inner {...props} /></ReactFlowProvider>;
}
