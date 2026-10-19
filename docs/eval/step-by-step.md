# 执行步骤（eval 线）

做完一步勾一步。工作目录 `~/Downloads/multiverse-investor-agent-eval`，分支 `eval-scaffold`，只 commit 不 push。

## 0. 准备
- [ ] clone 仓库，建分支 `eval-scaffold`
- [ ] 读 `docs/engineering-design.md` 全文与 `docs/prd.md` 主文
- [ ] 找到 CausalT5k 公开仓库，固定 commit，下载 `final_dataset/clean/` 与 `final_dataset/D3/`（放在仓库外的临时目录）

## 1. 计划
- [ ] `docs/eval/implementation-plan.md`
- [ ] `docs/eval/test-plan.md`
- [ ] `docs/eval/eval-plan.md`
- [ ] `docs/eval/step-by-step.md`
- [ ] commit：计划

## 2. 接口与适配层
- [ ] `eval/INTERFACE.md`：每个核心函数与字段的提议 + 需要主 session 决定的问题
- [ ] `tests/_adapter.py`：唯一 import catalyst 的地方，catalyst 不存在时 importorskip
- [ ] `tests/conftest.py`、`requirements-dev.txt`

## 3. Fixture 与 golden case
- [ ] `c1_graph_v1.json` + `c1_evidence_pack.json`（含反方片段、含一条 model_only 边）
- [ ] `c3_change_assumption.json`：op、期望写范围、范围内补丁、三种越界补丁、应受挑战集合
- [ ] `c3_add_shock.json`：Stage 1 查表结果、期望写范围、范围内补丁、未识别新边补丁、应受挑战集合
- [ ] `d1_hormuz.json`：阈值 null + 说明，期望 WAIT
- [ ] `gate_truth_table.json`、`condition_cases.json`、`reference_cases.json`

## 4. 确定性测试
- [ ] `test_gate.py`、`test_conditions.py`、`test_fork.py`、`test_validator.py`（依赖核心，现在跳过）
- [ ] `test_fixtures.py`、`test_cases.py`（不依赖核心，必须通过）

## 5. 案例
- [ ] CausalT5k 按规则选 T1–T6，原样摘录进 `eval/cases/causalt5k/`，`SOURCE.md` 记来源 URL、commit、选例规则、数据质量备注
- [ ] C1、C2、C3、C4、D1 案例文件

## 6. Runner 与报告
- [ ] `eval/scoring.py`（自动判定、E3 Expected Impact、检索命中、失败判据）
- [ ] `eval/runner.py`（pipeline / baseline 两组，reasoner 可注入）
- [ ] `eval/report.py` + `eval/sample_results.json`
- [ ] `eval/review_sheet.md`
- [ ] `test_scoring.py`、`test_runner_report.py`

## 7. 收尾
- [ ] `pytest` 全部通过或干净跳过，记录数量
- [ ] 本文件全部勾选
- [ ] commit：实现
- [ ] 在共享笔记目录留交接说明
