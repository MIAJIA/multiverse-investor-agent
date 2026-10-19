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
| `catalyst/diff.py` | 两个版本的结构 diff（含 `changed_claim_ids`，供前端直接显示） | 代码 |
| `catalyst/store.py` | 不可变快照 + 操作日志 + trace + 录音，一次运行一个目录 | 代码 |
| `catalyst/reasoner.py` | Reasoner 边界：实时 / 录制 / 回放 | 模型 |
| `catalyst/evidence.py` | Evidence Provider 边界：按 pack 载入资料 | — |
| `catalyst/harness.py` | 受控生成：调模型 → 解析 → schema → 领域校验 → 带错误重写，最多重试 2 次 | 代码 |
| `catalyst/entrypoints.py` | discover / inspect / fork 三个入口 | — |
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
- **只由代码写的提案字段**：`support_status` 由关键依赖与进场条件所在 claim 的证据状态和情景 assessment 推导；`user_judgment` 里的 confirmed、confirmed_claim_ids、probability 只能由用户写（模型输出 schema 里根本没有这几个字段）。模型改写过原话时，`requires_user_confirmation` 一定是 true。
- **条件判定随版本重算**：inspect 和 fork 产出的每个新版本，都按观测和日期重新判定全部条件。`conditions.evaluate` 永不抛异常，日期不合法时给 unknown。
- **引用立场不能翻转**：引用片段时的 stance 必须与资料包里该片段的 stance 一致。
- **证据只挂在边上**：没有入边的节点不能标 supported（inspect 阶段的检查）。节点级证据留到后续。
- **fork 的引用校验**：补丁不能改证据引用，所以 fork 只校验 Stage 1 新增的边；基线图已有的引用在生成时已经校验过。Stage 1 的新边必须从新节点连到声明的 impacts。
- **情景不推进证据**：补丁不能改 `evidence_status`，节点只允许改 statement / time_bucket / instruments。
- **相对时间**：anchor 或 observation_window 写 `scenario:<事件>` 时合法，但在用户确认起点之前，判定结果一律是 unknown。
- **结构化输出**：用 pydantic schema 转成严格的 JSON Schema（所有 object 都 `additionalProperties: false`、全部字段列入 required）。API 拒绝该 schema 时，退回到在提示词里约束 JSON，由校验器兜底。
- **模型默认值**：`claude-opus-5-5`，effort 设为 high，开启 server-side fallback。可用 `CATALYST_MODEL` / `CATALYST_EFFORT` 覆盖。
- **重试**：每次重试是一个新的单轮请求，内容是原题、上次输出和错误清单，不改写历史消息。

## 已知限制（POC）

- 检索（BM25）没有实现：整个资料包直接进入上下文。检索由证据线补上。
- AddShock 的 Stage 1 由调用方在 op 里给出 `impacts`、`new_nodes`、`new_edges`；用模型识别任意冲击留到后续。
- 条件判定需要的观测数据（`Config.observations`）在 POC 里通常为空，所以条件大多是 unknown，进场判定大多是 WAIT。这是设计上的默认状态（先别动）。
- 市场参照没有接入：`market_reference` 一律为 null，即 no_market。
