# 执行步骤（eval 线）

做完一步勾一步。工作目录 `~/Downloads/multiverse-investor-agent-eval`，分支 `eval-scaffold`，只 commit 不 push。

## 0. 准备
- [x] clone 仓库，建分支 `eval-scaffold`
- [x] 读 `docs/engineering-design.md` 全文与 `docs/prd.md` 主文
- [x] 找到 CausalT5k 公开仓库，固定 commit，下载 `final_dataset/clean/` 与 `final_dataset/D3/`（放在仓库外的临时目录）

## 1. 计划
- [x] `docs/eval/implementation-plan.md`
- [x] `docs/eval/test-plan.md`
- [x] `docs/eval/eval-plan.md`
- [x] `docs/eval/step-by-step.md`
- [x] commit：计划

## 2. 接口与适配层
- [x] `eval/INTERFACE.md`：每个核心函数与字段的提议 + 需要主 session 决定的问题
- [x] `tests/_adapter.py`：唯一 import catalyst 的地方，catalyst 不存在时 importorskip
- [x] `tests/conftest.py`、`requirements-dev.txt`

## 3. Fixture 与 golden case
- [x] `c1_graph_v1.json` + `c1_evidence_pack.json`（含反方片段、含一条 model_only 边）
- [x] `c3_change_assumption.json`：op、期望写范围、范围内补丁、三种越界补丁、应受挑战集合
- [x] `c3_add_shock.json`：Stage 1 查表结果、期望写范围、范围内补丁、未识别新边补丁、应受挑战集合
- [x] `d1_hormuz.json`：阈值 null + 说明，期望 WAIT
- [x] `gate_truth_table.json`、`condition_cases.json`、`reference_cases.json`

## 4. 确定性测试
- [x] `test_gate.py`、`test_conditions.py`、`test_fork.py`、`test_validator.py`（依赖核心，现在跳过）
- [x] `test_fixtures.py`、`test_cases.py`（不依赖核心，必须通过）

## 5. 案例
- [x] CausalT5k 按规则选 T1–T6，原样摘录进 `eval/cases/causalt5k/`，`SOURCE.md` 记来源 URL、commit、选例规则、数据质量备注
- [x] C1、C2、C3、C4、D1 案例文件

## 6. Runner 与报告
- [x] `eval/scoring.py`（自动判定、E3 Expected Impact、检索命中、失败判据）
- [x] `eval/runner.py`（pipeline / baseline 两组，reasoner 可注入）
- [x] `eval/report.py` + `eval/sample_results.json`
- [x] `eval/review_sheet.md`
- [x] `test_scoring.py`、`test_runner_report.py`

## 7. 收尾
- [x] `pytest` 全部通过或干净跳过，记录数量：35 passed、4 skipped（4 个依赖核心的测试文件整体跳过）；另用仓库外的临时 stub 核心验证依赖核心的测试本身可跑：72 passed，故意去掉范围检查后 7 failed
- [x] 本文件全部勾选
- [x] commit：实现
- [x] 在共享笔记目录留交接说明

## 8. 与核心对齐（核心 core-schema@64024cc）
- [x] D2 改判 met：`condition_cases.json` T3 → met，新增 T7（窗口内有记录 → not_met）；INTERFACE.md、test-plan 同步
- [x] E3 哈希先规范化：`tests/_graph.element_hashes(graph, normalize=...)`，test_fork 两边都过 `_adapter.canonical_graph`（`parse_graph(d).dump()`）
- [x] runner：三个入口都传 `packs`；资料包未交付时注入合成包；Discover 之后传 `candidate=pick`；fork 用核心回传的 `base_graph` 做哈希基线；`ok=False` 记 structured_failure；baseline 用同一份 pack 列表
- [x] fakes：没有输出 confirmed / confirmed_claim_ids / probability，无需删；新增实现 `complete` 协议的 ScriptedReasoner
- [x] `tests/test_runner_core.py`：runner 对真实核心入口的契约测试
- [x] 测试：有核心 84 passed；无核心 35 passed、5 skipped（Python 3.9 / 3.14）
- [x] commit（不 push）
