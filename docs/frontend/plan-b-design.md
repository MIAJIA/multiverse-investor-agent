# 前端设计：方案 B-最小（分支 + 批准计划）

2026-10-18 · frontend 分支（已合 core-schema@da2d097）· 状态：**已审过（第 10 节是审后的决定，优先于正文），等后端实现 commit 后开工**

依据：`docs/changes/2026-10-18-branches-and-plans.md`（下称「改动说明」）第 3、5、9 节。本文只写前端；数据契约以方案 B 后端最终交付的 schema 为准，本文先按主 session 转来的契约设计，第 7 节列出需要后端补的地方。

原则不变：**模型提议，代码裁决；前端只展示、编辑、确认、比较。** 分支、分支类别、gate、失效判定都由后端给；前端只做按 id 查找和集合运算。

## 1. 范围

| 页面 | 做 | 不做（下一期） |
| --- | --- | --- |
| B1 | 三类分支截然不同的视觉（D-B9）；点结论高亮整条分支；共用主干按 `trunk` 显示 | 分叉点标记；前提勾选后变淡（D-B6） |
| B2 | 「签字」改成「批准计划」：结论列表 + 预填计划 + 理解确认 + 批准 / 撤销批准 + 可选备注（D-B3、D-B4、D-B7） | 组合批准；导出给执行层 |
| B3 | 维持现状；受影响的已批准计划标「前提已改动，请重新批准」；对手分支变了给一句提示；加一个「在这个版本上重新批准」入口（见 4.3） | 撤销栈、「设为当前版本」的完整流程 |
| #scenarios | 保留，标「实验」，从顶栏挪进 playground 的二级入口，跟上新 schema 能编译 | 进入主流程 |
| 顶栏（可选） | 联网开关 + 一行状态「联网：开，拿到 N 段」，取自 `web.message` | — |

## 2. 数据契约（前端这边的类型）

```ts
type BranchKind = 'evidenced' | 'model_only' | 'hypothetical';

interface Branch {
  terminal_id: string;
  divergence_node_ids: string[];
  own_node_ids: string[];
  own_edge_ids: string[];
  kind: BranchKind;
  trunk: 'evidenced' | 'model_only';
}

interface TradeProposal { /* 现有字段 */ terminal_id: string; }

interface VersionBundle {
  graph: Graph;
  proposals: TradeProposal[];   // 取代 proposal，不保留旧字段
  branches: Branch[];
  scenario: Scenario | null;
  diff: GraphDiff | null;
  excerpts: Excerpt[];
}

interface SignBody {            // 语义是「批准」，接口名不变
  version: string;
  terminal_id: string;          // 必填
  clarified_statement?: string; // 可选：用户在「我们把你的想法理解为……」里改过才发
  criteria?: string | null;
  deadline?: string | null;
  confirmed_claim_ids: string[];
  condition_overrides: Record<string, ConditionOverride>;
}
```

前端按 `terminal_id` 关联 `proposals` 和 `branches`，不依赖数组顺序（改动说明 4.1：避免「默认显示哪一份」由模型的输出顺序决定）。列表按画布上终点的左右顺序排（`toFlow` 的坐标），这是纯展示。

## 3. B1：三类分支的视觉规范

### 3.1 规范

| | 有资料支持 evidenced | 仅模型推断 model_only | 假设 hypothetical |
| --- | --- | --- | --- |
| 节点底色 | 现在的类型淡底色（事件蓝 / 假设绿 / 终点紫） | 白底 | 灰紫底 `#f1eef7` + 45° 斜线底纹（`repeating-linear-gradient(45deg, #e3ddef 0 2px, transparent 2px 8px)`） |
| 节点描边 | 1px 实线，类型色 | 1px 虚线 `#b9bfc8`（5 4） | 1.5px 点线 `#8e7cc3`（2 3） |
| 文字 | 正常 | 整体减淡：标题 `#6b7280`，不用 opacity（避免叠加后发灰） | 标题 `#4b3f72` |
| 边 | 实线 `#9aa1ab` 1.2px | 虚线 `#c4c9d0`（5 4） | 点线 `#8e7cc3`（2 3） |
| 标签 | 无（默认状态不加字） | 小字「仅推断」，灰 | 醒目胶囊「假设 · 未观测」：`#5b4a9e` 字、`#e6e0f5` 底，**每个节点和结论卡片都有**，放在标题前 |
| 圆环 | 照常（绿 / 红 / 灰格） | 照常；没有引用时是虚线空环 | 照常，但底色换成灰紫 |

