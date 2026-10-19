# eval 对核心包的接口提议

> 2026-10-18 更新：核心已在 `core-schema` 分支落地（commit 64024cc），决定记录在 `docs/core-design.md`。D1、D3–D9 按本文默认采纳，D2 改判 met（已同步）；E3 哈希比对前两边先经 `parse_graph(d).dump()` 规范化。下文保留提议原文，与实现不同处以核心为准。

2026-10-18 · eval 线 → 主 session

这是**提议**，不是规格。主 session 照着实现，或者直接改这份文件；改了之后 eval 线只需要改 `tests/_adapter.py`（测试侧唯一 import catalyst 的地方）和 `eval/runner.py` 的 `load_core_entrypoints()`（runner 侧唯一 import catalyst 的地方）。字段名一律沿用 `docs/engineering-design.md`「核心数据模型」；设计文档没写到、本线需要的字段在下文标「新增」。

## 1. 数据表示

- 核心函数**接受普通 dict**（JSON 反序列化的结果），返回 dict 或带 `to_dict()` / `model_dump()` 的对象都可以，adapter 会归一。如果核心用 pydantic / dataclass，请提供 `catalyst.schema.parse_graph(dict)`、`parse_condition(dict)`，adapter 会自动用上。
- 日期在数据里是 ISO 字符串 `YYYY-MM-DD`；`now` 参数是 `datetime.date`。
- 枚举值是小写字符串（`met`、`not_met`、`unknown`、`supported` …）；gate 结果是大写字符串（`WAIT`、`BLOCKED`、`READY_FOR_REVIEW`）。返回 `Enum` 也行，adapter 取 `.value`。

## 2. 函数

| 函数 | 签名 | 行为要求（测试会查的） |
| --- | --- | --- |
| 进场判定 | `catalyst.gate.evaluate_entry(conditions: list[Condition]) -> "WAIT" \| "BLOCKED" \| "READY_FOR_REVIEW"` | AND；任一 not_met → BLOCKED；否则任一 unknown → WAIT；空集 → WAIT；全 met → READY_FOR_REVIEW；只看 evaluation_status，verification_status = verifiable 不算满足 |
| 条件判定 | `catalyst.conditions.evaluate(condition, observations: list[Observation], now: date) -> "met" \| "not_met" \| "unknown"` | not_observed_by：`now > observation_window.end` 且某个同源 observation 的 coverage 覆盖整个窗口、窗口内无记录 → met；窗口内有记录 → not_met；其余 unknown（决定 D2）；threshold 为 null 时数值条件永远 unknown |
| Condition 校验 | `catalyst.validator.validate_condition(condition) -> list[Error]` | numeric 且 threshold 为 null 时 threshold_note 必须非空；anchor、deadline 都是日期时 deadline ≥ anchor；anchor 以 `scenario:` 开头时跳过日期比较；predicate、kind 在枚举内 |
| 引用校验 | `catalyst.validator.validate_references(graph, evidence_pack) -> list[Error]` | excerpt_id 必须存在于**当前** pack；`model_only: true` 的边不得带 stance = supports 的证据；evidence_status = supported 的 Claim 必须至少有一条非 model_only 的入边带 supports 证据 |
| 写范围 | `catalyst.fork.compute_write_scope(graph, op) -> (node_ids: set[str], edge_ids: set[str])` | 见决定 D4 |
| 打补丁 | `catalyst.fork.apply_patch(graph, patch, scope) -> Graph` | 返回新版本：`version` 新值、`parent_version` = 基线 version；**不原地修改**输入图；越界抛 `catalyst.fork.ScopeViolation`，且不留半截写入 |
| diff | `catalyst.diff.diff(g1, g2) -> dict` | 至少含 `nodes_changed`、`edges_changed`、`conditions_changed`、`nodes_added`、`edges_added`、`nodes_removed`、`edges_removed`（id 列表或集合） |
| 案例入口 | 见第 4 节 | |

