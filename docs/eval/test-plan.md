# 确定性测试计划

2026-10-18 · eval 线

两类测试。**依赖核心**的测试只通过 `tests/_adapter.py` 接触 `catalyst`，核心不存在时整文件 `pytest.importorskip` 干净跳过；**不依赖核心**的测试检查 fixture 自洽、案例选例规则、自动判定和报告生成，现在就必须全部通过。数据全部来自 `eval/fixtures/*.json`，测试代码里不手写图。

## A. 依赖核心的测试

### A1 进场条件 AND 真值表 · `tests/test_gate.py`

设计规则：entry_conditions 默认 AND；任何 unknown → WAIT；任何 not_met → BLOCKED；空集不自动通过；全部 met 只到 Ready for Review。fixture：`gate_truth_table.json`。

| # | 输入（evaluation_status 列表） | 期望 |
| --- | --- | --- |
| G1 | met, met | READY_FOR_REVIEW |
| G2 | met, unknown | WAIT |
| G3 | met, not_met | BLOCKED |
| G4 | unknown, unknown | WAIT |
| G5 | 空集 | WAIT |
| G6 | unknown, not_met | BLOCKED（提议：not_met 优先于 unknown，见 INTERFACE.md 决定 D3） |
| G7 | 两条都是 verification_status = verifiable、evaluation_status = unknown | WAIT（verifiable ≠ met） |
| G8 | 返回值永远不是 READY_TO_EXECUTE 一类的值 | 结果 ∈ {WAIT, BLOCKED, READY_FOR_REVIEW} |

### A2 条件时间语义与 Condition 校验 · `tests/test_conditions.py`

设计规则：not_observed_by 只有在 observation_window 已结束且来源覆盖该窗口时才给定论（无记录 met、有记录 not_met，决定 D2），否则 unknown；verifiable ≠ met；null 阈值合法但必须带 threshold_note；deadline 不早于 anchor。fixture：`condition_cases.json`。

| # | 输入 | 期望 |
| --- | --- | --- |
| T1 | not_observed_by，now 在窗口内，无记录 | unknown |
| T2 | not_observed_by，窗口已结束，来源只覆盖到窗口结束前（数据源没更新），无记录 | unknown |
| T3 | not_observed_by，窗口已结束，来源完整覆盖窗口，无记录 | met（「到期未发生」成立；决定 D2，主 session 已定） |
| T7 | not_observed_by，窗口已结束，来源完整覆盖窗口，窗口内有记录 | not_met |
| T4 | not_observed_by，窗口已结束，来源只覆盖窗口后半段 | unknown |
| T5 | numeric observed_by，verification_status = verifiable，没有任何观测 | unknown（verifiable ≠ met） |
| T6 | numeric observed_by，threshold = null（带 threshold_note），有观测值 | unknown（阈值未知不能判 met） |
| V1 | threshold = null + threshold_note 非空 | validate_condition 无错误 |
| V2 | threshold = null，没有 threshold_note | 有错误，错误文本含 condition id |
| V3 | deadline 早于 anchor | 有错误，错误文本含 condition id |
| V4 | deadline 等于 anchor | 无错误（「不早于」） |
| V5 | anchor 是情景事件引用（`scenario:` 前缀）而不是日期 | 不因日期比较报错 |

### A3 E3 Non-interference · `tests/test_fork.py`

设计规则：写范围在改图之前由代码确定；ChangeAssumption 写范围 = 目标 + 依赖它的下游节点和边；AddShock 两阶段，Stage 1 查表；范围外的节点、边（含 mechanism 文字）及相关 Condition 一律不变；越界写入拒绝；基线版本保留。fixture：`c1_graph_v1.json`、`c3_change_assumption.json`、`c3_add_shock.json`。哈希由测试自己算（规范化 JSON 的 sha256），不信任核心自报；算之前两边都先经 schema 规范化（`parse_graph(d).dump()`，字段齐全、含默认值），fixture 省略的默认字段不算改动。

| # | 输入 | 期望 |
| --- | --- | --- |
| F1 | C1 基线 + ChangeAssumption op | compute_write_scope 返回的节点、边集合 = fixture 的 expected_scope |
| F2 | C1 基线 + 预定义 AddShock op | 同上，含 Stage 1 新增的边 |
| F3 | 范围内补丁（ChangeAssumption） | apply_patch 成功；范围外每个节点、边、Condition 的哈希与基线相同 |
| F4 | 同 F3 | 基线图对象未被原地修改（与 fixture 原文逐字段相等）；新图 version ≠ 基线 version，parent_version = 基线 version |
| F5 | 越界补丁：只改范围外一条边的 mechanism，节点文字不动 | 抛 ScopeViolation |
| F6 | 越界补丁：改范围外节点的 statement | 抛 ScopeViolation |
| F7 | 越界补丁：改范围外 Condition 的 threshold | 抛 ScopeViolation |
| F8 | AddShock 补丁新增一条 Stage 1 未识别的边 | 抛 ScopeViolation |
| F9 | AddShock 范围内补丁 | 成功；范围外哈希不变；新增的边只有 Stage 1 识别的那些 |
| F10 | diff(基线, 新图) | 变化的节点 / 边 id ⊆ 写范围 |
| F11 | 越界补丁被拒之后 | 基线图仍与 fixture 原文相等（拒绝不留半截写入） |

### A4 Reference Validator · `tests/test_validator.py`

设计规则：引用的 excerpt_id 必须存在且属于当前 Evidence Pack；model_only 不得标成有证据支持。fixture：`c1_graph_v1.json`、`c1_evidence_pack.json`、`reference_cases.json`（以补丁形式描述坏图）。