- **颜色只给状态**的原则保留：分支类别靠底纹 + 线型 + 标签区分，所以灰度打印或色弱也能分辨。橙色仍只留给「关键依赖」和情景里的「受挑战」。
- 合成资料包导致的降级（改动说明 4.2 第 3 条）：在 model_only 的标签后加「· 资料为占位」。需要后端给出这个标记，见第 7 节第 3 条。

### 3.2 每个节点用哪一类

后端只给了「分支」级别的 kind，节点要落到某一类，规则如下（只查表，不推导证据）：

1. 节点是 shock，或是本版本 `scenario.ops` 的 target → **假设**；
2. 节点在某条分支的 `own_node_ids` 里 → 该分支的 `kind`；
3. 其余（共用主干）→ 包含它的分支的 `trunk`；几条分支的 trunk 不一致时取较弱的一档（model_only）。

第 3 条是前端在后端结果上做的取舍。**建议后端直接给 `node_kinds` / `edge_kinds` 两张表**（第 7 节第 1 条），前端就不需要这条规则。边的类别跟它的终点节点走。

### 3.3 高亮整条分支

点一个结论（terminal）：这条分支 = 它的 `own_node_ids` + 它的全部祖先（共用主干）。祖先用图结构上溯，是按边查找，不做判断。高亮时其余节点退到 32% 透明度（沿用 B3 的「其余退后」），右侧面板显示这个结论的计划摘要，并提供「去批准这份计划 →」，跳到 B2 并选中这一行。点空白处取消。

### 3.4 组件改动

- `node/DesignNode.tsx`：`DesignData` 加 `kind: BranchKind`、`highlighted?: boolean`；按 3.1 出样式。现在的 `look.color` / `look.shape` 分支保留给 playground。
- `components/GraphCanvas.tsx`：读 `bundle.branches`，按 3.2 给每个节点、每条边定 kind；`selectedTerminalId` 时按 3.3 高亮。
- `lookup.ts`：`keyClaimId(proposal)` 改成 `keyClaimIds(proposals)`（每份计划一个）；新增 `branchOf(bundle, terminalId)`、`ancestors(graph, id)`。
- `Workspace.tsx`：点 terminal 时右侧显示「计划摘要」而不是证据面板（证据面板仍可从摘要里展开）。
- `NodePanel.tsx`：「为什么先查这一步」改成列出把这个节点当关键依赖的那几份计划。

## 4. B2：「批准计划」

### 4.1 页面结构

```text
┌ 我们把你的想法理解为：「2027-06-30 前 CPO 出货……」   ✓ 对   改一下 ┐   ← 只出现一次，所有计划共用
├ 结论列表 ────────────────────────────────────────────────────────────┤
│ ▌ 光源营收超预期  LITE 看多     你需要相信：外置光源架构、光源需求上升   WAIT 先别动   ✓ 已批准 │
│ ▒ 硅光代工营收占比升  TSM 看多  你需要相信：硅光代工利用率升           WAIT 先别动          │
│ ┆ DSP 业务承压  MRVL 看空       你需要相信：DSP 需求放缓（仅推断）       WAIT 先别动          │
├ 选中这一行的计划 ─────────────────────────────────────────────────────┤
│ [假设分支才有] ▧ 这条分支建立在尚未发生的假设上：改用集成激光            │
│ 方向 · 进场条件（且）· 离场条件（ANY / ALL）· 关键依赖 · Critic 一行灰字 │
│ 阈值为 null 的条件：黄底 + 「需要你确认」+ 输入框                       │
│ 你需要相信的前提（可选勾选，不勾也能批准）                               │
│ 备注（可选，一行）                                                      │
│ [批准这份计划]      本版本已批准：光源营收超预期 · 撤销批准             │
└───────────────────────────────────────────────────────────────────────┘
```