`Error` 可以是字符串或对象，但 `str(error)` 必须包含出错的 node / edge / condition / excerpt id——测试用这个定位。

## 3. 字段（新增标注）

- **node**（Claim）：`id`、`statement`、`original_statement`、`evidence_status`、`time_bucket`、`instruments`；新增 `role`：event / assumption / intermediate / terminal / shock（定位 ChangeAssumption 目标、AddShock 新节点用）。
- **edge**（Mechanism）：新增 `id`（写范围按 id 记边）；`from`、`to`、`channel`、`sign`（`+` / `-`）、`lag_days`、`mechanism`、`evidence: [{tier, source_id, excerpt_id, stance, supports}]` 或 `model_only: true`；stance = contradicts 的证据新增可选 `rebuttal`（说明为什么不构成反驳；没有 rebuttal 的 contradicts 证据才推进 Claim 为 contradicted，见决定 D8）。
- **channel 枚举**（提议）：adoption、capex、demand、supply、price、substitution、technology、policy、revenue、sentiment。
- **condition**：新增 `id`；其余照设计文档：`claim_id`、`kind`、`predicate`、`series`、`source`、`comparator`、`threshold`、`threshold_note`、`anchor`、`deadline`、`observation_window: {start, end}`、`rule`、`verification_status`、`evaluation_status`。
- **graph**：`version`、`parent_version`、`op`、`nodes`、`edges`、`model_output_ref`、`observations_ref`；新增 `conditions`（挂在图上，Fork 的「相关 Condition 变更一律拒绝」才能按图快照比对）。
- **op**：`{kind, target, value}`；AddShock 额外带 Stage 1 结果 `impacts: [node_id]`、`new_nodes: [node]`、`new_edges: [edge]`（三小时由代码查预定义表填）。
- **patch**（新增）：`{base_version, node_updates: [{id, fields}], edge_updates: [{id, fields}], condition_updates: [{id, fields}], node_adds: [node], edge_adds: [edge], assessment: {claim_id: unaffected|challenged|unresolved}}`。
- **observation**（新增）：`{source, coverage: {start, end}, records: [{date, value, excerpt_id}]}`；`source` 与 condition 的 `series` 或 `source` 匹配；`coverage` 是来源实际覆盖到的区间。
- **evidence pack**：`{pack_id, excerpts: [{source_id, excerpt_id, source, date, text, stance}]}`。

## 4. 案例入口（runner 用）

都放在 `catalyst.entrypoints`（或主 session 指定的模块），Reasoner 与 Evidence Provider 注入：

```python
discover(event: str, target: str | None = None, *, reasoner, evidence, config=None) -> {
    "candidates": [{"id", "direction", "label": "grounded" | "hypothesis" | "not_recommended", "rationale"}],  # 0–3 个
    "abstained": bool, "abstain_reason": str | None,
    "observations": [excerpt_id],          # 本轮检索到的全部片段 id（进快照的 observations_ref）
}
inspect(event: str, target: str | None = None, *, candidate_id=None, material: str | None = None,
        judgment_only: bool = False, reasoner, evidence, config=None) -> {
    "graph": Graph | None, "no_chain": bool, "no_chain_reason": str | None,
    "proposal": TradeProposal | None,      # judgment_only=True 时必须为 None
    "judgment": {"label": "YES" | "NO" | "AMBIGUOUS", "rationale": str} | None,   # judgment_only=True 时必填
    "observations": [excerpt_id],
}
fork(graph, op, *, reasoner, evidence, config=None) -> {
    "graph": Graph,                        # 新版本
    "base_graph": Graph,                   # 原版本（必须仍可取到）
    "scope": {"nodes": [...], "edges": [...]},
    "diff": {...},                         # catalyst.diff.diff 的结果
    "scenario": {"version", "base_version", "ops", "assessment": {claim_id: status}},
    "proposal": TradeProposal | None,
}
```

TradeProposal 至少要有 `entry_conditions`、`support_status`、`meta.approval_required`、`user_judgment`，以及 adapter 读 gate 结果用的 `gate`（`evaluate_entry(entry_conditions)` 的结果，提议作为派生字段直接放进提案）。

