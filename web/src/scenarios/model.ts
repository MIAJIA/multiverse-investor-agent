// 多情景 playground 的只读辅助：版本链、演示名、按层合并的着色。不做判断，只组合后端已给的 assessment。
import { changedTargets } from '../lookup';
import type { AssessmentStatus, VersionBundle } from '../types';

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
const DEMO_NAMES: Record<string, string> = { 'c1-v2': '改用集成激光', 'c1-v3': '代工厂停产一季', 'c1-v4': '+ 停产' };

export function scenarioName(versions: Versions, v: string): string {
  if (!versions[v]?.scenario) return '基线';
  const op = versions[v].scenario!.ops[0];
  return DEMO_NAMES[v] ?? String(op?.value ?? v).slice(0, 10);
}

/** 完整名：叠加的情景带上父情景的名字，如「改用集成激光 › + 停产」。 */
export function fullName(versions: Versions, v: string): string {
  return chain(versions, v).slice(1).map((x) => scenarioName(versions, x)).join(' › ') || '基线';
}

export function challenged(b: VersionBundle | undefined): string[] {
  return Object.entries(b?.scenario?.assessment ?? {}).filter(([, s]) => s === 'challenged').map(([id]) => id);
}

export interface Coloring {
  assessment: Record<string, AssessmentStatus>;
  changed: string[];
}

/** 相对上一层：后端给的 assessment 原样。 */
export function relativeColoring(b: VersionBundle): Coloring {
  return { assessment: b.scenario?.assessment ?? {}, changed: changedTargets(b.scenario) };
}

/** 相对基线（累计）：把链上每一层后端给的 challenged 合起来。正式版应由后端给出，这里只为演示这种读法。 */
export function cumulativeColoring(versions: Versions, v: string): Coloring {
  const layers = chain(versions, v).slice(1).map((x) => versions[x]);
  const lit = new Set(layers.flatMap(challenged));
  const assessment: Record<string, AssessmentStatus> = {};
  for (const n of versions[v].graph.nodes) assessment[n.id] = lit.has(n.id) ? 'challenged' : 'unaffected';
  return { assessment, changed: [...new Set(layers.flatMap((b) => changedTargets(b.scenario)))] };
}