- 行首的竖条是分支类别的缩略：▌实色（有资料）、┆ 虚线（仅推断）、▒ 斜线灰紫（假设），和画布同一套视觉。假设分支的行还带「假设 · 未观测」胶囊。
- 「你需要相信」= 这条分支的 `own_node_ids` 去掉 terminal 本身，用短标题列出，最多 3 个，多了写「等 N 个」；空的时候（分支只在终点分开）写「与其他结论共用全部前提」。
- 状态列只用 gate（先别动 / 受阻 / 待复核），不再单独显示 draft / needs_review，后者放进计划卡片的小字里。
- 原来的逐条假设表和三项必填表单（`SignDialog`）删掉。

### 4.2 交互流程

1. 进入 B2，默认选中：本版本已批准的那一份；没有就选列表第一行。不自动批准任何一份。
2. **理解确认**：任何一份计划的 `user_judgment.requires_user_confirmation` 为 true 时，顶部那一行必须点「✓ 对」才能批准；点「改一下」原地变成输入框，改完再 ✓，改过的文字随批准请求以 `clarified_statement` 发出。没改就不发这个字段（后端沿用计划里的值）。
3. **改阈值 / 日期**：只在选中的计划里改，记在这份计划的草稿里（`drafts[terminal_id].overrides`），和现在一样标「已修改，批准后由后端重算」。
4. **批准**：
   - 本版本没有已批准的计划 → 直接发 `sign`。
   - 本版本已有另一份已批准 → 先弹一句确认「批准这份会撤销对『光源营收超预期』的批准」，确认后再发。
   - 返回新版本号 → `getVersion` → 当前版本切到新版本，列表里这一行显示「✓ 已批准」，其余行没有。
5. **撤销批准**：已批准的那一行旁边有「撤销批准」。撤销后本版本没有任何已批准的计划，界面上写「本版本没有批准任何计划（= 不交易）」。**后端目前没有撤销接口**，见第 7 节第 2 条。
6. **不批准**：不需要专门的按钮；离开页面就是不批准。顶部一行小字常驻：「一份都不批准也是一个决定」。
7. 批准按钮旁边常驻小字「批准的是一份计划，不是下单」，没有执行按钮。

### 4.3 B3 的改动

- 情景页右侧「提案 v1 → v2」改成「计划」：只列**基线里已批准的那一份**和情景版本里同一个 terminal 的计划，并排显示 gate / 支持度 / 批准状态。
- **失效标记**：基线里已批准、情景里 `user_judgment.confirmed` 变成 false 的计划 → 橙色标「前提已改动，请重新批准」。判定用两个版本的后端字段对比（查表），不自己判断写范围；后端若补了显式字段就改用字段（第 7 节第 4 条）。
- **对手分支提示**：已批准的计划没有失效，但本次 `diff.changed_claim_ids` 和**其他分支**的 `own_node_ids` 有交集 → 灰字「对手分支变了，你的计划没有直接受影响，但值得再看一眼」。
- 「在这个版本上重新批准」：把情景版本设为 B2 的当前版本并跳到 B2。这是 B3 里唯一新增的动作，用来接上失效标记，否则用户看到「请重新批准」却无处可批。撤销栈不做。

### 4.4 state 改动（仍是一份 state）

```ts
type AppState = {
  runId: string | null;
  versions: Record<string, VersionBundle>;
  baseVersion: string | null;            // B1 / B2 看的版本，fork 的 base_version
  scenarioVersion: string | null;
  viewing: 'base' | 'scenario';
  tab: 'workspace' | 'signoff' | 'scenario';
  selectedNodeId: string | null;
  selectedTerminalId: string | null;      // 新：B1 高亮和 B2 选中行共用
  understood: { confirmed: boolean; text: string | null }; // 新：理解确认，按版本重置
  drafts: Record<string, {                 // 新：按 terminal_id 存未提交的输入，取代 signoff
    overrides: Record<string, ConditionOverride>;
    confirmedClaimIds: string[];
    note: string;
  }>;
  online: boolean;                         // 新（可选）：联网开关
  webMessage: string | null;               // 新（可选）：上一次建 run 返回的 web.message
  busy: boolean; errors: string[] | null; notices: string[] | null; runNote: string | null;
};
```

`selectedTerminalId` 在 B1 和 B2 之间共享：B1 点结论，切到 B2 时默认选中同一行。`drafts` 和 `understood` 在 `baseVersion` 变化时清空。

### 4.5 组件改动

