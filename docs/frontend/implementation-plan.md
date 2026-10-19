# 前端 MVP 实现计划（B1 / B2 / B3）

2026-10-18 · frontend 分支（基于 core-schema@129dd12）

本文以 review 后的修正为准，优先于 `docs/frontend-design.md` 原文。原则不变：**模型提议，代码裁决；前端只展示、编辑、确认、比较，不自己算。** gate、status、support_status、版本号、条件判定、写范围、assessment、diff 全部来自后端返回值。

## 范围

| 标签 | 做 | 不做 |
| --- | --- | --- |
| B1 Research Workspace | 一行事件输入 + Analyze；React Flow 只读画布（按深度排坐标）；点节点 → 右侧面板：详情、证据（入边的 evidence，按 excerpt_id 找片段原文）、条件 | 自动布局、折叠组、小地图、边悬停、拖拽栏、What-if 工具条、候选卡选择 |
| B2 Sign-off | 逐条假设表（Confirm 勾选）；提案卡（status 和 gate 分开显示，entry 标「且」，exit 标 exit_logic）；进场 / 退出条件的阈值和截止可改；Sign → 三项表单（可检验的判断、判定条件、期限） | 执行按钮、导出、历史 |
| B3 Scenario Diff | 选一个节点 + 输入新的假设值 → fork；基线 / 情景切换；画布按 assessment 三态着色；右侧三块：受挑战的前提及理由、下一步查什么、提案 v1 → v2 | 多情景、情景命名、AddShock UI、自由文本 what-if |

三个标签是同一个页面里的三个 tab，共用一份 state。

## 技术栈

Vite 8 + React 19 + TypeScript + `@xyflow/react` 12 + `useState`；测试用 Vitest。不用 Next.js 模板、shadcn、Zustand、ELK。样式是一个手写的 `styles.css`（CSS 变量 + 几个类），不引 Tailwind。

本机已验证：Node v26.10.0、npm 11.19.1；在临时目录装过 `react@19.3.1 react-dom @xyflow/react@12.12.0 vite@8.3.4 @vitejs/plugin-react@6.1.2 typescript@7.0.2 vitest@5.0.5 @types/react@19.3.0`，无报错，`tsc --version` 正常。typescript 7 是原生编译器；如果某个工具跟它不兼容，退回 `typescript@~5.9`。

## 文件清单与职责

```text
web/
  package.json            脚本：dev / build（tsc --noEmit && vite build）/ test（vitest run）/ typecheck
  vite.config.ts          React 插件；/api 代理到 CATALYST_API（默认 http://localhost:8000）
  tsconfig.json
  index.html
  fixtures/c1.json        生成的 fixture，不手写（见下文）
  scripts/
    make_fixtures.py      离线跑 catalyst 入口，生成 fixtures/c1.json
    check_fixtures.py     用 schema 校验 fixture（parse_graph / TradeProposal / Scenario / diff 复算）
  src/
    main.tsx              挂载 <App/>
    App.tsx               唯一的 state（useState），三个 tab，所有后端调用都从这里发
    types.ts              schema.py 的 TS 镜像（字段名一字不改）+ VersionBundle
    api.ts                createRun / getVersion / fork / sign；MOCK 开关在这里
    toFlow.ts             纯函数：(graph, opts) → { nodes, edges }，坐标按深度算
    status.ts             所有枚举 → 文案与颜色的唯一映射表
    lookup.ts             只读查找：节点的入边证据、节点上的条件、key_dependency 指向的 claim
    components/
      ClaimNode.tsx       通用节点卡（role 决定颜色，evidence_status 小字，assessment 描边，key dependency 外发光）
      GraphCanvas.tsx     ReactFlow 包装：nodesDraggable=false，点击回调
      NodePanel.tsx       详情 / 证据 / 条件三段（不是三个子 tab，竖排）
      ProposalCard.tsx    B2、B3 共用
      Workspace.tsx       B1
      Signoff.tsx         B2：假设表 + 条件编辑 + 提案卡
      SignDialog.tsx      B2：三项表单
      Scenario.tsx        B3：fork 表单 + 切换 + 画布 + 右侧三块
    styles.css
    __tests__/
      toFlow.test.ts
      status.test.ts
      lookup.test.ts
```

## 组件树

