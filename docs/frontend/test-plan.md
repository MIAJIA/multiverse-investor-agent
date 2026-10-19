# 前端 MVP 测试计划

2026-10-18 · frontend 分支

## 自动化

全部在 `web/` 下运行（Python 部分在仓库根目录）：

```bash
npm run typecheck && npm test && npm run build
~/Downloads/multiverse-investor-agent/.venv/bin/python web/scripts/check_fixtures.py
```

### 1. `toFlow` 纯函数（`src/__tests__/toFlow.test.ts`）

输入用 `fixtures/c1.json` 的真实版本，不另造图。

| 用例 | 期望 |
| --- | --- |
| c1-v1 的节点数 / 边数 | 10 / 9，id 与 graph 一一对应 |
| 深度坐标 | `c1.event`、`c1.assume.capex`、`c1.assume.external_laser` 深度 0；`c1.cpo_ramp` 1；`c1.laser_demand`、`c1.siph_foundry`、`c1.pluggable_dsp` 2（laser_demand 取最长路径，不是 1）；三个 terminal 3。同一深度的 y 相同、x 不重叠 |
| 边的 `from` alias | React Flow 边的 `source` = schema 里的 `from` |
| model_only | `c1.e6`、`c1.e9` 的 data.modelOnly = true（虚线），其余 false |
| key dependency | 传入 v1 提案时，只有 `c1.assume.external_laser` 的 data.isKey = true；`key_dependency.condition_id` 形式也能解析到条件的 claim_id（手造一个只含 condition_id 的提案） |
| assessment | 传入 c1-v2 的 scenario 时，`c1.laser_demand`、`c1.term.laser_vendor` 为 challenged，其余 unaffected；不传时 data.assessment 为 undefined |
| 改动的假设 | 传入 v2 时 `c1.assume.external_laser` 的 data.isChangedTarget = true |
| 不变性 | 调用前后 `JSON.stringify(graph)` 相同（不改输入） |
| 带环 / 悬空边 | 手造一条指向不存在节点的边：不崩，忽略该边并计入返回值的 `warnings` |

### 2. status 映射（`src/__tests__/status.test.ts`）

- 每个枚举（Role、EvidenceStatus、AssessmentStatus、Gate、ProposalStatus、SupportStatus、VerificationStatus、EvaluationStatus、ExitLogic）的每个取值都有文案和颜色：用 `types.ts` 里的取值数组逐个断言，漏一个就失败。枚举取值数组和 schema.py 的 Literal 对照一次（见第 3 节的脚本）。
- `gate` 的文案集合里没有 "execute" / "执行" 字样。
- `status` 与 `gate` 映射到两个不同的徽章组件 key（防止被合并成一个）。
- `exit_logic` ANY → 「或」，ALL → 「且」。

### 3. fixture 符合 schema（`web/scripts/check_fixtures.py`）

对 `fixtures/c1.json` 的每个版本：

- `parse_graph(graph)` 成功，且 `validator.blocking(validate_graph(g))` 为空；
- `TradeProposal.model_validate(proposal)` 成功，`proposal.graph_version == graph.version`；
- 有 `scenario` 时 `Scenario.model_validate` 成功，`scenario.version == graph.version`，`base_version` 在 `versions` 里；
- 有 `diff` 时用 `catalyst.diff.diff(base, graph)` 复算，结果与文件一致（防止 fixture 被手改）；
- `excerpts` 每条 `Excerpt.model_validate` 成功，图里所有被引用的 excerpt_id 都能在该版本的 excerpts 里找到；
- 规范形式：每个对象 `X.model_validate(d).dump() == d`（字段齐全，含默认值）；
- 额外打印 `types.ts` 需要的枚举取值（从 schema 的 Literal 读），与 `src/types.ts` 里的数组比对，不一致则退出码非 0。

再跑一次 `make_fixtures.py`，`git diff --exit-code web/fixtures/c1.json` 应为空（生成是确定的）。

### 4. TypeScript 与 build

- `npm run typecheck`（`tsc --noEmit`，strict）无错误；
- `npm run build` 成功；产物里不应包含 fixture，除非 `VITE_MOCK=1`（检查 `dist/assets` 里有没有 `c1.json` 的 chunk 名即可，不强制）。

### 不做的自动化

组件渲染测试、端到端浏览器测试：55 分钟预算里不做，由下面的手动脚本覆盖。

## 手动演示脚本（B1 → B2 → B3）

准备：`cd web && npm run dev`，打开 http://localhost:5173 。右上角应有「MOCK · fixture c1」徽章（真实后端时没有）。

### B1 Research Workspace

