// 后端接口。真实模式走 /api（Vite 代理到 CATALYST_API，默认 http://localhost:8000）；
// MOCK 模式读离线生成的 fixtures/*.json（页头选择）。默认 MOCK，`VITE_MOCK=0 npm run dev` 切到真实后端。
import type { ApproveBody, Fixture, Op, RunCreated, VersionBundle, WriteResult } from './types';
import { T } from './strings';

export const MOCK = import.meta.env.VITE_MOCK !== '0';

async function call<T>(method: 'GET' | 'POST', path: string, body?: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const errors = data?.errors ?? (data?.detail ? [JSON.stringify(data.detail)] : [`HTTP ${res.status}`]);
    return { ok: false, errors, version: null, run_id: null } as T;
  }
  return data as T;
}

// ---- MOCK -------------------------------------------------------------

// fixtures/*.json 都是 make_fixtures.py 生成的；MOCK 下由页头的选择器决定用哪一份。
const FIXTURES = import.meta.glob<{ default: unknown }>('../fixtures/*.json');
const nameOf = (path: string) => path.split('/').pop()!.replace('.json', '');
export const MOCK_FIXTURES = Object.keys(FIXTURES).map(nameOf).sort();

let mockName = MOCK_FIXTURES.includes('c1') ? 'c1' : MOCK_FIXTURES[0];
let fixtureP: Promise<Fixture> | null = null;
const loadFixture = () =>
  (fixtureP ??= FIXTURES[Object.keys(FIXTURES).find((p) => nameOf(p) === mockName)!]()
    .then((m) => structuredClone(m.default) as Fixture));

/** MOCK 专用：选一份 fixture，返回它的名字和事件原话（给页头填输入框）。 */
export async function mockFixtureInfo(name: string): Promise<{ label: string; event: string }> {
  const fx = (await FIXTURES[Object.keys(FIXTURES).find((p) => nameOf(p) === name)!]()).default as Fixture;
  return { label: fx.label, event: fx.event };
}
export function setMockFixture(name: string) {
  mockName = name;
  fixtureP = null;
}

const mock = {
  async createRun(online: boolean): Promise<RunCreated> {
    fixtureP = null; // 每次 Analyze 都从干净的 fixture 开始（MOCK 批准可能改内存里的那份）
    const fx = await loadFixture();
    const web = { online, message: online ? T.mock.web : null };
    if (fx.run) return { ...fx.run, run_id: 'mock', web };
    const root = Object.values(fx.versions).find((b) => b.graph.parent_version === null)!;
    return { ok: true, errors: [], version: root.graph.version, run_id: 'mock', discover: null, web };
  },
  async getVersion(version: string): Promise<VersionBundle> {
    const b = (await loadFixture()).versions[version];
    if (!b) throw new Error(T.mock.noVersion(version));
    return structuredClone(b); // 和网络返回一样：每次一份新对象
  },
  async fork(base: string, op: Op): Promise<WriteResult> {
    // 找 fixture 里录好的、从这个版本出发、这一层操作相同的分叉版本（叠加时 ops 继承父情景，看最后一个）
    const fx = await loadFixture();
    const all = Object.values(fx.versions);
    const hit = all.find((b) => b.graph.parent_version === base && b.scenario
      && b.scenario.ops.at(-1)?.kind === op.kind && b.scenario.ops.at(-1)?.target === op.target);
    if (hit) return { ok: true, errors: [], version: hit.graph.version };
    const recorded = all.filter((b) => b.graph.parent_version === base && b.scenario)
      .map((b) => b.scenario!.ops.at(-1)?.target).filter((x): x is string => !!x);
    return { ok: false, errors: [recorded.length ? T.mock.onlyRecorded(recorded, op.kind) : T.mock.noRecordedFork(base)], version: null };
  },
  async sign(body: ApproveBody): Promise<WriteResult> {
    const fx = await loadFixture();
    // 优先用 fixture 里由后端 ep.sign 录好的批准版本（approval / 重新派生都是真的）
    const recorded = Object.values(fx.versions).find((b) => b.graph.parent_version === body.version
      && b.graph.op.kind === 'sign' && b.graph.op.target === body.terminal_id);
    if (recorded) {
      const edited = !!(body.note || body.clarified_statement || Object.keys(body.condition_overrides).length);
      return { ok: true, errors: edited ? [T.mock.recordedApproval] : [], version: recorded.graph.version };
    }
    // 没录到：只在内存里改这个版本的计划（同一版本最多一份已批准），gate 不重算，返回同一个版本号
    const b = fx.versions[body.version];
    if (!b?.proposals.length) return { ok: false, errors: [T.mock.noProposal(body.version)], version: null };
    for (const p of b.proposals) {
      const on = p.terminal_id === body.terminal_id;
      Object.assign(p.user_judgment, on ? {
        confirmed: true, confirmed_claim_ids: body.confirmed_claim_ids, note: body.note ?? p.user_judgment.note,
        clarified_statement: body.clarified_statement ?? p.user_judgment.clarified_statement,
      } : { confirmed: false });
      p.approval_reset = false;
      if (on) for (const c of [...p.entry_conditions, ...p.exit_conditions]) Object.assign(c, body.condition_overrides[c.id] ?? {});
    }
    return { ok: true, errors: [T.mock.gateNotRecomputed], version: body.version };
  },
};

// ---- 导出 -------------------------------------------------------------

export function createRun(body: { event: string; target?: string; packs?: string[]; online?: boolean }): Promise<RunCreated> {
  return MOCK ? mock.createRun(!!body.online) : call('POST', '/runs', body);
}

export async function getVersion(runId: string, version: string): Promise<VersionBundle> {
  if (MOCK) return mock.getVersion(version);
  const b = await call<VersionBundle & Partial<WriteResult>>('GET', `/runs/${runId}/versions/${version}`);
  if (b.ok === false) throw new Error(b.errors?.join('; '));
  return b;
}

export function fork(runId: string, body: { base_version: string; op: Op }): Promise<WriteResult> {
  return MOCK ? mock.fork(body.base_version, body.op) : call('POST', `/runs/${runId}/fork`, body);
}

/** 批准一份计划；terminal_id 为 null = 本版本一份都不批准（撤销批准）。接口名保留 sign。 */
export function sign(runId: string, body: ApproveBody): Promise<WriteResult> {
  return MOCK ? mock.sign(body) : call('POST', `/runs/${runId}/sign`, body);
}