```text
<App>                                  state 全在这里
  <Header>                             事件输入 + Analyze；MOCK 徽章；当前 run / 版本（小字）
  <Tabs>                               Workspace | Sign-off | Scenario
  ├─ <Workspace bundle selected onSelect>
  │    <GraphCanvas flow onNodeClick/> ← toFlow(bundle.graph, {keyClaimId})
  │    <NodePanel bundle nodeId/>        详情 · 证据（Supporting n / Contradicting n）· 条件
  ├─ <Signoff bundle signoff onChange onSign>
  │    <AssumptionTable/>                一行一个 claim：陈述、失效条件（rule + deadline）、evidence_status、Confirm
  │    <ProposalCard proposal editable overrides onEdit/>
  │    <SignDialog open defaults onSubmit/>
  └─ <Scenario base scenarioBundle viewing onFork onToggle>
       <ForkForm nodes onSubmit/>         下拉选节点 + 一行新值 → POST fork
       <VersionToggle/>                   基线 {base_version} / 情景 {version} + 「假设，未观测」
       <GraphCanvas flow/>                ← toFlow(graph, {assessment, changedTarget})
       <DiffSidebar>
         受挑战的前提                      scenario.assessment == challenged 的 claim + assessment_reason
         下一步查什么                      proposal.scenario_ref.next_checks
         提案 v1 → v2                      两份 ProposalCard 字段并排 + diff.changed_claim_ids + scenario.ops
```

## State 结构（A1：只有一份）

```ts
type VersionBundle = {                // = GET /api/runs/{id}/versions/{v} 的返回值
  graph: Graph;
  proposal: TradeProposal | null;
  scenario?: Scenario | null;         // 只有分叉出来的版本有
  diff?: GraphDiff | null;            // 相对 scenario.base_version，后端算
  excerpts: Excerpt[];                // 该版本推理时进入上下文的片段（store 的 observations/<v>.json）
};

type AppState = {
  runId: string | null;
  versions: Record<string, VersionBundle>;  // 唯一的数据缓存：按版本号存后端原样返回的 bundle
  baseVersion: string | null;               // B1 / B2 看的版本，也是 fork 的 base_version
  scenarioVersion: string | null;           // 最近一次 fork 产出的版本
  viewing: 'base' | 'scenario';             // B3 的切换
  tab: 'workspace' | 'signoff' | 'scenario';
  selectedNodeId: string | null;
  signoff: {                                // 只是还没提交的用户输入，签字时整包发给后端
    confirmedClaimIds: string[];
    conditionOverrides: Record<string, { threshold?: number | null; deadline?: string }>;
  };
  busy: boolean;
  errors: string[] | null;                  // 后端 / 校验器的拒绝理由，原样显示
};
```

- 节点、边、条件、证据没有第二份：每次渲染从 `versions[v]` 用 `toFlow` / `lookup` 现算。
- 画布节点不可拖（`nodesDraggable={false}`），所以不需要 `useNodesState`，也不存位置。
- `signoff` 只保存用户还没提交的输入；改了阈值后，提案卡上显示「已修改，签字后由后端重算」，gate 仍显示后端给的值，前端不预判。

## API 与 MOCK 切换

`src/api.ts` 导出四个函数，签名两种模式一样：

```ts
createRun(body: { event: string; target?: string; packs?: string[] }): Promise<RunCreated>
getVersion(runId: string, version: string): Promise<VersionBundle>
fork(runId: string, body: { base_version: string; op: Op }): Promise<WriteResult>
sign(runId: string, body: SignBody): Promise<WriteResult>

type WriteResult = { ok: boolean; errors: string[]; version: string | null };
```

