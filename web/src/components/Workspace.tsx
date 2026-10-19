// B1 Research Workspace：只读画布 + 右侧面板。
import { useMemo } from 'react';
import { keyClaimId } from '../lookup';
import type { VersionBundle } from '../types';
import GraphCanvas from './GraphCanvas';
import NodePanel from './NodePanel';
import { T } from '../strings';

export default function Workspace({ bundle, selectedNodeId, onSelect }: {
  bundle: VersionBundle; selectedNodeId: string | null; onSelect: (id: string | null) => void;
}) {
  const opts = useMemo(() => ({ keyClaimId: keyClaimId(bundle.proposal, bundle.graph) }), [bundle]);
  return (
    <div className="split">
      <GraphCanvas bundle={bundle} opts={opts} selectedNodeId={selectedNodeId} onSelect={onSelect} />
      {selectedNodeId ? (
        <NodePanel bundle={bundle} nodeId={selectedNodeId} />
      ) : (
        <aside className="panel">
          <p className="muted">{T.workspace.hint}</p>
          <p className="small muted">{T.workspace.legend}</p>
        </aside>
      )}
    </div>
  );
}