| 文件 | 改动 |
| --- | --- |
| `types.ts` | 第 2 节的类型；`VersionBundle.proposal` → `proposals`；`Branch`、`BranchKind` |
| `api.ts` | `sign` 的请求体；mock 的 `sign`：按 terminal 把这一份设为 confirmed、其余 false（gate 不重算，照旧标 MOCK）；mock 的 `fork` 不变；可选：`createRun` 带 `online`，返回 `web` |
| `App.tsx` | 4.4 的 state；`signNow(terminalId)`；`revoke()`（等后端接口） |
| `components/Signoff.tsx` | 重写：理解确认行 + 结论列表 + 计划区 + 批准 / 撤销 |
| `components/SignDialog.tsx` | 删除，换成「批准会撤销另一份」的确认小框 `ApproveConfirm.tsx` |
| `components/ConclusionList.tsx` | 新：结论列表，一行一个 terminal |
| `components/ProposalCard.tsx` | 加分支类别横幅；null 阈值高亮「需要你确认」；去掉「研究判断」段（移到顶部理解确认行） |
| `components/BranchSwatch.tsx` | 新：行首的类别缩略 + 「假设 · 未观测」胶囊，B1 / B2 / B3 共用 |
| `components/Scenario.tsx` | 4.3 的计划对比、失效标记、对手提示、「在这个版本上重新批准」 |
| `components/GraphCanvas.tsx`、`node/DesignNode.tsx`、`node/node.css`、`lookup.ts`、`Workspace.tsx`、`NodePanel.tsx` | 第 3 节 |
| `scenarios/*` | 跟上 `proposals`（`scenario_ref` 从对应 terminal 的计划里取）；页头加「实验」标签；从 App 顶栏移除入口，只从 `#playground` 页头进入 |
| `status.ts` | 新增 `BRANCH_KIND` 映射（文案、颜色、线型、底纹），所有组件从这里取 |

## 4.6 顶栏联网开关（可选）

- 位置：Analyze 按钮右边，一个小开关「联网」，默认关。打开后 `createRun` 的请求体带 `online: true`。
- 状态行：开关下方一行小字，原样显示上一次 `POST /api/runs` 返回的 `web.message`（如「联网：开，拿到 6 段」或失败原因）；没有 `web` 字段时不显示。
- 联网拿到的片段和资料包片段一样进证据面板，前端不区分来源样式（来源名本身会写明）。MOCK 下开关可点，但状态行写「MOCK：不联网」。

## 5. fixture 怎么改

等后端交付 schema 的 commit 后再动，步骤：

1. `make_fixtures.py`：`DRAFT` 改成 3 份，每个 terminal 一份（LITE 看多、TSM 看多、MRVL 看空），各自的进场 / 离场条件取自这条分支上的条件，`terminal_id` 填上；调用后端的派生函数得到 `proposals`，调用 `catalyst/branches.py` 的函数得到 `branches`，**不在脚本里手算**。
2. 四份 fixture 都按新格式生成：
   - `c1`：基线 3 份计划；分叉到「改用集成激光」后，LITE 那条分支应变成 hypothetical；
   - `c1_blocked`：同上，`cond.c1.els_design_wins` 判 not_met，LITE 计划 BLOCKED；
   - `c1_multi`：加冲击的 c1-v3 让 TSM 那条分支变成 hypothetical，叠加的 c1-v4 两条都是；
   - `c4_abstain`：不变（没有图）。
3. 再加一份 `c1_approved`：在 c1 上用后端的 sign 入口批准 LITE 那份，然后分叉。这是演示「前提已改动，请重新批准」和「对手分支变了」的唯一办法，必须走后端，不在前端模拟。
4. `check_fixtures.py`：每个版本 `proposals` 的 terminal 集合 = 图上 terminal 集合；每份计划 `TradeProposal.model_validate` 并检查规范形式；`branches` 与后端函数复算一致；同一版本最多一份 `confirmed`。
5. **已知限制**：fixture 用的是合成资料包，按改动说明 4.2，所有分支都会降级成 model_only，fixture 里**看不到「有资料支持」的样式**。办法见第 7 节第 5 条；在那之前，evidenced 的样式只在 playground 里预览，并标明是演示。

## 6. 测试计划

### 自动化