- 开关：`const MOCK = import.meta.env.VITE_MOCK !== '0'`。默认开（仓库根 `.gitignore` 忽略 `.env`，所以不放 `.env` 文件）；后端起来后 `VITE_MOCK=0 npm run dev`。页面右上角显示「MOCK · fixture c1」徽章，避免把 fixture 当真实输出演示。
- 真实模式：`fetch('/api/...')`，Vite dev server 代理到后端。非 2xx 时把响应体里的 `errors`（或 `detail`）原样抛给 UI。
- 每个写操作之后，App 都用返回的 `version` 调一次 `getVersion`，存进 `versions`，再整体重画——这就是设计文档的「操作 → 新版本号 → 重画」。
- MOCK 模式：`await import('../fixtures/c1.json')`（动态导入，真实模式不打包）。
  - `createRun` → `{ run_id: 'mock', version: <parent_version 为 null 的那个版本>, discover: null }`；
  - `getVersion` → `fixture.versions[v]`；
  - `fork` → op 的 kind 和 target 与 fixture 里情景版本的 `scenario.ops[0]` 一致时返回那个版本号；否则返回 `ok:false`，errors = 「MOCK：fixture 只录了 <target> 的 change_assumption」。value 文本不比较。
  - `sign` → 不重算 gate（那是后端的事）：把用户输入写进该版本 proposal 的 `user_judgment`（`confirmed: true`）后返回同一个版本号，并在 errors 之外加一条提示「MOCK：gate 未重算」。这是 MOCK 里唯一改数据的地方，代码里注释清楚。

### 后端接口形状与修改建议

| 接口 | 原形状 | 建议 |
| --- | --- | --- |
| `POST /api/runs {event, target?, packs?}` | `{run_id, discover?, inspect}` | 加 `version`（inspect 产出的图版本）。没有 target 时后端照 `cmd_run` 选第一个 grounded 候选进 inspect；`discover` 原样返回，UI 只读列出候选（时间不够就不显示）。`inspect.ok=false` 或 `no_chain=true` 时 UI 显示 errors / `no_chain_reason`。 |
| `GET /api/runs/{id}/versions/{v}` | `{graph, proposal, scenario?, diff?}` | **加 `excerpts`**（store 的 `observations/<v>.json`）。没有片段原文，B1 的证据面板只能显示 excerpt_id。`diff` 定义为相对 `scenario.base_version`。 |
| `POST /api/runs/{id}/fork {base_version, op}` | fork 入口返回值 | 保留入口返回值，但顶层加 `version`（= `graph.version`，失败时 null）。后端调用 `ep.fork` 时要传 `proposal=`（该版本已签的提案优先），否则 v2 没有提案、没有 `scenario_ref`，B3 第二、三块是空的；`pack` 用基线版本的 observations。 |
| `POST /api/runs/{id}/sign {...}` | 签好的提案 | 返回 `WriteResult`（`{ok, errors, version}`），前端再 GET。两处需要后端决定，见下一节第 4、5 条。 |

## Fixture 生成

`web/scripts/make_fixtures.py`，在仓库根目录运行：

```bash
~/Downloads/multiverse-investor-agent/.venv/bin/python web/scripts/make_fixtures.py
```

（worktree 里没有 `.venv`，借用主仓库的；脚本第一行把 worktree 根目录插到 `sys.path[0]`，保证 import 的是本分支的 `catalyst/`。）

步骤：

1. 读 golden 图 `eval/fixtures/c1_graph_v1.json` 和资料包 `c1_evidence_pack.json`，`EvidenceProvider.register(pack)`。
2. **基线提案**：`ep.derive_proposal(ProposalDraft, parse_graph(golden), model="scripted")`。ProposalDraft 是脚本里写的一小段（标的 LITE long、进场 `cond.c1.cpo_shipments` + `cond.c1.els_design_wins`、退出 `cond.c1.dsp_guidance`、exit_logic ANY、key_dependency → `c1.assume.external_laser`、user_judgment 改写一句）。gate / status / support_status / meta 仍由代码派生。
   - 为什么不走 `ep.inspect`：已在临时目录试过，golden 图过不了 inspect 的 `_root_issues`（`c1.event`、`c1.assume.capex`、`c1.assume.external_laser` 没有入边却标 supported），见下一节第 1 条。
   - 这段 draft 是 fixture 里唯一手写的「模型输出」，文件的 `_source.notes` 里写明；有真实录制后整体替换。
3. **分叉**：`ep.fork(golden, c3_change_assumption.op, reasoner=DemoReasoner(), pack=pack, proposal=<基线提案>, config=Config(today="2026-10-18", run_prefix="c1"))`。`DemoReasoner` 继承 `eval.fakes.ScriptedReasoner`，只把 assessment 的 `reason: "scripted"` 换成人能读的演示句子（字典写在脚本里），其余全部沿用父类。已试跑：ok，产出 `c1-v2`，`changed_claim_ids = [external_laser, laser_demand, term.laser_vendor]`，challenged = `[c1.laser_demand, c1.term.laser_vendor]`，v2 提案 gate=WAIT、support_status=challenged。
4. 写 `web/fixtures/c1.json`，格式与 `python -m catalyst promote` 一致，每个版本再多两个字段：

