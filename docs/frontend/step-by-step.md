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
