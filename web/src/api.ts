// 后端接口。真实模式走 /api（Vite 代理到 CATALYST_API，默认 http://localhost:8000）；
// MOCK 模式读离线生成的 fixtures/c1.json。默认 MOCK，`VITE_MOCK=0 npm run dev` 切到真实后端。
import type { Fixture, Op, RunCreated, SignBody, VersionBundle, WriteResult } from './types';

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
  async createRun(): Promise<RunCreated> {
    fixtureP = null; // 每次 Analyze 都从干净的 fixture 开始（MOCK 签字会改内存里的那份）
    const fx = await loadFixture();
    if (fx.run) return { ...fx.run, run_id: 'mock' };
    const root = Object.values(fx.versions).find((b) => b.graph.parent_version === null)!;
    return { ok: true, errors: [], version: root.graph.version, run_id: 'mock', discover: null };
  },
  async getVersion(version: string): Promise<VersionBundle> {
    const b = (await loadFixture()).versions[version];
    if (!b) throw new Error(`MOCK：fixture 里没有版本 ${version}`);
    return structuredClone(b); // 和网络返回一样：每次一份新对象
  },
  async fork(op: Op): Promise<WriteResult> {
    const fx = await loadFixture();
    const hit = Object.values(fx.versions).find(
      (b) => b.scenario?.ops[0]?.kind === op.kind && b.scenario?.ops[0]?.target === op.target,
    );
    if (!hit) {
      const recorded = Object.values(fx.versions).flatMap((b) => b.scenario?.ops.map((o) => o.target) ?? []);
      return { ok: false, errors: [`MOCK：fixture 只录了 ${recorded.join('、')} 的 ${op.kind}`], version: null };
    }
    return { ok: true, errors: [], version: hit.graph.version };
  },
  async sign(body: SignBody): Promise<WriteResult> {
    // 只在 MOCK 里改数据：真实后端会产出新版本（op.kind = "sign"），套用 overrides 并重算条件和 gate。
    // 这里只把用户输入写进提案，gate 不重算，返回同一个版本号。
    const p = (await loadFixture()).versions[body.version]?.proposal;
    if (!p) return { ok: false, errors: [`MOCK：版本 ${body.version} 没有提案`], version: null };
    Object.assign(p.user_judgment, {
      clarified_statement: body.clarified_statement, criteria: body.criteria, deadline: body.deadline,
      confirmed: true, confirmed_claim_ids: body.confirmed_claim_ids,
    });
    for (const c of [...p.entry_conditions, ...p.exit_conditions]) Object.assign(c, body.condition_overrides[c.id] ?? {});
    return { ok: true, errors: ['MOCK：gate 未重算（真实后端会产出新版本并重新判定条件）'], version: body.version };
  },
};

// ---- 导出 -------------------------------------------------------------

export function createRun(body: { event: string; target?: string; packs?: string[] }): Promise<RunCreated> {
  return MOCK ? mock.createRun() : call('POST', '/runs', body);
}

export async function getVersion(runId: string, version: string): Promise<VersionBundle> {
  if (MOCK) return mock.getVersion(version);
  const b = await call<VersionBundle & Partial<WriteResult>>('GET', `/runs/${runId}/versions/${version}`);
  if (b.ok === false) throw new Error(b.errors?.join('; '));
  return b;
}

export function fork(runId: string, body: { base_version: string; op: Op }): Promise<WriteResult> {
  return MOCK ? mock.fork(body.op) : call('POST', `/runs/${runId}/fork`, body);
}

export function sign(runId: string, body: SignBody): Promise<WriteResult> {
  return MOCK ? mock.sign(body) : call('POST', `/runs/${runId}/sign`, body);
}
