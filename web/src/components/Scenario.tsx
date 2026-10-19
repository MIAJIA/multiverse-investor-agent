// B3 Scenario Diff：改一个假设 → fork；基线 / 情景切换；画布按 assessment 三态着色；右侧三块。
// assessment、diff、新版本的计划全部来自后端；失效标记读 approval_reset / rival_changed，不在前端比较。
import { useMemo, useState } from 'react';
import { changedTargets, keyClaimIds, planOf } from '../lookup';
import { nodeLabel } from '../node/labels';
import { ASSESSMENT, GATE, ROLE, SUPPORT } from '../status';
import type { TradeProposal, VersionBundle } from '../types';
import Badge from './Badge';
import GraphCanvas from './GraphCanvas';
import NodePanel from './NodePanel';
import { T } from '../strings';

function ForkForm({ bundle, busy, onFork }: { bundle: VersionBundle; busy: boolean; onFork: (t: string, v: string) => void }) {
  const nodes = [...bundle.graph.nodes].sort((a, b) => Number(b.role === 'assumption') - Number(a.role === 'assumption'));
  const [target, setTarget] = useState(nodes[0]?.id ?? '');
  const [value, setValue] = useState('');
  return (
    <div className="fork-form">
      <span className="small">{T.scenario.ifLabel}</span>
      <select value={target} onChange={(e) => { setTarget(e.target.value); setValue(''); }}>
        {nodes.map((n) => <option key={n.id} value={n.id}>{T.scenario.roleOption(ROLE[n.role].label, n.statement)}</option>)}
      </select>
      <span className="small">{T.scenario.changeTo}</span>
      <input value={value} placeholder={T.scenario.valuePlaceholder}
        onChange={(e) => setValue(e.target.value)} />
      <button className="primary" disabled={busy || !target || !value.trim()} onClick={() => onFork(target, value.trim())}>{T.scenario.fork}</button>
    </div>
  );
}

/** 一份计划在基线和情景两个版本里的样子：gate、支持度并排；批准状态只读后端字段。 */
function PlanRow({ title, a, b }: { title: string; a: TradeProposal | null; b: TradeProposal }) {
  return (
    <div className="plan-row">
      <div className="plan-row-title">{title} <span className="mono">{b.direction.instrument}</span>
        {b.user_judgment.confirmed && <span className="ok small"> {T.b3.approved}</span>}</div>
      <div className="row small">
        {a && <><Badge look={GATE[a.gate]} />→</>}<Badge look={GATE[b.gate]} />
        <span style={{ color: SUPPORT[b.support_status].color }}>{T.b3.support(b.support_status)}</span>
      </div>
      {b.approval_reset && <div className="warn small">{T.b3.approvalReset}</div>}
      {b.rival_changed && !b.approval_reset && <div className="small muted">{T.b3.rivalChanged}</div>}
    </div>
  );
}