| 测试 | 内容 |
| --- | --- |
| `branchStyle.test.ts`（新） | 3.2 的落类规则：shock / 改过的假设 → hypothetical；own 节点 → 分支 kind；共用主干 → trunk，不一致取 model_only；边跟终点走 |
| `lookup.test.ts` | `ancestors`、`branchOf`、`keyClaimIds`；「你需要相信」= own 去掉 terminal |
| `approval.test.ts`（新） | mock `sign`：批准一份后同版本只有它 confirmed；B3 失效判定（父 confirmed 且子 false）；对手提示（changed ∩ 其他分支 own） |
| `status.test.ts` | `BRANCH_KIND` 覆盖三类，文案里有「假设 · 未观测」 |
| `toFlow` / `strength` / `scenarios` | 跟上 `proposals` |
| `check_fixtures.py` | 第 5 节第 4 条 |
| typecheck、build | 照旧；`#scenarios` 必须能编译 |

### 手动演示（MOCK，接真实后端后重走）

| # | 操作 | 预期 |
| --- | --- | --- |
| P1 | c1，B1 | 3 个结论；fixture 里全是「仅推断」样式（合成资料包），标「资料为占位」 |
| P2 | B1 点 LITE 终点 | LITE 整条分支高亮（含共用主干），其余退后；右侧是 LITE 计划摘要和「去批准这份计划 →」 |
| P3 | 去 B2 | LITE 行已选中；顶部「我们把你的想法理解为……」；批准按钮在 ✓ 之前不可用 |
| P4 | ✓，填 CPO 出货阈值，批准 | LITE「✓ 已批准」；阈值那条标「已修改，批准后由后端重算」 |
| P5 | 选 TSM，批准 | 先弹「会撤销对 LITE 的批准」；确认后只有 TSM 已批准 |
| P6 | 撤销批准 | 「本版本没有批准任何计划（= 不交易）」（需后端接口；MOCK 下先模拟） |
| P7 | c1_approved，B3 分叉「改用集成激光」 | 画布上 LITE 分支变成灰紫斜线 + 「假设 · 未观测」；LITE 计划标「前提已改动，请重新批准」 |
| P8 | c1_approved 里批准的是 TSM 时再分叉同一处 | TSM 计划保留批准，出现「对手分支变了……值得再看一眼」 |
| P9 | 「在这个版本上重新批准」 | 跳到 B2，当前版本是情景版本，LITE 未批准 |
| P10 | #playground 页头进 #scenarios | 页头有「实验」，能正常显示 |

## 7. 需要后端确认或补的地方

1. **节点 / 边的类别表**：契约只有分支级别的 kind，共用主干上的节点要前端按 3.2 第 3 条取舍。建议版本包加 `node_kinds: {id: kind}`、`edge_kinds: {id: kind}`，由 `branches.py` 一起算；有了它，3.2 整节变成查表。
2. **撤销批准**：主 session 要求设计「撤销批准」，但现有接口只能批准。建议 `sign` 接受 `terminal_id: null`，表示本版本一份都不批准，产出新版本；或者新开 `POST /runs/{id}/revoke {version}`。前端两种都能接。
3. **「资料为占位」的标记**：分支降级的原因前端拿不到。建议 `Branch` 加 `synthetic: bool`（或 `note`）。
4. **失效的显式字段**：4.3 的失效标记现在靠「父版本 confirmed、子版本不是」推出来。建议 fork 在受影响的计划上写 `user_judgment.reset_by: <fork 版本号>`（或 `invalidated: true`），前端直接读，也能区分「本来就没批准」和「被分叉撤销」。
5. **能看到「有资料支持」的演示数据**：合成资料包会让所有分支降成 model_only。要演示 evidenced 样式，需要一份用真实资料包录制的 C1（改动说明第 9 节的重录计划里本来就有）。在那之前，B1 的 evidenced 样式只在 playground 预览。
6. **备注放哪**：「可选备注」没有对应字段。建议 `UserJudgment` 和 sign 请求体加 `note: str | None`；不建议塞进 `criteria`（语义不同）。
7. **理解确认是否每份计划一份**：现在每份 `TradeProposal` 都带 `user_judgment`，但「我们把你的想法理解为……」是对用户原话的改写，应该全图只有一句。前端按「取第一份计划的 `clarified_statement`」显示；如果几份不一样，就逐份显示在计划卡片里。建议后端保证同一版本的几份计划这一句相同，或把它提到版本级别。

