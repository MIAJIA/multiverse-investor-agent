# Catalyst 核心：schema、校验器与 harness

2026-10-18 · 主线（core-schema 分支）

本文只记录实现层的决定。产品与架构以 `docs/prd.md`、`docs/engineering-design.md` 为准，eval 的接口提议见 eval 分支的 `eval/INTERFACE.md`。

## 模块

| 模块 | 职责 | 谁写 |
| --- | --- | --- |
| `catalyst/schema.py` | 唯一数据契约：持久化对象（Graph、Condition、Scenario、TradeProposal…）与模型输出对象（`*Output`） | — |
| `catalyst/validator.py` | 结构校验：图（id、无环、可达 terminal、证据或 model_only）、Condition（阈值说明、日期、窗口）、引用（excerpt 存在于当前资料包、model_only 不冒充、supported 有证据撑、反方片段被回应） | 代码 |
| `catalyst/conditions.py` | 条件判定 met / not_met / unknown | 代码 |
| `catalyst/gate.py` | 进场 AND 真值表、退出 ANY / ALL | 代码 |
| `catalyst/fork.py` | 写范围计算、补丁应用（越界即拒）、Scenario 默认值 | 代码 |
| `catalyst/branches.py` | 分支推导：独有部分、分叉点、kind（hypothetical / evidenced / model_only）、trunk | 代码 |
| `catalyst/diff.py` | 两个版本的结构 diff（含 `changed_claim_ids`，供前端直接显示） | 代码 |
| `catalyst/store.py` | 不可变快照 + 操作日志 + trace + 录音，一次运行一个目录 | 代码 |
| `catalyst/reasoner.py` | Reasoner 边界：实时 / 录制 / 回放 | 模型 |
| `catalyst/evidence.py` | Evidence Provider 边界：按 pack 载入资料 | — |
| `catalyst/harness.py` | 受控生成：调模型 → 解析 → schema → 领域校验 → 带错误重写，最多重试 2 次 | 代码 |
| `catalyst/entrypoints.py` | discover / inspect / fork 三个入口，加上批准（sign） | — |
| `catalyst/__main__.py` | harness CLI：跑案例、录制、回放、提升 fixture | — |

## 为什么不手写 fixture

图层面的 fixture 由 harness 跑真实案例录下来，再用 `promote` 提升到 `fixtures/`，UI 和测试共用这一份。

- **录制**：`RecordingReasoner` 把每次请求的哈希和原始输出写进 `cassette.jsonl`，同时 `RunStore` 落下快照、提案、情景、trace 和操作日志。
- **回放**：`ReplayReasoner` 按请求哈希返回录音，过程确定、零成本。prompt、资料包、schema 或输入任何一项变了，回放都会报 `CassetteMiss`，不会拿旧答案冒充。
- **仍需人写的只有两类**：期望（gate 应是什么、C3 里哪些 claim 应受挑战），因为期望不能来自模型自己的输出，否则是循环论证；以及纯代码测试的最小输入（真值表里的几个 Condition）。

## 对 eval/INTERFACE.md 的决定

| # | 决定 |
| --- | --- |
| D1 | 采纳：edge / condition 有 `id`，graph 带 `conditions`，node 带 `role`。 |
| D2 | **改为 met。** evaluation_status 回答「这个条件是否成立」：`not_observed_by` 在窗口结束、来源覆盖整个窗口、窗口内没有记录时，「到期未发生」这个条件成立。窗口内看到了记录就给 not_met；其余一律 unknown。设计文档原文写的 not_met 需要同步改。 |
| D3 | 采纳：not_met 优先于 unknown，结果是 BLOCKED。 |
| D4 | 采纳：写范围 = 目标及其后代 + 这些节点的出边 + 挂在这些节点上的条件；起点在范围外的入边不在范围内。 |
| D5 | assessment 由模型在补丁里提议，代码只接受范围内的 claim，范围外一律由代码写 unaffected。 |
| D6–D9 | 采纳 eval 线的默认。 |

## 其他实现决定

