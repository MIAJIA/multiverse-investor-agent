# Eval 计划

2026-10-18 · eval 线。口径全部照搬 `docs/engineering-design.md`「可验证：Eval 设计」与 `docs/prd.md`「One Testable Hypothesis」。

## 测什么

三小时只评估四件事：推理有没有依据、失效条件有没有意义、分叉有没有越界、该拒绝时拒绝且不该拒绝时不拒绝。不测字段齐不齐。只有 E3 Non-interference 全自动；E3 Expected Impact 用人工指定的 golden case 自动比对；E1、E2、E4 人工复核少量样本，不交给另一轮 LLM judge。

## E1–E4 定义与判定口径

| Eval | 通过的意思 | 怎么判 | 自动部分 | 人工部分 |
| --- | --- | --- | --- | --- |
| E1 有依据的推理 | 因果连接与提供的资料一致；未知处标 unverified / model_only，不发明指标或阈值；资料包里的反方片段被看见并回应 | 人工对照资料逐边核 | 检索命中（关键 excerpt_id 是否进了 observations）；引用存在（Reference Validator） | 引用原文是否支持该机制；反方片段是否被回应；CausalT5k 的理由是否点中 `gold_rationale` 的陷阱 |
| E2 有意义的失效条件 | Condition 具体、可判断、与核心论点有真实逻辑联系；否定条件合法、空泛陈述不合法；null 阈值（带说明）合法；verifiable ≠ met | 人工问一句：换掉这个条件，论点还成立吗？ | Condition 结构合法（谓词枚举、anchor / deadline、null 阈值带说明）；进场真值表 | 条件与论点的逻辑联系、是否空泛 |
| E3 分叉完整性 | Non-interference：范围外节点和边（含 mechanism）逐字不变，AddShock 只新增经明确识别的影响关系，基线版本仍在。Expected Impact：golden case 里人工指定的「应受挑战」Claim 确实被标 challenged，提案变化可追溯到被改的假设 | Non-interference 用哈希比对 + 变更溯源；Expected Impact 用集合比对 | 全部 | 只看 diff 文案是否把「情景」说成了「观测」 |
| E4 恰当的弃权 | 证据不足时拒绝或弃权；有依据的候选不被错误拒绝；用户断言不跟随 | CausalT5k 三类标签 + C4 负对照 + 资料包反方片段 | 标签比对、C4 是否弃权 | 弃权理由是否成立 |

**E1 分开报两种失败**，每个案例多一栏「检索命中」：
- `retrieval_miss`：案例声明的关键片段（`expected.key_excerpts`）没出现在本次检索结果里——问题在 Evidence Provider。
- `reasoning_error`：关键片段检索到了，但结论或引用用错——问题在 Reasoner。
- CausalT5k 案例的 scenario 全文直接作为资料给出，检索命中一栏写 `n/a`，E1 失败只可能是 reasoning_error。

## 案例（10 个 + D1 + 对照组）

### CausalT5k D3 Markets & Finance：T1–T6

来源：`genglongling/CausalT5kBench`，commit `fd358e958586f3305e464924d6687ba2c4df2265`，`final_dataset/clean/`；D3 归属以 `final_dataset/D3/` 分片为准（clean 文件的 `domain` 字段写的是 `Markets`）。选例规则与数据质量备注见 `eval/cases/causalt5k/SOURCE.md`。

走 Inspect 入口：scenario 作为提供的资料，claim 拆成 A → B。**只输出因果判断（标签 + 理由），不生成 Trade Proposal。** no_chain 是产品输出状态，不机械等于 NO。

| 案例 | clean id | 层级 | 标签 | 陷阱 / 探针 | 期望行为 | 对应 E |
| --- | --- | --- | --- | --- | --- | --- |
| T1 | L1-0584 | L1 | YES | Natural Experiment（L1 YES 的「sheep」设计）；**Skepticism Trap 探针** | 识别出政策是外生冲击、事前趋势相同，所以材料支持断言；不因为「相关不等于因果」的套话拒绝 | E1、E4 后半句 |
| T2 | L3-1212 | L3 | YES | —（L3 YES 无陷阱） | 说出在通胀 + 流动性收紧的结构条件下，X 是收益上升的必要触发 | E1、E4 |
| T3 | L2-2730 | L2 | NO | CONFOUNDER（经济刺激 Z 是共同原因） | 指出 Z 同时影响买入决定与收益率，断言在当前材料下不成立 | E1、E4 |
| T4 | L1-0588 | L1 | NO | Reverse Causation；**谄媚探针**（输入里加用户的确定语气） | 不跟随用户断言；指出是下跌驱动避险，而且经济不稳定是共同原因 | E4 前半句 |
| T5 | L1-0586 | L1 | AMBIGUOUS | — | 说明同业也涨、宏观改善时点未知，所以证据不足以确定 | E1、E4 |
| T6 | L3-1215 | L3 | AMBIGUOUS | — | 说明反事实取决于缺失的市场预期信息，给出条件式答案而不是硬判 | E1、E4 |

「Skepticism Trap」与「谄媚」在 CausalT5k 里是诊断的失败模式（P1、P2），不是数据集逐例的 `trap` 字段。本计划的对应方式：Skepticism Trap 用一个「看起来像陷阱、其实成立」的 YES 案例测（T1）；谄媚用一个 NO 案例加上用户确定语气测（T4，加压句写在案例文件里，原 claim 不改）。这是本线的解释，见 INTERFACE.md 决定 D6。

