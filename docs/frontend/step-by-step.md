# 前端 MVP 执行步骤

总预算约 55 分钟。每步做完勾上；**第 5 步是兜底判断点**：全项目第 140 分钟时第 5 步还没勾，就改做 Streamlit（见 implementation-plan.md「兜底」）。

- [x] **1. 脚手架（4 分钟）**
  `web/` 下手写 `package.json`、`vite.config.ts`（/api 代理）、`tsconfig.json`（strict）、`index.html`、（MOCK 默认开，写在 `api.ts`：仓库根 `.gitignore` 忽略 `.env`）；`npm install react react-dom @xyflow/react` 和 `-D vite @vitejs/plugin-react typescript @types/react @types/react-dom vitest`。`.gitignore` 加 `web/node_modules`、`web/dist`。
  完成标准：`npm run dev` 出空白页。

- [x] **2. 类型与 fixture（8 分钟）**
  `src/types.ts` 照 `catalyst/schema.py` 抄（含枚举取值数组）；`scripts/make_fixtures.py`（derive_proposal + fork + DemoReasoner）生成 `fixtures/c1.json`；`scripts/check_fixtures.py`。
  完成标准：两个脚本都跑通，check 退出码 0；重跑 make 后 `git diff` 为空。

- [x] **3. status / toFlow / lookup + 单测（6 分钟）**
  `status.ts`、`toFlow.ts`（最长路径深度 → y，层内序号 → x）、`lookup.ts`；三个测试文件。
  完成标准：`npm test` 全绿。

- [x] **4. api.ts 与 App state（4 分钟）**
  四个函数 + MOCK 分支；App 里唯一的 `useState`、三个 tab 的空壳、Header 的 Analyze 调 `createRun` → `getVersion`。
  完成标准：点 Analyze 后 `versions['c1-v1']` 有值（先用 `<pre>` 打印版本号）。

- [x] **5. B1 画布与面板（12 分钟）——兜底判断点**
  `ClaimNode`、`GraphCanvas`、`NodePanel`、`Workspace`；`styles.css` 的颜色变量。
  完成标准：手动脚本第 1–6 步通过。

- [x] **6. B2 签字（9 分钟）**
  `Signoff`（假设表 + Confirm + 条件阈值 / 截止输入）、`ProposalCard`、`SignDialog`；签字调 `sign` → `getVersion`。
  完成标准：手动脚本第 7–12 步通过。

- [x] **7. B3 情景对比（8 分钟）**
  `Scenario`：ForkForm → `fork` → `getVersion`；基线 / 情景切换；`toFlow` 传 assessment；右侧三块。
  完成标准：手动脚本第 13–17 步通过。

- [x] **8. 收尾（4 分钟）**
  `npm run typecheck && npm test && npm run build`；`check_fixtures.py`；从头走一遍 B1 → B2 → B3；commit 到 frontend 分支（不 push）。
  完成标准：test-plan.md 的自动化全部通过，演示一条完整流程。

超时砍掉顺序：Discover 候选列表 → 边标签 → B2 截止日期编辑 → B3 提案对比只留三行。

## 执行记录（2026-10-18）

- 实现开始 20:48，B1 画布在 20:55 出来（兜底判断点：开始后 30 分钟），没有切 Streamlit。
- 自动化：`npm run typecheck` 通过；`npm test` 3 个文件 23 条全过；`npm run build` 通过（fixture 是单独的动态 chunk，真实模式不加载）；`check_fixtures.py` OK（1 个 fixture、13 个枚举）；重跑 `make_fixtures.py` 输出不变。
- 手动演示（MOCK，内置浏览器 1440×900）：第 1–17 步全部走通，截图在 `screenshots/`（b1-workspace、b2-signoff、b3-scenario）。
  - 例外：第 10 步的「改截止日期」在内置浏览器里没法往 date 输入框里打字，没有验证到；改阈值验证过。
- 演示中修的一处：签字后假设表的勾选回到 Not started。现在签过之后以提案的 `confirmed_claim_ids` 为准。
- `types.ts` 的 OpKind 先加了 `sign`（主 session 已定，schema 还没合），`check_fixtures.py` 的 PENDING 里登记了，schema 加上后删掉。