| # | 操作 | 预期看到 |
| --- | --- | --- |
| 1 | 输入框里是「光子芯片采用快于预期」，点 Analyze | 画布出现 10 个节点、9 条边，四行从上到下：事件 + 两个假设 / CPO 出货 / 三个中间节点 / 三个终点（LITE、TSM、MRVL）。顶部小字 `c1-v1` |
| 2 | 看画布 | 事件蓝、假设与中间节点绿、终点紫；`c1.e6`、`c1.e9` 是虚线（仅模型推断）；「主流 CPO 方案采用外置 CW 激光光源」有外发光和 Check first |
| 3 | 点「外置 CW 激光光源需求随 CPO 端口数上升」 | 右侧面板：详情（陈述、evidence_status = supported、入边两条的机制）；证据 Supporting 2（sc-003、sc-004，带来源、日期、原文）/ Contradicting 1（sc-005，下方显示 rebuttal）；条件一条 `cond.c1.els_design_wins`：可核实、未知 两个徽章分开 |
| 4 | 点「CPO 交换机……提前到 2027 年下半年」 | 条件 `cond.c1.cpo_shipments` 阈值显示「你来定」和 threshold_note；未核实、未知 |
| 5 | 点「可插拔 DSP 供应商相关业务增速承压」 | 证据区显示「仅模型推断」，没有空卡 |
| 6 | 点「光子芯片……采用快于预期」（事件） | 证据区显示「这个节点没有入边」；evidence_status 仍是后端给的 supported（已知问题 1） |

### B2 Sign-off

| # | 操作 | 预期看到 |
| --- | --- | --- |
| 7 | 切到 Sign-off | 假设表若干行，每行：陈述、失效条件（rule + 截止）、证据状态、Confirm；顶部「0 / n confirmed」 |
| 8 | 勾两行 Confirm | 计数变成 2 / n；证据状态列不变 |
| 9 | 看提案卡 | LITE long；进场两条用「且」连；退出一条，标「ANY · 或」；两个分开的徽章：status = draft、gate = WAIT（先别动）；support_status；关键依赖指向外置光源假设并带 why。没有任何执行按钮 |
| 10 | 在 `cond.c1.cpo_shipments` 填阈值（如 100000），改一个截止日期 | 条件旁出现「已修改，签字后由后端重算」；gate 仍是 WAIT |
| 11 | 点 Sign | 弹出三项：可检验的判断（预填 clarified_statement，旁边显示原话）、判定条件（预填 criteria，可空）、期限（预填 deadline）；按钮下小字「签的是研究判断，不是下单」 |
| 12 | 提交 | 提案卡显示「已签」，confirmed_claim_ids = 第 8 步勾的两条；MOCK 下另有一行「MOCK：gate 未重算」 |

### B3 Scenario Diff

| # | 操作 | 预期看到 |
| --- | --- | --- |
| 13 | 切到 Scenario，下拉选「主流 CPO 方案采用外置 CW 激光光源」，新值填「主流 CPO 方案改用集成激光，不再需要外置光源」，点 Fork | 情景版本 `c1-v2` 出现，切换器显示「基线 c1-v1 / 情景 c1-v2」和「假设，未观测」 |
| 14 | 看情景画布 | 「外置 CW 激光光源需求」和「激光器供应商……营收超预期」橙框橙点（challenged）；其余 8 个灰底对勾；被改的假设带「改动的假设」角标；节点上 evidence_status 仍显示 |
| 15 | 看右侧三块 | ① 受挑战的前提：两条 + 各自的理由；② 下一步查什么：「主要厂商 2027 年量产 CPO 是否确实采用集成激光（正式披露）……」；③ 提案 v1 → v2：gate WAIT → WAIT，status draft → draft，support_status supported → challenged，追溯到 `c1.assume.external_laser`（changed_claim_ids 三条） |
| 16 | 切回「基线」 | 画布恢复无着色的 v1；右侧三块隐藏或灰掉 |
| 17 | 选另一个节点（如资本开支假设）再 Fork | MOCK 下显示后端风格的拒绝：「MOCK：fixture 只录了 c1.assume.external_laser 的 change_assumption」，原情景不受影响 |

### 真实后端（后端落地后补跑）

`VITE_MOCK=0 npm run dev`，重走 1–17。差异只应出现在：没有 MOCK 徽章；第 12 步 gate 由后端重算（阈值改了、观测为空时仍应是 WAIT）；第 17 步走真实 fork。

### 补充案例（MOCK 页头的数据选择器）

| # | 操作 | 预期看到 |
| --- | --- | --- |
| 18 | 选「C1 到期复查（BLOCKED）」，Analyze，切到 Sign-off | 提案卡 gate = 红色「BLOCKED · 受阻」，status 仍是 draft；`cond.c1.els_design_wins` 是红色「未满足」，`cond.c1.cpo_shipments` 仍是「未知」 |
| 19 | 选「C4 弃权（没有因果链）」，Analyze | 没有画布，显示「没有找到有依据的因果链」和后端给的理由；三个标签都不可点 |

数据来源：`make_fixtures.py` 生成 `c1_blocked.json`（today=2027-04-15，加一份编造的「覆盖整个窗口但没有记录」的观测，not_met 和 BLOCKED 由代码判定）与 `c4_abstain.json`（真实 `ep.discover` 入口 + ScriptedReasoner 弃权）。没有覆盖：D1 霍尔木兹（没有 golden 图，ScriptedReasoner 也没有 inspect，只能等真实录制）、READY_FOR_REVIEW（C1 的出货阈值是 null，代码不会判 met）、AddShock（界面已砍）。