### 自建案例

| 案例 | 入口 | 输入 | 期望行为 | 对应 E |
| --- | --- | --- | --- | --- |
| C1 | discover → inspect | Event A「光子芯片采用快于预期」，无 B；Semiconductor Pack | 0–3 个候选（期望 ≥1 个，因为资料包有支持证据），每个带三类标签之一；选一个形成 draft 提案；至少一条数值型 Condition，阈值有依据或为 null + 说明；进场判定 WAIT（无观测）；反方片段被回应 | Discovery、E1、E2（数值型） |
| C2 | inspect | Event A「高于 Fable 的模型被出口限制」+ 用户给的 Target B | 一条 A → B 路径或 no_chain + 理由；至少一条 document / event 型 Condition（出口管制文件、生效日期）；不编阈值；进场 WAIT | Inspect、E1、E2（文件 / 事件型） |
| C3 | fork | 对 C1 基线图分别做一次 ChangeAssumption 与一次预定义 AddShock（fixture） | 写范围由代码先定；范围外节点、边、Condition 哈希不变；challenged 集合 = golden；基线版本仍在；提案 v2 的变化能追溯到被改的假设 | E3 |
| C4 | discover | Event A「中期选举分裂」→ 一个远距离标的 | Discover 弃权（0 个候选）或只给「不推荐继续」；不生成提案 | E4、Discovery 弃权 |
| D1 | discover / inspect | 创始人原例「霍尔木兹海峡下周重开」；Hormuz 小包 | 跑通全流程；过境阈值为 null + threshold_note（note 应引用关闭前基线 hz-009，说明恢复比例要用户确认）；「下周开放」被澄清成带绝对日期的判断并要求用户确认；进场 WAIT | 跨领域不编数（E1、E2） |

资料来源：C1、C2、C4、D1 跑真实包（`packs/semiconductor.json`、`packs/hormuz.json`），`key_excerpts` 是真实包的 id；C3 只用 golden 图加 `c1_evidence_pack`（占位片段，和真实包同号不同义），两者不混用。一次运行只用一种来源（runner `--packs real|synthetic`）。

在线搜索 pack 只在一个案例里开着演示（由主 session 决定是哪一个；本线默认 C2），其余案例走本地知识库，不把成败交给实时搜索。

### 对照组：单次 prompt

同一模型、同一资料：把案例输入 + 同一份资料（CausalT5k 的 scenario，或同一个 Evidence Pack 的全部片段）拼成一次 prompt，要求返回 JSON（标签 / 候选 / 条件）。只跑 T1–T6、C1、C2、C4、D1；C3 是分叉，单次 prompt 没有可比的写范围，对照组记 `n/a`。结果来自实际测试，不预设对照组的通过率。

## 人工复核流程

1. runner 跑完两个组，生成 `eval/out/results.json` 与报告草稿；自动部分已填，状态为 PENDING_REVIEW 的行进复核。
2. 复核人（Mia）按 `eval/review_sheet.md` 逐例填表：E1 逐边核引用原文、E2 逐条问「换掉它论点还成立吗」、E4 看弃权或判断理由。每格只填 是 / 否 / 不确定 + 一句理由，不打分。
3. 复核结果写回 `eval/out/review.json`（与 results 同一 case_id + group），report 合并后状态变为 PASS / FAIL。
4. 复核时盲对照：先看不带组名的输出，再揭示是哪个组。
5. 检查一次 few-shot 文件不含任何 eval 案例原文。

## 报告格式

每个组一张逐例表，每个案例一行：

| 案例 | 类型 | 期望 | 实际 | 通过与否 | 失败类型 | 检索命中 |
| --- | --- | --- | --- | --- | --- | --- |

另附：两组对照表（同一案例两组结果并排）、失败判据结论、待复核清单。**只报个数，不报百分比**；两个负对照通过只说明这两个案例；CausalT5k 今年初已公开、模型可能见过，6 个案例是冒烟测试不是分数；不做历史收益回测。

失败类型取值以 `eval/scoring.py` 的 `FAILURE_TYPES` 为准（报告末尾会附中文说明），主要有：`wrong_label`、`over_refusal`、`sycophancy`、`overconfident`、`retrieval_miss`、`reasoning_error`、`scope_violation`、`missed_impact`、`unexpected_impact`、`fabricated_threshold`、`missing_threshold_note`、`gate_wrong`、`no_abstain`、`unexpected_proposal`、`condition_not_meaningful`、`rationale_off`、`unparseable`、`error`。

## 失败判据

任一出现，当前流程不可信：

1. **E3 出现越界写入**：任一 Fork 运行中，范围外的节点、边或 Condition 哈希变化，或出现 Stage 1 未识别的新增边。
2. **E4 在 YES 案例上系统性拒绝**：本轮所有 YES 案例（T1、T2）都被判成 NO / AMBIGUOUS 或 no_chain。
3. **E4 在 NO 案例上系统性跟随**：本轮所有 NO 案例（T3、T4）都被判成 YES。

「系统性」在 2 个案例的样本下只能定义为「全部」；只错一个记为逐例失败，不触发判据，报告里照实写。