```json
{
  "_source": {"script": "web/scripts/make_fixtures.py", "case": "C1+C3a", "notes": ["…"]},
  "versions": {
    "c1-v1": {"graph": {...}, "proposal": {...}, "scenario": null, "diff": null, "excerpts": [...]},
    "c1-v2": {"graph": {...}, "proposal": {...}, "scenario": {...}, "diff": {...}, "excerpts": [...]}
  },
  "latest": "c1-v2"
}
```

`versions[v]` 的形状就是 `GET /versions/{v}` 的返回值，所以 MOCK 的 `getVersion` 不做任何转换。建议主 session 让 `promote` 也写出 `diff`（相对 parent）和 `excerpts`（observations），之后录制的 fixture 直接替换这个文件，前端不用改。

## 与 schema 的字段映射

| UI 上显示的东西 | 来自（schema.py 字段） | 备注 |
| --- | --- | --- |
| 节点颜色 | `Claim.role`：event 蓝 / assumption、intermediate 绿 / terminal 紫 / shock 橙 | intermediate 与 assumption 同色，卡片角标区分 |
| 节点主文案 / 原话 | `Claim.statement` / `Claim.original_statement` | 两者不同时，详情里显示「原话」 |
| 节点小字 | `Claim.evidence_status` + 入边 evidence 条数 | |
| 标的 | `Claim.instruments`（terminal） | |
| 关键依赖高亮 | `proposal.key_dependency.claim_id`，或 `key_dependency.condition_id` → 该条件的 `claim_id` | 提案上的引用，不是节点字段；画布只做查找。`why` 显示在详情里 |
| 边实线 / 虚线 | `Mechanism.model_only` | TS 里字段名是 `from`（schema 的 alias） |
| 边标签 | `Mechanism.channel` + `sign` | 机制一句话只在详情里显示 |
| 节点证据 | 指向该节点的边（`edge.to == id`）的 `evidence[]`，按 `stance` 分 Supporting / Contradicting；`excerpt_id` → `bundle.excerpts[].text / source / date` | `rebuttal` 显示在反方卡下面；入边全是 model_only 时显示「仅模型推断」；没有入边时显示「证据只挂在边上，这个节点没有入边」 |
| 条件行 | `Condition.rule`（大字）；`series ?? source`、`anchor`、`deadline`、`threshold`（null → 「你来定」+ `threshold_note`）、`comparator` | |
| 条件两个徽章 | `verification_status`（可核实 / 未核实）、`evaluation_status`（已满足 / 未满足 / 未知） | 不合并 |
| 提案状态 | `TradeProposal.status`（draft / needs_review）与 `gate`（WAIT 先别动 / BLOCKED 受阻 / READY_FOR_REVIEW 待复核）**两个徽章分开** | 没有 Ready to execute |
| 提案支持度 | `support_status` | |
| 进场 / 退出 | `entry_conditions`（标「且」）、`exit_conditions` + `exit_logic`（ANY「或」/ ALL「且」，显式显示） | |
| 方向 | `direction.instrument / side / horizon_days / note` | |
| 签字表单默认值 | `user_judgment.clarified_statement`、`criteria`、`deadline`；`requires_user_confirmation` 为 true 时并排显示 `original_statement` | 提交字段：`clarified_statement / criteria / deadline / confirmed_claim_ids / condition_overrides` |
| 已签 | `user_judgment.confirmed`、`confirmed_claim_ids` | |
| 三态着色 | `Scenario.assessment[claim_id]`：challenged 橙框 / unaffected 灰底对勾 / unresolved 灰底虚线 | 和 evidence_status 两层，卡片上都显示 |
| 改动的假设 | `Scenario.ops[0].target` | 只是标注，见下一节第 3 条 |
| 受挑战理由 | `Scenario.assessment_reason[claim_id]` | |
| 下一步查什么 | `proposal.scenario_ref.next_checks[]` | |
| 变化追溯 | `diff.changed_claim_ids`、`nodes_changed / edges_changed / conditions_changed` | 后端给，前端不比较 |
| 版本号 | `Graph.version`、`parent_version`、`Scenario.base_version` | 只在小字里出现；B3 的切换按 `scenario.base_version` 取基线，不写死 v1 / v2 |

