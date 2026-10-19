# Eval 脚手架 · 实现计划

2026-10-18 · eval 线（分支 `eval-scaffold`）

依据：`docs/engineering-design.md`「核心数据模型」「Agent loop 与 harness」「可验证：Eval 设计」「三小时映射」「验收清单」；`docs/prd.md` 主文。字段名一律沿用设计文档；设计文档没定的地方在 [`eval/INTERFACE.md`](../../eval/INTERFACE.md) 里写成提议，由主 session 确认或改。

## 边界

- 本线只拥有 `eval/`、`tests/`、`docs/eval/`、根目录 `requirements-dev.txt`。不创建、不修改 `catalyst/`，不改两份设计文档。
- 不真实调用模型，不读任何 API key。Reasoner 一律注入，测试用 fake。
- 「模型提议，代码裁决」在 eval 里的对应：能由代码裁决的（E3 Non-interference、进场真值表、条件时间语义、引用存在）写成确定性测试；不能由代码裁决的（E1 因果是否成立、E2 条件是否有意义、E4 的理由是否点中陷阱）进人工复核表，不交给 LLM judge。

## 目录结构

```
eval/
  INTERFACE.md          对核心包的接口提议（函数签名、字段、错误类型）
  __init__.py
  loader.py             读案例与 fixture（纯 JSON，不 import catalyst）
  scoring.py            自动判定：标签比对、E3 Expected Impact 集合比对、检索命中、失败类型、失败判据
  runner.py             两个组：pipeline / baseline；Reasoner、Evidence、入口函数全部可注入
  report.py             逐例 markdown 报告（不报百分比）
  fakes.py              fake reasoner / evidence / 核心入口（测试与 sample_results 用）
  review_sheet.md       E1 / E2 / E4 人工复核表模板
  sample_results.json   假结果，只用来验证报告生成器
  cases/
    causalt5k/T1.json … T6.json   CausalT5k D3 原样摘录 + 本项目的期望行为
    causalt5k/SOURCE.md           来源 URL、commit hash、选例规则、数据质量备注
    C1.json C2.json C3.json C4.json D1.json   自建案例规格
  fixtures/
    c1_graph_v1.json              C1 基线图（golden）
    c1_evidence_pack.json         C1 图引用的半导体片段（手写占位，结构测试用）
    c3_change_assumption.json     ChangeAssumption：op、期望写范围、范围内 / 越界补丁、应受挑战集合
    c3_add_shock.json             预定义 AddShock：Stage 1 查表结果、期望写范围、补丁、应受挑战集合
    d1_hormuz.json                D1：Hormuz 小包占位片段 + 提案进场条件（阈值 null + 说明）+ 期望 WAIT
    gate_truth_table.json         进场 AND 真值表
    condition_cases.json          条件时间语义与 Condition 校验用例
    reference_cases.json          Reference Validator 用例
  cases/causalt5k/extract.py      从固定 commit 的 CausalT5k 下载里原样摘出 T1–T6
tests/
  conftest.py           把仓库根加进 sys.path
  _graph.py             测试侧图工具：规范化哈希、写范围参考实现（不 import catalyst）
  _adapter.py           唯一 import catalyst 的地方；catalyst 不存在时 importorskip
  test_gate.py          进场真值表、verifiable ≠ met（依赖核心）
  test_conditions.py    not_observed_by 时间语义、null 阈值、deadline ≥ anchor（依赖核心）
  test_fork.py          E3 Non-interference：写范围、越界拒绝、哈希不变、基线仍在（依赖核心）
  test_validator.py     Reference Validator（依赖核心）
  test_fixtures.py      golden fixture 自洽（不依赖核心）
  test_cases.py         案例文件与 CausalT5k 选例规则（不依赖核心）
  test_scoring.py       自动判定与失败判据（不依赖核心）
  test_runner_report.py fake reasoner 跑 runner、假结果跑报告（不依赖核心）
  test_runner_core.py   ScriptedReasoner + 真实核心入口跑 T1–T6、C3、C4：runner 与核心的契约（依赖核心）
docs/eval/
  implementation-plan.md  test-plan.md  eval-plan.md  step-by-step.md
requirements-dev.txt      pytest
```

## 模块职责

