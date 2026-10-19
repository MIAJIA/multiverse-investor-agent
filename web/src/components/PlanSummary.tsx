// B1 右侧：选中一个结论时的计划摘要（类别标签、方向、gate、你需要相信、先查、去批准）。B1 和预览页共用。
import { nodeLabel } from '../node/labels';
import { GATE } from '../status';
import { T } from '../strings';
import type { Branch, Claim, Graph, TradeProposal } from '../types';
import Badge from './Badge';
import { BranchTag } from './BranchSwatch';

export default function PlanSummary({ graph, plan, branch, onGoApprove, labelOf = nodeLabel }: {
  graph: Graph; plan: TradeProposal; branch: Branch | null; onGoApprove: () => void; labelOf?: (c: Claim) => string;
}) {
  const node = (id: string) => graph.nodes.find((n) => n.id === id)!;
  const premises = (branch?.own_node_ids ?? []).filter((id) => id !== plan.terminal_id).map((id) => labelOf(node(id)));
  return (
    <aside className="panel">
      <h3>{labelOf(node(plan.terminal_id))} {branch && <BranchTag kind={branch.kind} synthetic={branch.synthetic_evidence} />}</h3>
      <p className="small">{T.b1.side(plan.direction.side)} <b>{plan.direction.instrument}</b>{plan.direction.note ? ` · ${plan.direction.note}` : ''}</p>
      <div className="row">
        <Badge look={GATE[plan.gate]} />
        {plan.user_judgment.confirmed && <span className="ok small">{T.b1.approved}</span>}
        {plan.approval_reset && <span className="warn small">{T.b1.approvalReset}</span>}
      </div>
      <p className="small">{T.b1.youNeedToBelieve(premises)}</p>
      {plan.key_dependency && <p className="small key-why">{T.b1.checkFirst(plan.key_dependency.why)}</p>}
      <button className="primary" onClick={onGoApprove}>{T.b1.goApprove}</button>
    </aside>
  );
}
