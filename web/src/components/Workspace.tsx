// B1 Research Workspace：所有修改都在这张图上做（改节点、加原因），没有单独的情景页。
// 改完后同一块画布显示新版本：你改的节点、受影响的节点（后端 assessment）、要重新批准的结论（后端 approval_reset）；
// 顶部可以在「改之前 / 改之后」之间切换。点一个结论高亮它的整条分支，右侧显示计划摘要；点其他节点看证据。
import { useMemo } from 'react';
import { editedIds } from '../edits';
import { ancestors, branchOf, keyClaimIds, planOf } from '../lookup';
import { nodeLabel } from '../node/labels';
import { T } from '../strings';
import type { Op, VersionBundle } from '../types';
import { BranchTag } from './BranchSwatch';
import EditableCanvas, { type ScenarioMarks } from './EditableCanvas';
import type { BranchView } from './GraphCanvas';
import NodePanel from './NodePanel';
import PlanSummary from './PlanSummary';

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

export default function Workspace({ versions, base, scenario, viewing, busy, selectedNodeId, selectedTerminalId,
  onSelectNode, onSelectTerminal, onGoApprove, onToggle, onEdit, onReapproveHere }: {
  versions: Record<string, VersionBundle>; base: VersionBundle; scenario: VersionBundle | null;
  viewing: 'base' | 'scenario'; busy: boolean; selectedNodeId: string | null; selectedTerminalId: string | null;
  onSelectNode: (id: string | null) => void; onSelectTerminal: (id: string | null) => void; onGoApprove: () => void;
  onToggle: (v: 'base' | 'scenario') => void;
  onEdit: (baseVersion: string, op: Op) => void; // 在当前显示的版本上 fork
  onReapproveHere: () => void;
}) {
  const sc = scenario?.scenario ?? null;
  const before = (sc && versions[sc.base_version]) || base; // 「改之前」是情景自己声明的 base_version
  const showScenario = viewing === 'scenario' && !!sc;
  const shown = showScenario ? scenario! : before;
  const marks = useMemo<ScenarioMarks | null>(() => (showScenario ? {
    assessment: sc!.assessment, edited: editedIds(sc),
    reapprove: new Set(scenario!.proposals.filter((p) => p.approval_reset).map((p) => p.terminal_id)),
  } : null), [showScenario, sc, scenario]);
  const view = useMemo(() => branchViewOf(shown, showScenario ? null : selectedTerminalId), [shown, showScenario, selectedTerminalId]);
  const keyIds = useMemo(() => keyClaimIds(shown), [shown]);
  const node = (id: string) => shown.graph.nodes.find((n) => n.id === id);
  const plan = planOf(shown, selectedTerminalId);
  const challenged = sc ? Object.values(sc.assessment).filter((s) => s === 'challenged').length : 0;
  const reapprove = scenario ? scenario.proposals.filter((p) => p.approval_reset).length : 0;

  return (
    <div className="split">
      <div className="col">
        {sc ? (
          <div className="fork-form">
            <div className="toggle">
              <button className={!showScenario ? 'on' : ''} onClick={() => onToggle('base')}>{T.edit.before(sc.base_version)}</button>
              <button className={showScenario ? 'on' : ''} onClick={() => onToggle('scenario')}>{T.edit.after(sc.version)}</button>
            </div>
            <span className="small">{T.edit.summary(editedIds(sc).length, challenged, reapprove)}</span>
            {scenario!.proposals.length > 0 && <button className="secondary" onClick={onReapproveHere}>{T.edit.reapproveHere}</button>}
            <span className="small muted">{T.edit.stackHint}</span>
          </div>
        ) : (
          <div className="legend"><span className="small muted">{T.b1.highlightHint}</span></div>
        )}
        <EditableCanvas bundle={shown} branchView={view} keyIds={keyIds} marks={marks} busy={busy}
          selectedNodeId={selectedNodeId ?? selectedTerminalId}
          onSelect={(id) => {
            if (id && node(id)?.role === 'terminal') { onSelectTerminal(id); onSelectNode(null); }
            else { onSelectNode(id); if (!id) onSelectTerminal(null); }
          }}
          onChangeNode={(target, value) => onEdit(shown.graph.version, { kind: 'change_assumption', target, value, impacts: [], new_nodes: [], new_edges: [] })}
          onAddCause={(op) => onEdit(shown.graph.version, op)} />
      </div>
      {selectedNodeId && node(selectedNodeId) ? (
        <NodePanel bundle={shown} nodeId={selectedNodeId} assessment={sc && showScenario ? sc.assessment[selectedNodeId] : undefined}
          reason={sc && showScenario ? sc.assessment_reason[selectedNodeId] : undefined} />
      ) : plan ? (
        <PlanSummary graph={shown.graph} plan={plan} branch={branchOf(shown, plan.terminal_id)} onGoApprove={onGoApprove} />
      ) : (
        <aside className="panel">
          <p className="muted">{T.b1.intro(shown.branches.length)}</p>
          {shown.branches.map((b) => (
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