export default function Scenario({ versions, base, scenario, viewing, busy, selectedNodeId, onSelect, onToggle, onFork, onReapproveHere }: {
  versions: Record<string, VersionBundle>; base: VersionBundle; scenario: VersionBundle | null;
  viewing: 'base' | 'scenario'; busy: boolean; selectedNodeId: string | null;
  onSelect: (id: string | null) => void; onToggle: (v: 'base' | 'scenario') => void; onFork: (t: string, v: string) => void;
  onReapproveHere: () => void; // 把情景版本设为 B2 的当前版本，去重新批准
}) {
  // 对比的基线是情景自己声明的 base_version，不一定是当前 B1 / B2 的版本
  const baseB = (scenario?.scenario && versions[scenario.scenario.base_version]) || base;
  const showScenario = viewing === 'scenario' && scenario?.scenario;
  const shown = showScenario ? scenario! : baseB;
  const sc = scenario?.scenario ?? null;
  const opts = useMemo(() => (showScenario
    ? { assessment: sc!.assessment, changedTargets: changedTargets(sc), keyClaimIds: keyClaimIds(scenario!) }
    : { keyClaimIds: keyClaimIds(baseB) }), [showScenario, sc, scenario, baseB]);
  const name = (id: string) => shown.graph.nodes.find((n) => n.id === id)?.statement ?? id;
  const challenged = sc ? Object.entries(sc.assessment).filter(([, s]) => s === 'challenged').map(([id]) => id) : [];

  return (
    <div className="col">
      <ForkForm bundle={base} busy={busy} onFork={onFork} />
      {sc && (
        <div className="fork-form">
          <div className="toggle">
            <button className={!showScenario ? 'on' : ''} onClick={() => onToggle('base')}>{T.scenario.base(sc.base_version)}</button>
            <button className={showScenario ? 'on' : ''} onClick={() => onToggle('scenario')}>{T.scenario.scenario(sc.version)}</button>
          </div>
          <span className="small">{T.scenario.opsLine(sc.ops.map((o) => String(o.value)))}</span>
          <span className="badge" style={{ color: ROLE.shock.color, borderColor: ROLE.shock.color }}>{T.scenario.notObserved}</span>
        </div>
      )}
      <div className="split">
        <GraphCanvas bundle={shown} opts={opts} selectedNodeId={selectedNodeId} onSelect={onSelect} />
        {selectedNodeId && shown.graph.nodes.some((n) => n.id === selectedNodeId) ? (
          <div className="panel" style={{ padding: 0 }}>
            <div style={{ padding: '8px 16px' }}><button className="link" onClick={() => onSelect(null)}>{T.scenario.backToSummary}</button></div>
            <NodePanel bundle={shown} nodeId={selectedNodeId} assessment={showScenario ? sc!.assessment[selectedNodeId] : undefined}
              reason={showScenario ? sc!.assessment_reason[selectedNodeId] : undefined} />
          </div>
        ) : (
          <aside className={`panel${showScenario ? '' : ' dim'}`}>
            {!sc && <p className="muted">{T.scenario.emptyHint}</p>}
            {sc && (
              <>
                <div className="diff-block">
                  <h3>{T.scenario.challengedTitle} <Badge look={ASSESSMENT.challenged} /></h3>
                  {challenged.length === 0 && <p className="small muted">{T.scenario.noneChallenged}</p>}
                  {challenged.map((id) => (
                    <div key={id} className="challenged-item">
                      <div>{name(id)}</div>
                      <div className="small muted">{sc.assessment_reason[id] ?? T.scenario.noReason}</div>
                    </div>
                  ))}
                </div>
                <div className="diff-block">
                  <h3>{T.scenario.nextChecks}</h3>
                  {(scenario!.proposals[0]?.scenario_ref?.next_checks ?? []).map((c) => <p key={c}>{c}</p>)}
                  {!scenario!.proposals[0]?.scenario_ref?.next_checks.length && <p className="small muted">{T.scenario.noNextChecks}</p>}
                </div>
                <div className="diff-block">
                  <h3>{T.b3.plans(sc.base_version, sc.version)}</h3>
                  {scenario!.proposals.length === 0 && <p className="small muted">{T.scenario.noProposal}</p>}
                  {scenario!.proposals.map((p) => (
                    <PlanRow key={p.terminal_id} title={nodeLabel(scenario!.graph.nodes.find((n) => n.id === p.terminal_id)!)}
                      a={planOf(baseB, p.terminal_id)} b={p} />
                  ))}
                  {scenario!.proposals.length > 0 && <button className="secondary" onClick={onReapproveHere}>{T.b3.reapproveHere}</button>}
                  <p className="small">
                    {T.scenario.trace(changedTargets(sc).map(name), (scenario!.diff?.changed_claim_ids ?? []).map(name))}
                  </p>
                </div>
              </>
            )}
          </aside>
        )}
      </div>
    </div>
  );
}