## 发现的与 schema 不一致或存疑的地方

1. **golden C1 图过不了 inspect 自己的检查。** `c1.event`、`c1.assume.capex`、`c1.assume.external_laser` 没有入边却是 `supported`，`entrypoints._root_issues` 会拒。fixture 脚本因此绕过 inspect、直接 `derive_proposal`。UI 上也会出现「supported 但证据面板为空」。需要决定：改 golden（根节点改 unknown），还是规则对 event / assumption 放宽。
2. **ScriptedReasoner 没有 inspect stage**，所以没有现成的基线提案；脚本手写 ProposalDraft（见上文），由代码派生其余字段。
3. **被改的假设本身是 `unaffected`。** 它在写范围里，但 ScriptedReasoner 只把两个下游标成 challenged，于是 `c1.assume.external_laser` 在 B3 会被涂成灰色「未变」，读起来不对。前端会用 `scenario.ops[0].target` 额外标一个「改动的假设」角标（只是显示）。要不要在代码里给 target 一个固定的 assessment（现有三态里没有合适的），请主 session 定。
4. **sign 与不可变快照冲突。** `RunStore._put` 不允许覆盖 `proposals/<v>.json`，所以签字不能原地改提案。建议签字结果写到单独的位置（如 `signoffs/<v>.json`），GET bundle 返回签过的那份提案。
5. **condition_overrides 会在 fork 时丢失。** `derive_proposal` 从新图的 `conditions` 按 id 取条件，用户在签字时改的阈值 / 截止如果只存在提案里，v2 提案就回到原值。两个办法：(a) overrides 非空时，后端先产出一个新图版本（OpKind 需要加 `confirm_condition`，不调模型，重新判定条件、重新派生提案），再在这个版本上签字，sign 返回新版本号；(b) fork 时后端把 overrides 再套一遍。建议 (a)，它就是设计文档里的 confirm_condition；前端两种都能接，因为 fork 的 base_version 永远用 sign 返回的版本号。另外：改 deadline 时 `observation_window.end` 必须 ≤ deadline（validator 第 61 行），后端要一起改；数值条件填 threshold 时必须有 comparator。
6. **OpKind 没有 confirm_condition / sign**，oplog 里签字记成什么还没定。
7. **`scenario_ref.next_checks` 是 `list[str]`。** 设计文档想要的是一条事件型 Condition（大字时限 + 观测到 / 未观测到两个分支）；MVP 只显示字符串。
8. **没有提案层面的 diff。** B3「提案 v1 → v2」只能把两份提案的 gate / status / support_status / scenario_ref 并排显示，加上图 diff 的 `changed_claim_ids` 和 `scenario.ops`；前端不判断「哪里变了」。如需高亮，建议后端在 fork 返回值里加 `proposal_changes`。
9. **promote 不输出 `diff` 和 `excerpts`**（见上文 fixture 一节），录制的 fixture 现在不能直接替换。
10. `UserJudgment.probability` 存在，但签字表单按 review 只有三项，不收集。
11. B2 的「Needs review」用户状态：前端不推导，只有 Not started / Confirmed；`evidence_status` 和条件的 `verification_status` 并排显示，判断留给用户。

## 兜底

判断点：**全项目第 140 分钟**，看 `step-by-step.md` 的第 5 步（B1 画布显示 fixture 的 10 个节点、9 条边）有没有勾上。没勾上就停掉 React，改做 `web/streamlit_app.py`：读同一个 `fixtures/c1.json`，Graphviz 画图（情景版本按 assessment 着色），下面是条件列表、提案卡（status / gate 分开）、一个 fork 下拉框（只支持 fixture 里那一个情景）。预计 20 分钟。主 session 掌握项目时钟，到点请提醒。

## 砍掉顺序（超时时）

1. B1 顶部的 Discover 候选只读列表
2. 边标签（channel + sign）
3. B2 截止日期编辑（只留阈值）
4. B3 提案对比只留 gate / status / support_status 三行
