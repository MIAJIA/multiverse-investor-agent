# Catalyst — 前端设计（UI/UX 与前端工程）

2026-10-18 · Mia

## 一句话与设计原则

前端是图快照的一个视图，不是第二个大脑：画布只渲染后端的 ClaimGraph 版本，用户在画布上的每一个动作都翻译成一个后端操作（ChangeAssumption / AddShock / confirm / commit），经校验器写入新快照后再回来重画。三个页面对应产品的六个站：Research Workspace（检验、条件、证据）、Sign-off（签字）、Scenario Diff（分叉）；发现（Discover）是 Workspace 的第一屏。

四条原则，后面每个屏幕都能追溯：

1.  **字少，一屏一个数字。** 每个页面只有一个大数字和一个主动作（Workspace 是条件的阈值，Diff 是“下一步查什么”的时限）；工程信息（版本号、写范围、哈希）不进主屏，放详情层。这是设计画布里 D 方向（苹果设计师）的结论。

2.  **四层状态不混成一个徽章。** 情景假设了什么、证据支持不支持、条件能不能核实和有没有满足、用户有没有签，是四件事，UI 上各有自己的位置和颜色。

3.  **不显示没有来源的数字。** 分叉后节点只标受挑战 / 未变 / 暂时到不了，不显示“-15%”这类传播出来的百分比；有引用的数字才显示，并带片段编号。

4.  **画布只读，动作有限。** 用户不能改节点文字、不能随意连边；能做的是改一个假设的值、加一个冲击、确认或改一个阈值、签字。这是工程文档“写图只经 graph.commit”在前端的体现。

## 信息架构

三个页面加一个输入屏，左侧导航固定：Analyze / Sign-off / Scenarios / Evidence；Monitoring 和 Projects 在三小时和 MVP 里置灰（慢环延期）。

| 页面                     | 回答的问题                       | 主要元素                                                                                                                           | 对应的站                   |
|--------------------------|----------------------------------|------------------------------------------------------------------------------------------------------------------------------------|----------------------------|
| 输入                     | 你相信什么会发生？               | 一行大字的 belief、可选的终点圆片（含“No target”）、一个按钮                                                                       | 第 1 站 事件               |
| Research Workspace（B1） | 它怎么传到标的？什么会证明我错？ | 没有终点时先显示最多 3 张候选卡（带三类标签）或一句弃权；点一张进入画布 + 右侧面板（详情 / 证据 / 条件）；底部固定工具条“What if…” | 第 2–4 站 发现、检验、条件 |
| Sign-off（B2）           | 我签哪几条？                     | 逐条假设表：假设、失效条件、证据状态、用户状态；底部是提案卡（WAIT / needs_review）和 Sign                                         | 第 6 站 提案与签字         |
| Scenario Diff（B3）      | 改了一个假设，什么变了？         | 基线 v1 vs 情景 v2 切换；画布按三态着色；右侧“下一步查什么”+ 提案 v2                                                               | 第 5 站 分叉               |
| Evidence                 | 我引了哪些材料？                 | 知识库 pack 列表、这一轮检索到的片段、每段的 stance 和被哪条边引用                                                                 | 证据先于推理的可见面       |

参考稿是 Mia 在另一个对话里做的 B1 / B2 / B3 三张图（深蓝导航、白卡片、四色节点）；取它的布局，按本文第 3–5 节改它的内容。

## 画布规范

画布是 ClaimGraph 快照的直接渲染：节点 = Claim，边 = Mechanism，自动排版（ELK，从上到下），默认只展开 3 个主要阶段（max_visible_hops），中间节点折叠成一个可展开的组。

### 四种节点

| 节点         | 来自                        | 卡片上显示                                                            | 颜色 |
|--------------|-----------------------------|-----------------------------------------------------------------------|------|
| Event        | 用户输入的 belief（根节点） | 原话 + 系统改写后的一句（两行，用户确认过打勾）                       | 蓝   |
| Assumption   | 链中间的 Claim              | 一句陈述 + 证据状态小字（supported / contradicted / unknown）+ 引用数 | 绿   |
| Outcome      | 终点，能解析到白名单标的    | 标的与方向                                                            | 紫   |
| Risk / Shock | AddShock 加进来的外部冲击   | 一句话 + “assumed, not observed”虚线框                                | 橙   |

关键依赖只有一个，用外发光的描边 + “Check first”小字标出；不给每个节点打 High / Medium / Low。边上显示机制一句话（悬停展开），有引用的边实线，model_only 的边虚线。

### 状态着色（情景页）

| 状态                  | 来自                | 样式                |
|-----------------------|---------------------|---------------------|
| 受挑战 challenged     | Scenario Assessment | 橙色边框 + 橙色圆点 |
| 未变 unaffected       | Scenario Assessment | 灰底 + 对勾         |
| 暂时到不了 unresolved | Scenario Assessment | 灰底 + 虚线描边     |