- **规范形式**：快照、API、diff 和哈希一律使用字段齐全（含默认值）的 `dump()`。E3 的哈希比对必须先把两边都经过 schema 规范化，不能直接哈希手写的原始 dict。
- **提案状态拆成两个字段**：`status`（生命周期）和 `gate`（进场判定：WAIT / BLOCKED / READY_FOR_REVIEW），两者都只由代码写。gate 为 READY_FOR_REVIEW 时 status 是 needs_review，否则是 draft。
- **只由代码写的提案字段**：`support_status` 由关键依赖与进场条件所在 claim、以及这条分支独有的 claim 的证据状态和情景 assessment 推导；`user_judgment` 里的 confirmed、confirmed_claim_ids、probability 只能由用户写（模型输出 schema 里根本没有这几个字段）。模型改写过原话时，`requires_user_confirmation` 一定是 true。
- **条件判定随版本重算**：inspect 和 fork 产出的每个新版本，都按观测和日期重新判定全部条件。`conditions.evaluate` 永不抛异常，日期不合法时给 unknown。
- **引用立场不能翻转**：引用片段时的 stance 必须与资料包里该片段的 stance 一致。立场有三种：supports、contradicts、neutral。neutral 是背景信息（如「数据每周才更新」），可以引用，但不让 claim 变成 supported，也不需要 rebuttal，`unanswered_contradictions` 也不管它。三种立场两两都不能互相翻转。
- **证据只挂在边上**：没有入边的节点不能标 supported（inspect 阶段的检查）。节点级证据留到后续。
- **fork 的引用校验**：补丁不能改证据引用，所以 fork 只校验 Stage 1 新增的边；基线图已有的引用在生成时已经校验过。Stage 1 的新边必须从新节点连到声明的 impacts。
- **情景不推进证据**：补丁不能改 `evidence_status`，节点只允许改 statement / time_bucket / instruments。
- **情景叠加**：在一个情景版本上再分叉时，新情景接着上一层算。
  - `ops` = 父情景的 ops 加上这次的 op；`base_version` 是直接父版本，`root_version` 是最初的非情景基线（老快照没有这个字段，读到 None 时按 `base_version` 理解）。
  - assessment 先继承父情景：写范围内的 claim 用模型这次给的值，范围外的保留父情景的值，不重置成 unaffected。
  - 提案的 `scenario_ref.challenged_claim_ids` 和 `support_status` 按叠加后的 assessment 算。
  - 上一层的「受挑战」不会因为这一层没涉及就被抹掉。要撤销一层情景，只能回到更早的版本。如果模型在写范围内把上一层的 challenged 改掉了，用模型的值，但给一条非阻断提示。
  - `fork(scenario=...)` 传入基线版本的情景，不传就从 store 读。签字不改情景：情景版本签字后，新版本带着同一个情景，在签字版本上再分叉照样叠加。
- **相对时间**：anchor 或 observation_window 写 `scenario:<事件>` 时合法，但在用户确认起点之前，判定结果一律是 unknown。
- **结构化输出**：用 pydantic schema 转成严格的 JSON Schema（所有 object 都 `additionalProperties: false`、全部字段列入 required）。API 拒绝该 schema 时，退回到在提示词里约束 JSON，由校验器兜底；退回原因（API 错误原文）记进 meta 的 `schema_fallback_reason`，录音和 trace 里都能看到。
- **Inspect 分两步**：一整份 `InspectOutput` 被 API 拒绝（`The compiled grammar is too large`）。实测语法预算大约只够 70 个平铺的字符串字段，可空字段和对象数组还要额外占用；InspectOutput 有 64 个字段、18 个可空字段，嵌套数组也多，就算去掉全部 union、enum 和 description 仍然超限，所以没法靠删字段解决。现在分两步：`inspect`（`InspectGraphOutput`：no_chain、nodes、edges）→ `inspect.plan`（`InspectPlanOutput`：conditions、proposal），两份 schema 都实测能被接受，每份的 union 数都在 API 上限 16 以内。第 2 步只在图通过校验后才跑，并把定稿的图放进提示词；错误只回给出错的那一步重写。`inspect()` 的返回形状不变，`attempts` 是两步之和。
- **节点短标题**：Claim 有可选字段 `label`（10 个汉字或 4 个英文词以内），老快照没有这个字段也能解析。Inspect 必须写（缺了是阻断错误）；超长只给非阻断提示，代码不截断。分叉补丁可以改 label。
- **anchor**：绝对时间窗口的 anchor 写今天或事件已发生的日期；只有相对于一个尚未发生、要用户确认起点的事件时才写 `scenario:`。全部条件都是 scenario anchor 时，inspect 给一条非阻断提示（这种提案在用户确认前只会停在 WAIT）。
- **分叉的 assessment**：提示词列出「需要给出 assessment 的 claim id」（= 写范围的 nodes）。写了边、条件或范围外 claim 时，一次列出全部错误（「c1.e4 是边，不是 claim；assessment 只写这些 claim：[...]」），由模型重写；代码不静默丢掉非法条目。被改的假设本身和新加的冲击节点是情景输入，写 unresolved；challenged 只用于依赖它们的 claim。
- **Discover 的弃权边界**：只有找不到任何合理机制时才弃权（只能靠「情绪」「政策不确定性」这类泛化渠道硬连，也算没有机制）。下面三种情况都不弃权：没有支持片段（标 hypothesis）；有未驳回的反方片段（这是 Inspect 阶段的校验）；需要用户确认日期或定义。
- **模型默认值**：`claude-opus-5-5`，effort 设为 high，开启 server-side fallback。可用 `CATALYST_MODEL` / `CATALYST_EFFORT` 覆盖。
- **重试**：每次重试是一个新的单轮请求，内容是原题、上次输出和错误清单，不改写历史消息。