runner 的 CLI 另外需要 `catalyst.reasoner.default_reasoner()`（返回的对象还要有 `single_prompt(prompt: str) -> str`，baseline 组用同一个模型做单次 prompt）和 `catalyst.evidence.default_provider()`（要有 `load_pack(pack_id) -> list[excerpt]`，baseline 组把同一份资料全文拼进 prompt）。

`judgment_only=True` 是给 CausalT5k 的：scenario 作为 `material` 直接给出，只输出因果判断，不生成提案。

## 4b. runner 实际怎么调核心（对齐后）

- 三个入口都传 `packs=<本案例可用的 pack>`。pack 列表由 `eval.runner.prepare_packs` 算：真实 pack 优先；还没交付时用 `EvidenceProvider.register` 注入 `eval/fixtures` 里同 pack_id 的合成包，并在结果的 `notes` 里写明；不存在的 pack（如 `web`）两个组都不带。baseline 组的 prompt 用同一份列表，保证「同一资料」。
- Discover 之后的 inspect 传 `candidate=<整个候选 dict>`（同时带 `candidate_id`）。
- fork 传 `packs`，不传 `pack`；E3 哈希的基线取核心回传的 `base_graph`（已是规范形式），不直接哈希手写 fixture。
- 入口返回 `ok=False` 时记 `structured_failure`，附核心给的 errors。
- baseline 组优先调 `reasoner.single_prompt(prompt)`；reasoner 没有这个方法时退回 `complete(stage="baseline", system="", user=prompt, schema={"type": "object"})`。

## 5. 需要主 session 决定的问题

| # | 问题 | 本线的默认（测试按它写） | 改了要动哪里 |
| --- | --- | --- | --- |
| D1 | edge / condition 的 `id`、graph 上的 `conditions`、node 的 `role` 是否加进 schema | 加 | fixture 全部 |
| D2 | not_observed_by 在「窗口结束 + 来源全覆盖 + 窗口内无记录」时给什么 | **已定（主 session，docs/core-design.md）：met。** evaluation_status 回答「条件是否成立」，「到期未发生」此时成立；窗口内看到记录给 not_met；其余一律 unknown。设计文档原文写的 not_met 待同步 | `eval/fixtures/condition_cases.json` 的 T3 `expected` |
| D3 | 进场条件里 unknown 与 not_met 同时出现时 | BLOCKED（已证实未满足优先） | `gate_truth_table.json` 的 G6 |
| D4 | 写范围的边怎么算：ChangeAssumption = 目标 + 全部后代节点 + **这些节点的出边**；指向后代节点、但起点在范围外的入边（如 C1 的 `c1.e3`）**不在**范围内。AddShock = Stage 1 新节点与新边 + `impacts` 及其后代 + 这些节点的出边 | 如左 | `c3_*.json` 的 expected_scope；`tests/test_fixtures.py` 里的参考实现 |
| D5 | patch 格式、`assessment` 放在 patch 里由模型提议还是由代码从 diff 推出 | 放在 patch 里，代码只接受范围内的 claim | `c3_*.json` |
| D6 | CausalT5k 的 Skepticism Trap 与谄媚陷阱怎么落到案例：数据集里它们是诊断的失败模式（P1、P2），不是逐例的 `trap` 字段 | T1 = 看似陷阱、实则成立的 YES 案例（Natural Experiment）；T4 = NO 案例 + 用户确定语气的加压句 | `eval/cases/causalt5k/` |
| D7 | 非数值条件 threshold 为 null 时是否也必须写 threshold_note | 只强制 numeric；fixture 里非数值条件也写了说明 | `condition_cases.json` |
| D8 | contradicts 证据「被驳回」用什么字段表示 | 可选 `rebuttal` 文本 | `c1_graph_v1.json` 的 `c1.e4` |
| D9 | 在线搜索 pack 在哪个案例里开着演示 | C2 | `eval/cases/C2.json` |
