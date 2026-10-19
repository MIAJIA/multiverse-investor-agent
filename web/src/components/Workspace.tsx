// B1 Research Workspace：只读画布 + 右侧面板。
import { useMemo } from 'react';
import { keyClaimId } from '../lookup';
import type { VersionBundle } from '../types';
import GraphCanvas from './GraphCanvas';
import NodePanel from './NodePanel';

export default function Workspace({ bundle, selectedNodeId, onSelect }: {
  bundle: VersionBundle; selectedNodeId: string | null; onSelect: (id: string | null) => void;
}) {
  const opts = useMemo(() => ({ keyClaimId: keyClaimId(bundle.proposal, bundle.graph) }), [bundle]);
  return (
    <div className="split">
      <GraphCanvas graph={bundle.graph} opts={opts} selectedNodeId={selectedNodeId} onSelect={onSelect} />
      {selectedNodeId ? (
        <NodePanel bundle={bundle} nodeId={selectedNodeId} />
      ) : (
        <aside className="panel">
          <p className="muted">点一个节点，看它的证据和「什么会证明我错」。</p>
          <p className="small muted">实线 = 有引用；虚线 = 仅模型推断。外发光的是关键依赖。</p>
        </aside>
      )}
    </div>
  );
}