它们和证据状态是两层：一个受挑战的节点，证据状态仍然可以是 supported，卡片上两样都显示。

### 画布动作到后端操作的映射

| 用户在画布上做的事                                   | 翻译成的操作                                | 谁裁决                                       |
|------------------------------------------------------|---------------------------------------------|----------------------------------------------|
| 点一个节点                                           | 只读：右侧面板显示详情                      | —                                            |
| 在节点上改一个假设的值（如“开放日期”）               | ChangeAssumption（target, value）           | 代码算写范围，模型在范围内重评，校验器拒越界 |
| 左栏拖一个 Risk 节点进来，或底部工具条输入“What if…” | AddShock（statement）；三小时内接入点预定义 | 同上                                         |
| 改条件的阈值或截止                                   | confirm_condition（threshold, deadline）    | 校验器查类型和日期，不调模型                 |
| 在签字页点 Confirm / Sign                            | confirm_claim / commit                      | 写入 user_judgment，不改图                   |
| 改节点文字、删节点、随意连边                         | 不允许（POC 和 MVP 都禁用）                 | —                                            |

每个操作成功后后端返回新版本号，前端整体重画；前端不在本地改 store 里的节点数据。React Flow 模板自带的“拖节点改位置”保留，位置是纯展示状态，不进快照。

## 右侧面板

点一个节点，右侧面板分三个标签：详情、证据、条件。面板是整个前端里字最多的地方，所以它默认收起，点节点才展开。

**详情**：陈述、原话（如果被改写过）、证据状态、在当前情景下的评估、进出的边和机制一句话。是关键依赖的节点多一行：“为什么先查这一步”。

**证据**：两栈，Supporting (n) 和 Contradicting (n)，来自证据对象的 stance。每张证据卡：来源名、日期、片段编号（excerpt_id）、原文一段、它支持或反驳的是这条 Claim 的哪一句。没有证据的边显示“仅模型推断”，不显示空卡。模型对反方片段的回应（为什么不构成反驳）显示在那张卡下面。

**条件**（“What would prove this wrong?”）：每条 Condition 一行大字 + 一行小字。大字是人话（“到第 7 天每天少于 20 艘”），小字把字段露出来：观测量或来源 · 起点（anchor）· 截止（deadline）· 阈值（未知就显示“你来定”并可点开填）· 可核实 / 未核实 · 已满足 / 未满足 / 未知。“可核实”和“已满足”是两个徽章，不合并。用户改阈值或截止是这里唯一的写动作（confirm_condition）。

参考稿里的“Add”按钮在 POC 里不做：条件由模型提议、用户改数，不让用户从零写——这是和 Helm 那种“用户自写理由”有意不同的地方。

## 签字页与分叉页

### Sign-off（B2）

一张表，一行一条假设，底下一张提案卡。列：假设、失效条件（人话 + 截止）、证据状态、用户状态、动作。两个状态列必须分开：

| 列       | 取值                                   | 谁写             |
|----------|----------------------------------------|------------------|
| 证据状态 | supported / contradicted / unknown     | 后端，由引用推进 |
| 用户状态 | Not started / Needs review / Confirmed | 用户点 Confirm   |

“Confirmed”的意思是“我认这条假设和它的失效条件”，不是“证据成立”；一条证据 unknown 的假设也可以被 Confirm，因为用户签的是条件。顶部进度“3 / 6 confirmed”保留。

提案卡：标的与方向、成立条件（标明“且”）、失效条件（标明“或”）、状态。状态只有三个词：WAIT（先别动）、BLOCKED（受阻）、Ready for review；没有 Ready to execute。Sign 按钮下面一行小字：“签的是研究判断，不是下单”。签字后提案变成 draft 导出，UI 不提供任何执行按钮。

### Scenario Diff（B3）

顶部一个切换：基线 v1 / 情景 v2，情景名就是用户输入的那句话（“Iran is struck tomorrow”），旁边一个小徽章“假设，未观测”。画布按三态着色（第 3 节），冲击节点虚线框。

右侧不是指标表，是三块：

1.  **受挑战的前提**：哪几条、为什么（模型写的一句话）。

2.  **下一步查什么**：一条事件型 Condition，大字是时限（“72 小时”），两个分支写清：观测到 → 继续等；窗口结束未观测到 → 基线继续。

3.  **提案 v1 → v2**：状态变没变，哪个条件变了，追溯到哪个被改的假设。

参考稿里的“CoWoS -20%、GPU shipments -15%、Revenue -8% vs base case”不做：那是把冲击沿图传播成百分比，工程文档已经把概率和数值传播删掉了。有引用的数字（材料里写了“延期六个月”）可以显示在冲击节点上，带片段编号。“Save Scenario”= 快照已经存了，按钮只是给它起名。

## 前端工程