## Critic（本期不启用）

**要解决什么。** Inspect 的校验器只裁决结构：引用存不存在、立场有没有翻转、阈值有没有说明。它不裁决推理本身。有两类错误结构校验抓不到：
- 关键依赖选错了。key_dependency 指向一个容易验证、但对结论影响不大的条件，真正会推翻论点的前提反而没被列出来。
- 谄媚或过度怀疑。用户语气很确定时，模型顺着用户把链补齐了；或者反过来，只因为资料里有反方材料，就把一条站得住的链判弱了。

Critic 是另一个 prompt，只检查用户选中的那一条链。它的输出是「对哪个 claim 提了什么质疑」，即 `CriticReport.items = [{claim_id, challenge}]`。它只提质疑，不改图，也不改 gate。

**为什么本期不做。** 设计文档把 Critic 列为可选项，并且是时间不足时第二个放弃的（排序精细度 → Critic → 市场参照 → UI 动画）。本期优先保证状态一致性、证据标注、拒绝机制和端到端流程。另外，Critic 本身也要有 eval 才能判断它是在帮忙还是在添乱，而目前 eval 里还没有针对 Critic 的案例。

**现在的占位。** 接口先定下来：
- `TradeProposal.critic` 一律是 `{status: "disabled", reason: "未启用：不在本期范围", items: []}`，老快照没有这个字段时也按这个值解析。
- `entrypoints.critic()` 直接返回 disabled，不调模型。`derive_proposal` 每次生成提案都会调用它，前端可以按这个字段显示「未启用」。
- 将来实现时必须走 `run_stage`（解析 → schema → 领域校验 → 带错误重写），用独立的 prompt；claim_id 只能是选中链上的节点。模型失败时给 `status: "failed"`，不阻断提案。

## 已知限制（POC）

- 检索（BM25）没有实现：整个资料包直接进入上下文。检索由证据线补上。
- AddShock 的 Stage 1 由调用方在 op 里给出 `impacts`、`new_nodes`、`new_edges`；用模型识别任意冲击留到后续。
- 条件判定需要的观测数据（`Config.observations`）在 POC 里通常为空，所以条件大多是 unknown，进场判定大多是 WAIT。这是设计上的默认状态（先别动）。
- 市场参照没有接入：`market_reference` 一律为 null，即 no_market。

## HTTP 接口（`catalyst/api.py`）

前端用的薄 HTTP 层，不含业务逻辑：只把请求翻译成入口调用，再从 RunStore 读出版本。运行 `.venv/bin/python -m catalyst.api`，地址是 http://localhost:8000。设 `CATALYST_REPLAY=<录制目录>` 时用录音回放，不调用模型。

- 所有写操作都返回 `{ok, errors, version}`，前端拿到版本号后再 GET 这个版本。
- `GET /api/runs/{id}/versions/{v}` 返回 `{graph, proposal, scenario, diff, excerpts}`。`diff` 相对父版本计算，`promote` 写出的 fixture 也是这个形状。
- **sign = 批准一份计划**，不调用模型，产出一个新版本（`op.kind = "sign"`，`op.value.terminal_id` 是批准的那份）：
  - 请求体 `{version, terminal_id, clarified_statement?, criteria?, deadline?, confirmed_claim_ids?, condition_overrides?}`。`terminal_id` 必填，缺了回 `{ok: false, errors}`（不再因 KeyError 变成 404）；三个文本字段不给就沿用计划里的值，所以不能通过 sign 清空它们。
  - 用户改的阈值和截止写进条件；截止提前时，观测窗口跟着收。改条件不调用模型，代码重新判定、重新派生全部计划。
  - 被批准的那份 `user_judgment.confirmed = true`；同版本其他计划的 confirmed 置 false（D-B4），保留它们的 confirmed_claim_ids。
  - 批准时只能改 threshold / threshold_note / comparator / deadline 这几个字段。