## 8. 可选：给 Mia 挑的 playground

实现阶段可以先做两组 A/B，用真实 fixture 渲染，放进现有 `#playground`：

1. **假设分支的视觉**：A 斜线底纹 + 灰紫（本文默认） / B 整个分支套一个灰紫虚线外框（「泡泡」），节点本身不变色。
2. **B2 的布局**：A 列表在上、计划在下（本文默认） / B 左列表右计划，两栏。

各约 20 分钟。如果主 session 觉得没必要，直接按默认实现。

## 9. 步骤清单与估时

数据结构以后端 commit 为准，第 1 步要等它。

- [ ] **1. 合并后端 schema，改 `types.ts`、mock `api.ts`，重新生成 5 份 fixture，改 `check_fixtures.py`**（30 分钟）
- [ ] **2. 现有组件跟上 `proposals`，先保证 typecheck 和现有测试能过**（20 分钟）
- [ ] **3. B1：三类样式 + 高亮整条分支 + `BRANCH_KIND` 映射 + 单测**（35 分钟）
- [ ] **4. B2：理解确认、结论列表、计划区、批准 / 撤销、确认小框 + 单测**（50 分钟）
- [ ] **5. B3：计划对比、失效标记、对手提示、「在这个版本上重新批准」**（25 分钟）
- [ ] **6. #scenarios 标实验、入口挪走**（10 分钟）
- [ ] **7. 可选：联网开关和状态行**（15 分钟）
- [ ] **8. 可选：第 8 节的两组 playground**（40 分钟）
- [ ] **9. typecheck / test / build / check_fixtures，手动演示 P1–P10，截图，更新 `docs/frontend/`，commit**（30 分钟）

必做（1–6、9）约 **3 小时 20 分钟**；加上两项可选约 4 小时 15 分钟。第 2 步之后每一步都能单独验收。

## 10. 审后的决定（优先于上文）

| # | 决定 | 改了上文哪里 |
| --- | --- | --- |
| 1 | 后端在版本包里给 `node_kinds`、`edge_kinds` 两张表 | 3.2 整节改成查表，第 3 条的取舍规则删掉 |
| 2 | 撤销批准 = `sign` 发 `terminal_id: null`，产出新版本 | 4.2 第 5 步调这个 |
| 3 | 「资料为占位」读 `Branch.synthetic_evidence` | 3.1 |
| 4 | 失效用后端字段：`TradeProposal.approval_reset` → 「前提已改动，请重新批准」；`TradeProposal.rival_changed` → 「同一版本里另一份计划受了影响，值得再看一眼」。rival_changed 不判断是不是竞争关系，文案不写「对手」 | 4.3 的两条推断规则删掉，改读字段 |
| 5 | evidenced 样式的演示数据等真实资料包重录；在那之前只在 playground 预览并标明演示 | 第 5 节第 5 条 |
| 6 | 备注：`UserJudgment.note`，sign 请求体加可选 `note` | 4.2、`SignBody` |
| 7 | 后端保证同一版本几份计划的 `original_statement`、`clarified_statement` 相同，顶部只显示一句 | 4.1 |
| 8 | 第 8 节的两组 playground 不做，按默认实现 | 第 8 节、第 9 步 |
| 9 | 联网开关和状态行做 | 4.6、第 7 步 |

后端字段（d105c45 加上面几处）：`ProposalDraft` / `TradeProposal.terminal_id`（必填）；`TradeProposal.approval_reset`、`rival_changed`（默认 false）；`UserJudgment.note`；`Branch = {terminal_id, divergence_node_ids, own_node_ids, own_edge_ids, kind, trunk, synthetic_evidence}`；`VersionBundle = {graph, proposals, branches, node_kinds, edge_kinds, scenario, diff, excerpts}`；inspect / fork / sign 返回体里 `proposal` → `proposals`；`proposal_version = "{graph_version}.{terminal_id}"`。

估时随之变成：必做 1–7、9 约 3 小时 15 分钟（去掉 8，第 3、5 步因为查表各少 5 分钟，加上联网 15 分钟）。

### 开工前已做（不依赖后端数据）

