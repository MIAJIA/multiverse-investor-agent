# Catalyst（multiverse-investor-agent）

面向散户交易者的研究工具：用户输入一个事件，系统给出因果图和一份条件式交易提案（draft，永不执行）；用户可以改一个假设做分叉，看哪些前提受到挑战。面试 take-home，产品与架构以 `docs/prd.md`、`docs/engineering-design.md` 为准（Claude Docs 在线版的导出快照），实现层的决定记在 `docs/core-design.md`。

## 一条原则

**模型提议，代码裁决。** 模型只经 `catalyst/reasoner.py` 进入，只能提出因果假设、机制、条件和解释。下面这些只由代码写，任何改动都不能把它们交给模型：
- gate、提案的 status 与 support_status、版本号；
- 条件判定（evaluation_status）；
- 分叉的写范围，以及范围外 claim 的 assessment；
- diff；
- 用户判断里的 confirmed、confirmed_claim_ids、probability。

## 数据契约

**唯一来源是 `catalyst/schema.py`**，UI、eval、harness 都不另起一份。

- 快照、API、diff 和哈希一律用 `.dump()` 的规范形式：字段齐全，含默认值。
- 改字段时，下面几处要一起改：
  - `web/src/types.ts`（TS 镜像，字段名一字不改）；
  - `eval/INTERFACE.md`；
  - 需要的话，`eval/fixtures/` 和 `tests/_adapter.py`。
- 模型输出的形状是 `*Output` 和 `ProposalDraft`。它们故意比持久化对象少字段，凡是由代码裁决的字段都不在里面。
- 图快照不可变。批准（接口名仍是 sign）和分叉（fork）都产出新版本，不覆盖旧版本。
- **Plan B — competing branches, one plan per terminal** (`docs/changes/2026-10-18-branches-and-plans.md`):
  - The version bundle `VersionBundle` is `{graph, proposals, branches, node_kinds, edge_kinds, scenario, diff, excerpts}`. There is **no** `proposal` field. inspect / fork / sign results also carry a `proposals` list (`[]` when there are none).
  - `proposals` follow the graph's terminal order. Each has a `terminal_id`, and `meta.proposal_version = "{graph_version}.{terminal_id}"`. `parse_proposals` reads a legacy single-dict file as a one-item list.
  - `catalyst/branches.py` (`derive_views`) derives the following; kinds are decided by code, never by the model:
    - `branches`: `{terminal_id, divergence_node_ids, own_node_ids, own_edge_ids, kind, trunk, synthetic_evidence}`;
    - the lookup tables `node_kinds: {node_id: kind}` and `edge_kinds: {edge_id: kind}`, with kind one of hypothetical / evidenced / model_only.
  - Approval:
    - approved means `user_judgment.confirmed`, and at most one plan per version is approved;
    - `sign` with `terminal_id: null` approves none (no trade);
    - `user_judgment.note` is written by the user only.
  - `approval_reset` and `rival_changed` are written by fork only. They describe what changed relative to the parent version and are never inherited.
  - `validator.validate_plans` blocks unless:
    - the plans' terminals are exactly the graph's terminals;
    - each instrument belongs to its plan's terminal;
    - every plan carries the same `original_statement` / `clarified_statement`.

## 目录与归属

| 目录 | 内容 | 归属 |
| --- | --- | --- |
| `catalyst/` | 核心：schema、validator、conditions、gate、fork、diff、store、reasoner、harness、entrypoints、prompts、api、CLI | 核心线 |
| `catalyst/evidence.py` | Evidence Provider 与 BM25 `search()` | 证据线（schema 不归证据线） |
| `packs/` | 真实资料包（EvidencePack），每段可回溯到来源 | 证据线 |
| `eval/`、`tests/`（`tests/core/`、`tests/evidence/` 除外） | 案例、golden fixture、runner、报告、eval 测试 | eval 线 |
| `tests/core/` | 核心回归测试 | 核心线 |
| `tests/evidence/` | 资料包测试 | 证据线 |
| `web/`、`docs/frontend/` | 前端（Vite + React + @xyflow/react），单页三个标签共用一份 state | 前端线 |
| `fixtures/` | 由 `python -m catalyst promote` 从真实录制生成的共享 fixture | 不手写 |

**并行工作的规矩**：每条线在自己的 git worktree 和分支上工作，只改自己的文件，不推送；合并由主 session 统一做，合并后跑全套测试。

## 怎么跑

```bash
.venv/bin/python -m pytest -q                       # 核心 + eval + 证据，全部离线
cd web && npm test && npm run typecheck && npm run build
.venv/bin/python web/scripts/check_fixtures.py      # 前端 fixture 符合 schema
```

```bash
set -a && . ./.env && set +a                        # 读入 API key（.env 永不提交）
.venv/bin/python -m catalyst run D1 --live          # 跑一个案例：录音 + 快照写到 runs/D1/<时间戳>/
.venv/bin/python -m catalyst run D1 --replay runs/D1/<ts>   # 零成本、确定性回放
.venv/bin/python -m catalyst run <case.json> --live --online   # 先在白名单网站联网检索（config/web_whitelist.json），冻结成资料包再推理；默认关，回放不上网
.venv/bin/python -m catalyst promote runs/D1/<ts> d1        # 提升成 fixtures/d1.json
.venv/bin/python -m eval.runner --record eval/out/<name>    # 全部案例 × pipeline / baseline 两组，出逐例报告
.venv/bin/python -m catalyst.api                    # 前端用的 HTTP 接口，http://localhost:8000
cd web && VITE_MOCK=0 npm run dev                   # 前端接真实后端（默认 VITE_MOCK=1 读 fixture）
```

- 模型：`CATALYST_MODEL`，默认 `claude-opus-5-5`；调试可以用 `claude-haiku-5-5`。effort 用 `CATALYST_EFFORT` 设置。联网检索这一步单独用 `CATALYST_WEB_MODEL`，默认 `claude-haiku-5-5`（立场标注和推理仍用 `CATALYST_MODEL`）。
- 回放按请求哈希匹配。prompt、资料包、schema 或输入任何一项变了，旧录音都会报 `CassetteMiss`。改了 prompt 要提升 `PROMPT_VERSION`。

## 不要做的事

- 不要手写图层面的 fixture。期望可以由人写（gate 应是什么、哪些 claim 应受挑战），图要从真实录制里提升出来。
- 不要为了让某个 eval 案例通过去调 prompt；few-shot 不得包含 eval 案例。
- 不要让代码静默改写模型的输出。校验不过，就把带对象 id 的错误回给模型重写。
- 资料包不收回溯不到来源的内容，也不编数字或日期。
- 不要提交 `.env`、`runs/`、`web/node_modules/`。