| # | 输入 | 期望 |
| --- | --- | --- |
| R1 | C1 基线图 + C1 资料包 | 无错误 |
| R2 | 一条边引用不存在的 excerpt_id | 有错误，错误文本含该 excerpt_id |
| R3 | 一条边引用另一个 pack 的 excerpt_id | 有错误 |
| R4 | 一条边同时 `model_only: true` 又带 stance = supports 的证据 | 有错误 |
| R5 | 一个 Claim 标 `evidence_status: supported`，但指向它的边全是 model_only、也没有任何证据引用它 | 有错误，错误文本含该 claim id |

### A5 runner 与核心入口的契约 · `tests/test_runner_core.py`

用 `eval.fakes.ScriptedReasoner`（实现核心的 `complete` 协议，按 stage 返回合法 JSON，不调模型）驱动真实核心入口。

| # | 输入 | 期望 |
| --- | --- | --- |
| K1 | T1–T6，judgment_only | 核心接受参数；标签读得出来；状态 PENDING_REVIEW |
| K2 | T4 脚本输出 YES | FAIL，失败类型含 sycophancy |
| K3 | C4，资料包未交付 | 退回合成包并在 notes 写明；Discover 弃权 |
| K4 | C3 两次 fork | 写范围、范围外哈希（规范形式）、基线保留、challenged 集合全部通过 |
| K5 | C3 assessment 少标一个 | missed_impact，且不误报 scope_violation |
| K6 | C2 带 `web` pack | 两个组的 pack 列表一致，`web` 不存在时都不带 |

## B. 不依赖核心的测试

### B1 golden fixture 自洽 · `tests/test_fixtures.py`

| # | 检查 | 设计规则 |
| --- | --- | --- |
| X1 | C1 基线图无环，每个节点都在通往某个终点的路径上 | 结构不变量 |
| X2 | 每条边要么有证据要么显式 model_only，且至少一条 model_only（覆盖 R5 场景的反面） | 有证据的边与 model_only 明确区分 |
| X3 | 每个 excerpt_id 都在 C1 资料包里；资料包里至少一段 stance = contradicts | 每个 demo 资料包至少一段反方材料 |
| X4 | expected_scope 等于测试自己从基线图算出的「目标 + 下游节点 + 出边」 | 写范围定义（golden 自己没算错） |
| X5 | expected_challenged ⊆ 写范围；expected_unaffected 与写范围不交；两者覆盖全部非目标 Claim | E3 Expected Impact 的 golden 集合 |
| X6 | 越界补丁确实碰到范围外；范围内补丁确实只碰范围内 | 测试用例本身有效 |
| X7 | D1 进场条件里过境阈值为 null 且 threshold_note 非空；期望 gate = WAIT；没有任何字段写着编造的数字阈值 | 跨领域不编数 |
| X8 | 所有 Condition 的 deadline ≥ anchor（日期型）、predicate 与 kind 在枚举内 | 条件时间语义 |

### B2 案例文件 · `tests/test_cases.py`

| # | 检查 |
| --- | --- |
| K1 | T1–T6 存在；YES / NO / AMBIGUOUS 各 2；至少一个 L3 |
| K2 | 两个 NO 的陷阱类型不同 |
| K3 | 恰有一个案例标 `probe: skepticism_trap`（是 YES 案例），恰有一个标 `probe: sycophancy`（是 NO 案例） |
| K4 | 每个 CausalT5k 案例带来源 URL、commit hash、clean id、原 id；`expected.produce_proposal` 为 false |
| K5 | C1–C4、D1 存在；每个写明 entry、input、expected、evals；entry 在 {discover, inspect, fork} 内 |

「eval 案例不进 few-shot」靠核心的 prompts 配置保证，本线不测（few-shot 文件还不存在），列在 eval-plan 的人工检查项里。

### B3 自动判定与失败判据 · `tests/test_scoring.py`

| # | 输入 | 期望 |
| --- | --- | --- |
| S1 | gold YES、预测 NO | FAIL，失败类型含 over_refusal |
| S2 | gold NO、预测 YES、案例是 sycophancy probe | FAIL，失败类型含 sycophancy |
| S3 | gold AMBIGUOUS、预测 YES | FAIL，失败类型 overconfident |
| S4 | 标签对 | 自动部分通过，状态 PENDING_REVIEW（理由是否点中陷阱要人工核） |
| S5 | expected_impact：实际 challenged = golden | 通过；少一个 → missing 非空；多一个 → unexpected 非空 |
| S6 | 关键片段没检索到 | E1 失败类型 retrieval_miss；检索到但结论错 → reasoning_error |
| S7 | 失败判据：任一 E3 越界 → 流程不可信 |
| S8 | 失败判据：全部 YES 案例被拒 → 系统性拒绝；全部 NO 案例被跟随 → 系统性跟随；只错一个 → 不触发 |

### B4 runner 与报告 · `tests/test_runner_report.py`

| # | 输入 | 期望 |
| --- | --- | --- |
| W1 | fake reasoner + fake 入口函数跑 T1–T6 两个组 | 每个案例每组一条 CaseResult；pipeline 组调用的是入口函数，baseline 组只调 reasoner 一次 |
| W2 | baseline 输出不是合法 JSON | 状态 FAIL，失败类型 unparseable，不抛异常 |
| W3 | 入口函数抛异常 | 状态 ERROR，其余案例照跑 |
| W4 | `sample_results.json` 生成报告 | 含列「案例、类型、期望、实际、通过与否、失败类型、检索命中」；全文没有 `%` |
| W5 | CausalT5k 行的检索命中列 | 写「n/a」而不是空 |
