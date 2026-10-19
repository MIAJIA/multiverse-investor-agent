# 前端 MVP 执行步骤

总预算约 55 分钟。每步做完勾上；**第 5 步是兜底判断点**：全项目第 140 分钟时第 5 步还没勾，就改做 Streamlit（见 implementation-plan.md「兜底」）。

- [ ] **1. 脚手架（4 分钟）**
  `web/` 下手写 `package.json`、`vite.config.ts`（/api 代理）、`tsconfig.json`（strict）、`index.html`、`.env`（`VITE_MOCK=1`）；`npm install react react-dom @xyflow/react` 和 `-D vite @vitejs/plugin-react typescript @types/react @types/react-dom vitest`。`.gitignore` 加 `web/node_modules`、`web/dist`。
  完成标准：`npm run dev` 出空白页。

- [ ] **2. 类型与 fixture（8 分钟）**
  `src/types.ts` 照 `catalyst/schema.py` 抄（含枚举取值数组）；`scripts/make_fixtures.py`（derive_proposal + fork + DemoReasoner）生成 `fixtures/c1.json`；`scripts/check_fixtures.py`。
  完成标准：两个脚本都跑通，check 退出码 0；重跑 make 后 `git diff` 为空。

- [ ] **3. status / toFlow / lookup + 单测（6 分钟）**
  `status.ts`、`toFlow.ts`（最长路径深度 → y，层内序号 → x）、`lookup.ts`；三个测试文件。
  完成标准：`npm test` 全绿。

- [ ] **4. api.ts 与 App state（4 分钟）**
  四个函数 + MOCK 分支；App 里唯一的 `useState`、三个 tab 的空壳、Header 的 Analyze 调 `createRun` → `getVersion`。
  完成标准：点 Analyze 后 `versions['c1-v1']` 有值（先用 `<pre>` 打印版本号）。

- [ ] **5. B1 画布与面板（12 分钟）——兜底判断点**
  `ClaimNode`、`GraphCanvas`、`NodePanel`、`Workspace`；`styles.css` 的颜色变量。
  完成标准：手动脚本第 1–6 步通过。

- [ ] **6. B2 签字（9 分钟）**
  `Signoff`（假设表 + Confirm + 条件阈值 / 截止输入）、`ProposalCard`、`SignDialog`；签字调 `sign` → `getVersion`。
  完成标准：手动脚本第 7–12 步通过。

- [ ] **7. B3 情景对比（8 分钟）**
  `Scenario`：ForkForm → `fork` → `getVersion`；基线 / 情景切换；`toFlow` 传 assessment；右侧三块。
  完成标准：手动脚本第 13–17 步通过。

- [ ] **8. 收尾（4 分钟）**
  `npm run typecheck && npm test && npm run build`；`check_fixtures.py`；从头走一遍 B1 → B2 → B3；commit 到 frontend 分支（不 push）。
  完成标准：test-plan.md 的自动化全部通过，演示一条完整流程。

超时砍掉顺序：Discover 候选列表 → 边标签 → B2 截止日期编辑 → B3 提案对比只留三行。