选型：React Flow 的 [workflow editor 模板](https://reactflow.dev/ui/templates/workflow-editor)（Next.js + Tailwind + shadcn/ui + Zustand + ELKjs 自动排版）。编辑器是它的，节点和面板是我们的。模板页面没有写许可证，React Flow 本身是 MIT；用之前看 ZIP 里的 LICENSE。

| 直接复用                                        | 自己写                                                             | 删掉                                    |
|-------------------------------------------------|--------------------------------------------------------------------|-----------------------------------------|
| 画布、拖拽、缩放、小地图、键盘操作              | 4 个节点组件（Event / Assumption / Outcome / Risk，各约 40–60 行） | Runner（“Run Workflow”顺序执行节点）    |
| 左侧拖拽栏（只留 Risk 一种可拖）                | 1 个边组件（机制文字 + 实线 / 虚线）                               | Transform / Join / Branch / Output 节点 |
| ELK 自动排版、深色模式、Zustand store 骨架      | 右侧面板（详情 / 证据 / 条件）、签字表、Diff 页的三块              | 节点文字编辑、自由连边、删节点          |
| shadcn 的 Button / Badge / Table / Tabs / Sheet | API 客户端（读快照、发操作）                                       | —                                       |

### 数据契约

后端给前端两个接口，前端不自己维护图的真相：

- `GET /graph/{version}` → 快照 JSON：nodes（id, kind, statement, original_statement, evidence_status, is_key_dependency, assessment）、edges（from, to, mechanism, evidence\[\] 含 stance / excerpt_id, model_only）、conditions（claim_id, kind, predicate, observable, anchor, deadline, threshold 可 null, verification_status, evaluation_status）、proposal（direction, entry\[\], exit\[\], status, support_status）、scenario（base_version, ops）、retrieved_excerpts\[\]。

- `POST /ops` → 一个操作（change_assumption / add_shock / confirm_condition / confirm_claim / commit），返回新版本号，或校验器的拒绝理由（前端原样显示）。

快照 →React Flow 的转换是一个纯函数 `toFlow(snapshot) → {nodes, edges}`：节点 data 里放 kind、状态、是否关键依赖；边 data 里放机制和是否 model_only。Zustand store 里只存“当前版本号 + 选中节点 + 对比的基线版本号 + 节点位置”；节点内容每次从快照重算，不在前端改。

### 目录结构（建议）

``` text
web/
  app/            页面：input / workspace / signoff / scenario / evidence
  components/
    nodes/        EventNode Assumption Node OutcomeNode RiskNode
    edges/        MechanismEdge
    panel/        Details Evidence Conditions
    signoff/      AssumptionTable ProposalCard
    scenario/     DiffSummary
  lib/
    api.ts        getGraph / postOp
    toFlow.ts     快照 → nodes/edges
    status.ts     四层状态 → 颜色与文案（唯一的映射表）
  store/          zustand：version, baseVersion, selectedNodeId, positions
```

后端仍是 Python（工程文档），前端通过这两个接口读写；POC 里前后端各一个进程，不做鉴权。

## POC 与 MVP 范围、时间与兜底

|               | POC（三小时里的 35–90 分钟）                                                         | MVP                                                  |
|---------------|--------------------------------------------------------------------------------------|------------------------------------------------------|
| 输入屏        | 一个输入框 + 终点圆片                                                                | 同左，加历史记录                                     |
| Workspace     | 只读画布 + 右侧面板（详情 / 证据 / 条件）+ 底部 What-if 工具条；候选卡用最简单的列表 | 加左侧拖 Risk 节点、折叠 / 展开中间节点、Evidence 页 |
| Sign-off      | 一张表 + 提案卡 + Sign                                                               | 加逐条 Confirm 的历史、导出                          |
| Scenario Diff | 三态着色 + 右侧三块                                                                  | 加基线 / 情景并排、多情景                            |
| 交互          | change_assumption、add_shock（预定义接入点）、confirm_condition、commit              | 加任意冲击、confirm_claim                            |
| 时间          | 用 React Flow 模板约 90 分钟；从“排序精细度”和“UI 动画”里省                          | —                                                    |

兜底：如果到第 115 分钟前端还没跑通，换成 Streamlit 一页：Graphviz 渲染图（按三态着色）+ 条件列表 + 提案卡 + 一个输入框。功能不少，只是不好看。这个判断点写进工程文档的时间表。

设计稿来源：设计画布里的 D 方向网页版（输入 / 论点 / 假如三屏）定字数和气质，Mia 的 B1 / B2 / B3 参考图定布局和导航。两者冲突时以本文第 1 节的四条原则为准。

## 开放问题

- 候选卡（Discover 的 3 个方向）放在 Workspace 的第一屏，还是单独一页？现在定的是第一屏。

- 折叠的中间节点展开后，关键依赖的高亮要不要跟着进折叠组内部？

- Sign-off 表里的“Needs review”是系统推的（证据 contradicted 或条件未核实）还是用户标的？建议系统推。

- 模板的许可证未确认。