- `types.ts` 加了方案 B 的类型（`Branch`、`BranchKind`、`PlanBBundle`、`ApproveBody`，`TradeProposal` / `UserJudgment` 的新字段）。`VersionBundle` 暂时不切，等第 1 步和 fixture 一起切，保证每个 commit 都能编译。
- `status.ts` 的 `BRANCH_KIND`（文案、颜色、线型、底纹）和 `components/BranchSwatch.tsx`（行首缩略 + 「假设 · 未观测」胶囊）。

### 视觉预览（/#plan-b，开工前先做）

- 用 `c1_multi` 的 c1-v3（加了「代工停产」冲击）做演示数据（`src/preview/demoPlanB.ts`）：LITE 分支手动指定为有资料支持，TSM 分支是假设（含冲击节点），MRVL 是仅推断 · 资料为占位；TSM、MRVL 两份计划是手写的。页头常驻「演示数据」说明。后端交付后删掉这份演示数据，换成真实 fixture。
- 预览里用到的都是正式实现要复用的：`GraphCanvas` 加了可选的 `branchView`（`node_kinds` / `edge_kinds` / 高亮）和 `labelOf`；`DesignNode` 加了 `kind` / `synthetic` / `dimmed`；`ConditionRow` / `ProposalCard` 加了「需要你确认」和 `planB`；新组件 `ApprovePlans`（B2 整页）；`lookup.ancestors`。
- 浏览器里走过：B1 点 LITE、TSM 高亮整条分支；B2 理解确认前不能批准；批准 TSM；改批 LITE 时弹「会撤销对硅光代工的批准」；撤销批准后显示「本版本没有批准任何计划（= 不交易）」；勾「演示：改了假设之后回到这里」后，已批准的那份显示「前提已改动，请重新批准」，其余显示「另一份计划受了影响，值得再看一眼」（真实数据里这两个由后端字段决定）。截图 `screenshots/pb-*`。

### 界面文字（主 session 决定）

- 界面文字全部集中在 `web/src/strings.ts`（`T`），组件里不写字符串；`status.ts` 只管颜色和线型，文案也从 `T` 取。现在是中文，提交前统一换英文，只改这一个文件。
- `src/__tests__/strings.test.ts` 扫描 `src` 下的源码（去掉注释后），出现中文就失败。例外：`strings.ts` 和演示数据（`playground/demoLabels.ts`、`preview/demoPlanB.ts`、`scenarios/demoNames.ts`）。
- 后端生成的内容（节点陈述、条件、理由）以后会是英文，界面中文、内容英文是预期的。MOCK fixture 的中文内容不动，等重录替换。`T.app.defaultEvent` 要和 fixture 的事件一致，换英文时一起换。

### B2 精简版（Mia：原版太满，参考灵动岛 / Robinhood / OpenEvidence）

预览页 B2 右上角可以切换 A / B / 原版，三者用同一套属性（`components/approve/model.ts`），批准逻辑完全一样。

- 共用件（`components/approve/Pieces.tsx`）：
  - 「你的想法」收成顶部一颗胶囊，点「对，就是这个意思」确认；「改一下」原地展开成输入框（灵动岛）。
  - 批准收成底部黑色胶囊：「批准「X」」/「改批这份 · 会撤销「Y」」/「✓ 已批准「X」 撤销」；点开原地展开出阈值提醒、可选备注和确认，取代原来的弹窗。没确认想法时胶囊变灰并提示。
  - 计划详情像 OpenEvidence 的答案卡：「你需要相信」是带引用数的小标签（上标数字，仅推断写「仅推断」），点开在下面列出编号的原文和来源；「盯这些信号」一行一条（状态圆点 · 进场 / 离场 · 规则 · 截止），缺阈值的那条有黄色「需要你确认 · 设一个阈值」，点了原地出输入框；完整计划卡和逐条勾选前提收进「更多细节」。
- A 列表展开（Robinhood）：一个大标题（「3 个结论，还没批准」/「已批准：X」）+ 一行一个结论（名字、标的 · 方向、一个状态），点一行原地展开；假设分支整行带斜线底纹。
- B 答案卡（OpenEvidence）：顶部一排胶囊切换结论，下面只有一张卡：大字「看多 TSM」、一句衬线体的论点、前提和信号。
- 截图：`screenshots/pb-b2-lite-*`。原版（`ApprovePlans`）先保留做对比，定了之后删掉没选中的。