- **fork** 以基线版本的全部计划和 observations 为输入，逐份重新派生；只有受影响的计划失效（见下节「方案 B」）。

## 方案 B：一张图多条分支 + 批准计划（B-最小，后端）

依据 `docs/changes/2026-10-18-branches-and-plans.md` 第 4 节。

- **数据结构**：
  - `ProposalDraft` / `TradeProposal` 带 `terminal_id`，`Direction` 仍必填。
  - `InspectPlanOutput.proposals` 是列表，结构化输出实测被 API 接受（Haiku，2 次调用，无 fallback；union 12 个，上限 16）。
  - 版本包见 `schema.VersionBundle`，一次切换成 `proposals`，不留 `proposal`。
- **计划顺序**：按图里 terminal 的顺序排，默认显示哪一份不由模型输出顺序决定。
- **旧文件**：
  - `proposals/<v>.json` 是单个 dict 时，`parse_proposals` 包成一项的列表，按 `direction.instrument` 在图里找唯一的 terminal 填 `terminal_id`；找不到或有多个时报 `LegacyProposalError`，不猜。
  - `observations/<v>.json` 新增 `synthetic`（本版本资料里有合成占位资料包），旧文件缺失时按 false 读。
- **分支推导**（`branches.derive_branches`，store.bundle、promote、fork / inspect 的返回体共用）：
  - 独有部分：`(ancestors(t) ∪ {t}) − ⋃ ancestors(其他 terminal)`，独有边是终点在独有部分里的边。
  - 分叉点：几条出边能到达的 terminal 集合不一样的节点；每条分支列出它祖先里的分叉点。
  - kind：
    1. hypothetical：`ancestors(t) ∪ {t}` 含 role=shock 的节点、情景冲击新增的节点或情景 ops 改过的假设（terminal 本身被改也算）。
    2. evidenced：独有边至少一条，全部非 model_only 且带 supports 证据；独有节点没有 contradicted；独有边不引用合成片段。
    3. model_only：其余情况。
  - 独有部分一条边都没有时不算 evidenced。`synthetic_evidence` 标「独有边引用了合成片段」，与 kind 独立。
  - trunk：祖先里不属于独有部分的节点及其入边，按同一规则算；没有边（只共用起点事件）时是 evidenced。
- **计划校验**（`validator.validate_plans`）：
  - 阻断：
    - terminal 集合恰好等于图上全部 terminal（缺、重、挂在非 terminal 上都报）；
    - 标的属于该 terminal；
    - 引用存在；
    - 至少一条进场条件。
  - 非阻断：进场条件挂在非上游 claim 上。离场条件不提示，因为提示词鼓励用对手分支上的镜像信号当离场条件。
- **改假设后哪些计划失效**（`entrypoints.plan_affected`，只看代码算出的写范围）：
  - 判定：terminal 在写范围里，或者进场 / 离场条件挂在写范围内的 claim 上，或者 key_dependency 指向写范围内的 claim 或条件。
  - 受影响：confirmed 置 false，confirmed_claim_ids 剔除写范围内的 claim。其余计划的批准原样保留。
  - `approval_reset`：原本已批准、这次受影响。
  - `rival_changed`：本计划没受影响，但同版本另一份受了影响。只说「另一份受了影响」，不判断两者是否竞争（C1 那种并列受益的 terminal 也会触发）。
  - 两个标记每次派生都重算，inspect 和 sign 一律写 false。
- **补查挂钩**：`inspect` 里图和计划建好、还没落盘的位置留了注释，agent loop 在那里接（缺口用 `kind == "model_only"`）。
- **提示词 p5**：竞争分支只在真正的争议点给出；尚未发生的事件一律 role=shock；每个 terminal 一份计划，鼓励镜像条件。旧录音全部失效，需要重新录制。