| 模块 | 职责 | 不做什么 |
| --- | --- | --- |
| `eval/loader.py` | 读 `cases/` 与 `fixtures/` 的 JSON，返回 dict；列出全部案例 | 不做校验逻辑（校验在测试和核心） |
| `eval/scoring.py` | 纯函数：`judge_label`、`expected_impact`、`retrieval_hit`、`classify_e1_failure`、`failure_criteria` | 不判断因果是否成立；不调模型 |
| `eval/runner.py` | `run_case(case, group, reasoner, evidence, entrypoints)` → `CaseResult`；pipeline 组走 `discover / inspect / fork`，baseline 组把同一资料拼成一次 prompt 交给同一个 reasoner；捕获异常记为 ERROR | 不 import catalyst 的顶层；入口函数由调用方注入，只在 CLI 里懒加载 |
| `eval/report.py` | `render_report(results)` → markdown：每组一张逐例表 + 两组对照表 + 失败判据结论 + 待复核清单 | 不算百分比、不算平均分 |
| `tests/_adapter.py` | 把核心的返回值归一成测试需要的形状（字符串枚举、集合、错误列表）；核心字段变化只改这里 | 不实现任何核心逻辑 |

## 对核心包的依赖（摘要，详见 `eval/INTERFACE.md`）

| 依赖 | 用在 |
| --- | --- |
| `catalyst.gate.evaluate_entry(conditions) -> "WAIT" / "BLOCKED" / "READY_FOR_REVIEW"` | test_gate |
| `catalyst.conditions.evaluate(condition, observations, now) -> "met" / "not_met" / "unknown"` | test_conditions |
| `catalyst.validator.validate_condition(condition) -> list[error]` | test_conditions（null 阈值说明、deadline ≥ anchor） |
| `catalyst.validator.validate_references(graph, evidence_pack) -> list[error]` | test_validator |
| `catalyst.fork.compute_write_scope(graph, op) -> (node_ids, edge_ids)` | test_fork |
| `catalyst.fork.apply_patch(graph, patch, scope) -> Graph`，越界抛 `catalyst.fork.ScopeViolation` | test_fork |
| `catalyst.diff.diff(g1, g2)` | test_fork、runner（C3） |
| 入口：`discover(event, target=None, ...)`、`inspect(...)`、`fork(...)` | runner pipeline 组 |

## 数据文件格式

所有 fixture 与案例都是 UTF-8 JSON，字段名用设计文档原词。

**Graph**（`c1_graph_v1.json`）：`version`、`parent_version`、`op`、`nodes`、`edges`、`conditions`、`model_output_ref`、`observations_ref`。
- node（Claim）：`id`、`statement`、`original_statement`、`evidence_status`（supported / contradicted / unknown）、`time_bucket`、`instruments`（只有终点有）；额外 `role`（event / assumption / intermediate / terminal，提议字段，方便定位 ChangeAssumption 的目标）。
- edge（Mechanism）：`id`（提议字段，写范围要用）、`from`、`to`、`channel`、`sign`、`lag_days`、`mechanism`、`evidence: [{tier, source_id, excerpt_id, stance, supports}]` 或 `model_only: true`。
- condition：`id`（提议字段）、`claim_id`、`kind`、`predicate`、`series` 或 `source`、`comparator`、`threshold`、`threshold_note`、`anchor`、`deadline`、`observation_window: {start, end}`、`rule`、`verification_status`、`evaluation_status`。

**Evidence Pack**：`{pack_id, synthetic, excerpts: [{source_id, excerpt_id, source, date, text, stance}]}`。fixture 里的片段文本是手写占位（`synthetic: true`），只用于结构测试；真实 Semiconductor Pack 与 Hormuz 小包由证据线交付。

**Op**：`{kind: change_assumption | add_shock, target, value}`；AddShock 额外带 Stage 1 查表结果 `impacts`（既有节点 id）与 `new_edges`、`new_nodes`。

**Patch**（提议）：`{base_version, node_updates: [{id, fields}], edge_updates: [{id, fields}], condition_updates: [{id, fields}], node_adds: [...], edge_adds: [...]}`。

**Observations**（提议，条件判定用）：`[{source, coverage: {start, end}, records: [{date, value, excerpt_id}]}]`。`coverage` 是来源实际覆盖到的区间，用来判断「窗口已结束且来源覆盖该窗口」。

**案例文件**：`{id, type, title, entry, input, material, expected, evals, auto_checks, human_review, notes}`；CausalT5k 案例另带 `source`（原样摘录 + clean id + 原 id + commit）。

**CaseResult**（runner 输出 / report 输入）：`{case_id, group, case_type, expected, actual, status: PASS | FAIL | PENDING_REVIEW | ERROR, failure_types: [...], retrieval: {expected, retrieved, hit} | null, checks: [{name, eval, passed, detail}], human_review: [...]}`。

## 运行方式

```
python -m eval.runner --group pipeline --group baseline --out eval/out/results.json   # 需要核心与真实 reasoner，本线不跑
python -m eval.report eval/sample_results.json > eval/out/sample_report.md            # 本线可跑
pytest -q
```
