// B3 Scenario Diff：改一个假设 → fork；基线 / 情景切换；画布按 assessment 三态着色；右侧三块。
// assessment、diff、提案 v2 全部来自后端；「提案 v1 → v2」只把两份提案并排显示，不在前端比较。
import { useMemo, useState } from 'react';
import { changedTargets, keyClaimId } from '../lookup';
import { ASSESSMENT, GATE, PROPOSAL_STATUS, ROLE, SUPPORT } from '../status';
import type { TradeProposal, VersionBundle } from '../types';
import Badge from './Badge';
import GraphCanvas from './GraphCanvas';
import NodePanel from './NodePanel';

function ForkForm({ bundle, busy, onFork }: { bundle: VersionBundle; busy: boolean; onFork: (t: string, v: string) => void }) {
  const nodes = [...bundle.graph.nodes].sort((a, b) => Number(b.role === 'assumption') - Number(a.role === 'assumption'));
  const [target, setTarget] = useState(nodes[0]?.id ?? '');
  const [value, setValue] = useState('');
  return (
    <div className="fork-form">
      <span className="small">假如</span>
      <select value={target} onChange={(e) => { setTarget(e.target.value); setValue(''); }}>
        {nodes.map((n) => <option key={n.id} value={n.id}>{ROLE[n.role].label}：{n.statement}</option>)}
      </select>
      <span className="small">改成</span>
      <input value={value} placeholder="新的假设值，例如：主流 CPO 方案改用集成激光，不再需要外置光源"
        onChange={(e) => setValue(e.target.value)} />
      <button className="primary" disabled={busy || !target || !value.trim()} onClick={() => onFork(target, value.trim())}>Fork</button>
    </div>
  );
}

function ProposalCompare({ a, b, av, bv }: { a: TradeProposal; b: TradeProposal; av: string; bv: string }) {
  const row = (label: string, x: React.ReactNode, y: React.ReactNode) => (
    <tr><th>{label}</th><td>{x}</td><td>{y}</td></tr>
  );
  const conds = (p: TradeProposal) => p.entry_conditions.map((c) => <div key={c.id} className="small">{c.rule}</div>);
  return (
    <table className="compare">
      <thead><tr><th /><th>{av}</th><th>{bv}</th></tr></thead>
      <tbody>
        {row('gate', <Badge look={GATE[a.gate]} />, <Badge look={GATE[b.gate]} />)}
        {row('status', <Badge look={PROPOSAL_STATUS[a.status]} />, <Badge look={PROPOSAL_STATUS[b.status]} />)}
        {row('支持度', <Badge look={SUPPORT[a.support_status]} />, <Badge look={SUPPORT[b.support_status]} />)}
        {row('标的', `${a.direction.side} ${a.direction.instrument}`, `${b.direction.side} ${b.direction.instrument}`)}
        {row('进场条件', conds(a), conds(b))}
      </tbody>
    </table>
  );
}

export default function Scenario({ versions, base, scenario, viewing, busy, selectedNodeId, onSelect, onToggle, onFork }: {
  versions: Record<string, VersionBundle>; base: VersionBundle; scenario: VersionBundle | null;
  viewing: 'base' | 'scenario'; busy: boolean; selectedNodeId: string | null;
  onSelect: (id: string | null) => void; onToggle: (v: 'base' | 'scenario') => void; onFork: (t: string, v: string) => void;
}) {
  // 对比的基线是情景自己声明的 base_version，不一定是当前 B1 / B2 的版本
  const baseB = (scenario?.scenario && versions[scenario.scenario.base_version]) || base;
  const showScenario = viewing === 'scenario' && scenario?.scenario;
  const shown = showScenario ? scenario! : baseB;
  const sc = scenario?.scenario ?? null;
  const opts = useMemo(() => (showScenario
    ? { assessment: sc!.assessment, changedTargets: changedTargets(sc), keyClaimId: keyClaimId(scenario!.proposal, scenario!.graph) }
    : { keyClaimId: keyClaimId(baseB.proposal, baseB.graph) }), [showScenario, sc, scenario, baseB]);
  const name = (id: string) => shown.graph.nodes.find((n) => n.id === id)?.statement ?? id;
  const challenged = sc ? Object.entries(sc.assessment).filter(([, s]) => s === 'challenged').map(([id]) => id) : [];

  return (
    <div className="col">
      <ForkForm bundle={base} busy={busy} onFork={onFork} />
      {sc && (
        <div className="fork-form">
          <div className="toggle">
            <button className={!showScenario ? 'on' : ''} onClick={() => onToggle('base')}>基线 {sc.base_version}</button>
            <button className={showScenario ? 'on' : ''} onClick={() => onToggle('scenario')}>情景 {sc.version}</button>
          </div>
          <span className="small">{sc.ops.map((o) => `假如「${String(o.value)}」`).join('；')}</span>
          <span className="badge" style={{ color: ROLE.shock.color, borderColor: ROLE.shock.color }}>假设，未观测</span>
        </div>
      )}
      <div className="split">
        <GraphCanvas bundle={shown} opts={opts} selectedNodeId={selectedNodeId} onSelect={onSelect} />
        {selectedNodeId && shown.graph.nodes.some((n) => n.id === selectedNodeId) ? (
          <div className="panel" style={{ padding: 0 }}>
            <div style={{ padding: '8px 16px' }}><button className="link" onClick={() => onSelect(null)}>← 返回情景摘要</button></div>
            <NodePanel bundle={shown} nodeId={selectedNodeId} assessment={showScenario ? sc!.assessment[selectedNodeId] : undefined}
              reason={showScenario ? sc!.assessment_reason[selectedNodeId] : undefined} />
          </div>
        ) : (
          <aside className={`panel${showScenario ? '' : ' dim'}`}>
            {!sc && <p className="muted">选一个节点、写下新的假设值，点 Fork。</p>}
            {sc && (
              <>
                <div className="diff-block">
                  <h3>受挑战的前提 <Badge look={ASSESSMENT.challenged} /></h3>
                  {challenged.length === 0 && <p className="small muted">没有前提受挑战。</p>}
                  {challenged.map((id) => (
                    <div key={id} className="challenged-item">
                      <div>{name(id)}</div>
                      <div className="small muted">{sc.assessment_reason[id] ?? '（没有理由）'}</div>
                    </div>
                  ))}
                </div>
                <div className="diff-block">
                  <h3>下一步查什么</h3>
                  {(scenario!.proposal?.scenario_ref?.next_checks ?? []).map((c) => <p key={c}>{c}</p>)}
                  {!scenario!.proposal?.scenario_ref?.next_checks.length && <p className="small muted">后端没有给出下一步。</p>}
                </div>
                <div className="diff-block">
                  <h3>提案 {sc.base_version} → {sc.version}</h3>
                  {baseB.proposal && scenario!.proposal
                    ? <ProposalCompare a={baseB.proposal} b={scenario!.proposal} av={sc.base_version} bv={sc.version} />
                    : <p className="small muted">缺少提案。</p>}
                  <p className="small">
                    追溯：改动 {changedTargets(sc).map(name).join('、')}；
                    受影响的 claim（后端 diff）：{(scenario!.diff?.changed_claim_ids ?? []).map(name).join('；')}
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