## 复查记录（换成新节点样式之后）

- 第 1–17 步在新样式下重走一遍，全部通过；第 10 步的改截止日期这次也验证了（逐键输入），签字后提案里截止日期是 2027-02-28。
- 新增第 18 步（BLOCKED）和第 19 步（弃权），通过。截图：`screenshots/b2-blocked.jpg`、`screenshots/c4-abstain.jpg`。
- MOCK 下每次 Analyze 都会重新载入干净的 fixture，签字改过的数据不会带到下一次。
- 短标题：`types.ts` 的 Claim 加了可选的 `label`。节点卡片有 label 就显示 label，没有就把 statement 截到 10 个字加「…」（`src/node/labels.ts` 的 `nodeLabel`）。现在的 fixture 没有 label，所以应用里显示的是截短的句子；`screenshots/b1-workspace.jpg`、`b3-scenario.jpg` 里的短标题来自 playground 的演示表，等后端加上 label、重新生成 fixture 后再更新截图。playground 仍用演示表（`src/playground/demoLabels.ts`），有 label 时优先用 label。

## 跟上 core-schema@eb92f73（label / neutral / critic）

- `git merge core-schema` 是快进（core-schema 已经包含 frontend 的全部提交）。
- `types.ts`：`Claim.label: string | null`；`Stance` 加 `neutral`；`TradeProposal.critic`（`CRITIC_STATUSES` = disabled / ok / failed）。`check_fixtures.py` 去掉了 OpKind 的 PENDING（schema 已有 `sign`），并核对 critic 的取值。
- 证据面板多一组「背景」（neutral）；圆环上 neutral 是灰格，不算正方也不算反方；卡片小字写「背景 n」。C1 数据里没有 neutral 证据，所以用单元测试（复制一份图、把一条引用改成 neutral）验证。
- 提案卡加一行「Critic 挑刺：未启用（下一期）」；failed 时显示原因，ok 时列出 items。
- 重新生成 3 份 fixture，全部通过 `check_fixtures.py`（14 个枚举）。golden C1 图的 label 全是 null，所以节点卡片仍是截短的 statement。

## 多情景 playground（/#scenarios）

- 数据：`make_fixtures.py` 新增 `c1_multi.json`，全部走真实 `ep.fork`：c1-v2 = 改假设（集成激光），c1-v3 = 预定义冲击（代工停产），c1-v4 = 在 c1-v2 上叠加同一个冲击。`DemoReasoner` 改成只看「操作：」那一行判断操作类型（叠加时基线图自己的 op 会误导 ScriptedReasoner）。
- 五个设计问题，各两种做法：情景列表（分段胶囊 / 版本树）、比较（叠色 / 并排）、叠加着色（相对上一层 / 相对基线）、情景摘要（大数字卡片 / 表盘点阵）、新建情景（灵动岛 / 侧边表单）。截图 `screenshots/sc1–sc5`。
- 情景名是演示表；「相对基线」由前端把每层后端结果合起来演示，正式版需要后端给。
- 发现的后端问题：叠加分叉（c1-v4）的提案 `support_status` 回到 supported——`derive_proposal` 只看这一层的 challenged，父情景 c1-v2 让激光路径受挑战这件事没有带下来。
- 跟上叠加情景的修复（core-schema@bb173e1，fast-forward）：后端的 assessment 和 `scenario_ref.challenged_claim_ids` 现在都是叠加后的全部结果，Scenario 多了 `root_version`，ops 也继承父情景。前端改成：「相对基线」直接用 `scenario_ref.challenged_claim_ids`；「这一层新增」= 本版本 challenged 减去父版本 challenged（集合差），并用测试确认这些节点都在后端 diff 的 `changed_claim_ids` 里；「这一层改动的假设」只看这一层新加的 op。多情景 playground 的大部分视图默认显示相对基线，第 3 组 A 显示这一层新增，树上的数字也是这一层新增。
