// 多情景 playground 的只读辅助：版本链、演示名、两种着色。不做判断：累计结果是后端给的，「这一层新增」只做集合差。
import { changedTargets } from '../lookup';
import type { AssessmentStatus, VersionBundle } from '../types';
import { DEMO_NAMES } from './demoNames';
import { T } from '../strings';

export type Versions = Record<string, VersionBundle>;

/** 从根到 v 的版本链（沿 scenario.base_version 往上找）。 */
export function chain(versions: Versions, v: string): string[] {
  const out: string[] = [];
  for (let cur: string | undefined = v; cur && versions[cur]; cur = versions[cur].scenario?.base_version) {
    out.unshift(cur);
    if (!versions[cur].scenario) break;
  }
  return out;
}

export function rootOf(versions: Versions): string {
  return Object.keys(versions).find((v) => !versions[v].scenario)!;
}

export function scenarioIds(versions: Versions): string[] {
  return Object.keys(versions).filter((v) => versions[v].scenario);
}

export function childrenOf(versions: Versions, v: string): string[] {
  return scenarioIds(versions).filter((c) => versions[c].scenario!.base_version === v);
}

// 演示名：后端的 Scenario 还没有 name 字段。正式版应由用户起名，默认取用户原话。

export function scenarioName(versions: Versions, v: string): string {
  if (!versions[v]?.scenario) return T.scenarioName.baseline;
  const op = versions[v].scenario!.ops.at(-1); // 叠加时 ops 继承父情景，最后一个是这一层的
  return DEMO_NAMES[v] ?? String(op?.value ?? v).slice(0, 10);
}

/** 完整名：叠加的情景带上父情景的名字，如「改用集成激光 › + 停产」。 */
export function fullName(versions: Versions, v: string): string {
  return chain(versions, v).slice(1).map((x) => scenarioName(versions, x)).join(T.scenarioName.sep) || T.scenarioName.baseline;
}

export function challenged(b: VersionBundle | undefined): string[] {
  return Object.entries(b?.scenario?.assessment ?? {}).filter(([, s]) => s === 'challenged').map(([id]) => id);
}

export interface Coloring {
  assessment: Record<string, AssessmentStatus>;
  changed: string[];
}

function coloringOf(b: VersionBundle, lit: string[], changed: string[]): Coloring {
  const set = new Set(lit);
  const assessment: Record<string, AssessmentStatus> = {};
  for (const n of b.graph.nodes) assessment[n.id] = set.has(n.id) ? 'challenged' : 'unaffected';
  return { assessment, changed };
}

/** 这一层新增的受挑战节点：本版本 assessment 的 challenged 减去父版本的（只做集合差，不判断因果）。 */
export function newChallenged(versions: Versions, v: string): string[] {
  const parent = versions[v].scenario?.base_version;
  const prev = new Set(parent ? challenged(versions[parent]) : []);
  return challenged(versions[v]).filter((id) => !prev.has(id));
}

/** 这一层的操作：叠加时 ops 继承父情景，所以去掉父版本已有的那几个。 */
function layerOps(versions: Versions, v: string) {
  const ops = versions[v].scenario?.ops ?? [];
  const parent = versions[v].scenario?.base_version;
  return ops.slice(versions[parent ?? '']?.scenario?.ops.length ?? 0);
}

/** 相对上一层：只亮这一层新增的受挑战节点和这一层改动的假设。 */
export function layerColoring(versions: Versions, v: string): Coloring {
  const changed = changedTargets({ ...versions[v].scenario!, ops: layerOps(versions, v) });
  return coloringOf(versions[v], newChallenged(versions, v), changed);
}

/** 相对基线（累计）：直接用后端给的 scenario_ref.challenged_claim_ids（叠加后的全部结果）。 */
export function cumulativeChallenged(b: VersionBundle): string[] {
  return b.proposal?.scenario_ref?.challenged_claim_ids ?? challenged(b);
}

export function cumulativeColoring(versions: Versions, v: string): Coloring {
  const b = versions[v];
  return coloringOf(b, cumulativeChallenged(b), changedTargets(b.scenario));
}
