// 左侧：研究记录（每个问题一个工作区）+ 跨工作区的已批准计划总览 +「新建研究」。数据来自 workspaces.ts 的 store。
import { T } from '../strings';
import { approvedOverview, latestApproval, type Workspace, type WorkspaceStore } from '../workspaces';

export default function WorkspaceSidebar({ store, missing, onOpen, onNew, onOpenApproved }: {
  store: WorkspaceStore;
  missing: Set<string>; // 这次会话里发现后端已经找不到运行的工作区
  onOpen: (id: string) => void;
  onNew: () => void;
  onOpenApproved: (id: string) => void;
}) {
  const statusOf = (w: Workspace) => (missing.has(w.id) ? 'missing' : w.status);
  const approved = approvedOverview(store);
  return (
    <aside className="ws-side">
      <button className="ws-new" onClick={onNew}>{T.ws.newResearch}</button>

      <div className="ws-section">{T.ws.approvedTitle}</div>
      {approved.length === 0 && <p className="ws-empty">{T.ws.noApproved}</p>}
      {approved.map(({ workspace, approval }) => (
        <button key={workspace.id} className="ws-approved" onClick={() => onOpenApproved(workspace.id)}>
          <span className="ws-approved-title">{approval.title}</span>
          <span className="ws-meta">{workspace.event}</span>
          <span className="ws-meta">{T.ws.date(approval.at)}</span>
        </button>
      ))}

      <div className="ws-section">{T.ws.history}</div>
      {store.workspaces.length === 0 && <p className="ws-empty">{T.ws.noHistory}</p>}
      {store.workspaces.map((w) => {
        const st = statusOf(w);
        const a = latestApproval(w);
        const revoked = !a && w.approvals.length > 0;
        return (
          <button key={w.id} className={`ws-item${w.id === store.currentId ? ' on' : ''}`} onClick={() => onOpen(w.id)}>
            <span className="ws-event">{w.event}</span>
            <span className="ws-row">
              <span className={`ws-status ${st}`}>{T.ws.status[st]}</span>
              <span className="ws-meta">{T.ws.date(w.createdAt)}</span>
              {w.online && <span className="ws-meta">{T.ws.online}</span>}
            </span>
            <span className={`ws-meta${a ? ' ok' : ''}`}>
              {a ? T.ws.approved(a.title ?? '') : revoked ? T.ws.revoked : w.note ? T.ws.noGraph : w.status === 'ready' ? T.ws.notApproved : ''}
            </span>
          </button>
        );
      })}
    </aside>
  );
}
