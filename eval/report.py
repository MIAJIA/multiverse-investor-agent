"""逐例 markdown 报告。只报个数，不报百分比。

用法：python -m eval.report <results.json> [review.json] > report.md
"""
from __future__ import annotations

import json
import sys
from typing import Any

from eval import scoring
from eval.scoring import get

COLUMNS = ["案例", "类型", "期望", "实际", "通过与否", "失败类型", "检索命中"]
STATUS_TEXT = {"PASS": "通过", "FAIL": "未通过", "PENDING_REVIEW": "待复核", "ERROR": "运行出错", "N/A": "n/a"}
TYPE_TEXT = {"causalt5k": "CausalT5k", "custom": "自建"}


def _cell(text: Any) -> str:
    return str(text if text not in (None, "") else "—").replace("|", "\\|").replace("\n", " ")


def _expected(r: dict) -> str:
    e = r.get("expected") or {}
    parts = []
    if "label" in e:
        parts.append(e["label"] + (f"（{e['trap']}）" if e.get("trap") else ""))
    if e.get("abstain"):
        parts.append("弃权")
    if "gate" in e:
        parts.append(f"gate={e['gate']}")
    return "；".join(parts) or (e.get("behavior") or "")[:60]


def _actual(r: dict) -> str:
    a = r.get("actual") or {}
    if "error" in a:
        return a["error"]
    if "summary" in a:
        return a["summary"]
    if "raw" in a:
        return f"无法解析：{a['raw'][:40]}"
    parts = []
    if a.get("label") is not None or r.get("case_type") == "causalt5k":
        parts.append(str(a.get("label")))
    if "candidates" in a:
        parts.append(f"候选 {a['candidates']} 个" + ("（弃权）" if a.get("abstained") else ""))
    if a.get("no_chain"):
        parts.append("no_chain")
    if a.get("gate"):
        parts.append(f"gate={a['gate']}")
    if "conditions" in a:
        parts.append(f"条件 {a['conditions']} 条")
    return "；".join(parts)


def _retrieval(r: dict) -> str:
    if r.get("case_type") == "causalt5k":
        return "n/a（scenario 全文给定）"
    if r.get("group") == "baseline":
        return "n/a（资料全文进 prompt）"
    ret = r.get("retrieval")
    if ret is None:
        return "n/a（未声明关键片段）"
    text = f"命中 {len(ret['hits'])} / 共 {len(ret['expected'])}"
    return text + (f"，缺 {', '.join(ret['missing'])}" if ret["missing"] else "")


def _failures(r: dict) -> str:
    return "、".join(r.get("failure_types") or []) or "—"


def case_table(results: list[dict]) -> str:
    lines = ["| " + " | ".join(COLUMNS) + " |", "| " + " | ".join("---" for _ in COLUMNS) + " |"]
    for r in results:
        row = [r["case_id"], TYPE_TEXT.get(r.get("case_type"), r.get("case_type")), _expected(r), _actual(r),
               STATUS_TEXT.get(r.get("status"), r.get("status")), _failures(r), _retrieval(r)]
        lines.append("| " + " | ".join(_cell(c) for c in row) + " |")
    return "\n".join(lines)


def comparison_table(results: list[dict]) -> str:
    by_case: dict[str, dict[str, dict]] = {}
    for r in results:
        by_case.setdefault(r["case_id"], {})[r["group"]] = r
    lines = ["| 案例 | 期望 | pipeline | baseline |", "| --- | --- | --- | --- |"]
    for case_id, groups in by_case.items():
        any_r = next(iter(groups.values()))
        cells = []
        for g in ("pipeline", "baseline"):
            r = groups.get(g)
            cells.append("—" if r is None else f"{STATUS_TEXT.get(r['status'], r['status'])}：{_actual(r)}")
        lines.append("| " + " | ".join(_cell(c) for c in [case_id, _expected(any_r), *cells]) + " |")
    return "\n".join(lines)


def _counts(results: list[dict]) -> str:
    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    order = ["PASS", "FAIL", "PENDING_REVIEW", "ERROR", "N/A"]
    return "，".join(f"{STATUS_TEXT[s]} {counts[s]} 个" for s in order if counts.get(s))


def criteria_section(results: list[dict], groups: list[str]) -> str:
    lines = []
    for g in groups:
        c = scoring.failure_criteria(results, g)
        verdict = "**当前流程不可信**" if c["untrustworthy"] else "未触发失败判据"
        lines.append(f"- **{g}**：{verdict}。"
                     f"E3 越界写入：{('、'.join(c['scope_violation_cases']) or '无')}；"
                     f"YES 案例 {c['yes_total']} 个中被拒 {len(c['yes_refused'])} 个"
                     f"{'（系统性拒绝）' if c['systematic_refusal'] else ''}；"
                     f"NO 案例 {c['no_total']} 个中被跟随 {len(c['no_followed'])} 个"
                     f"{'（系统性跟随）' if c['systematic_following'] else ''}。")
    return "\n".join(lines)


def pending_section(results: list[dict]) -> str:
    lines = []
    for r in results:
        if r["status"] == "PENDING_REVIEW":
            lines.append(f"- {r['case_id']}（{r['group']}）：" + "；".join(r.get("human_review") or []))
    return "\n".join(lines) or "- 无"


def check_details(results: list[dict]) -> str:
    lines = []
    for r in results:
        failed = [c for c in r.get("checks", []) if not c["passed"]]
        for c in failed:
            lines.append(f"- {r['case_id']}（{r['group']}）`{c['name']}`［{c['eval']}］：{c.get('detail') or '—'}")
    return "\n".join(lines) or "- 无"


def render_report(results: list[dict], title: str = "Catalyst eval 逐例报告") -> str:
    groups = [g for g in ("pipeline", "baseline") if any(r["group"] == g for r in results)]
    out = [f"# {title}", "",
           "只报个数，不报百分比。十个案例是 POC 的定向测试，不是金融推理能力的统计证明；两个负对照通过只说明这两个案例；"
           "CausalT5k 今年初已公开，模型可能见过，T1–T6 是冒烟测试不是分数。对照组结果来自实际测试，不预设。", ""]
    if any(r.get("fake") for r in results):
        out[2:2] = ["> **这是 fake reasoner 生成的假结果，只用来验证报告生成器，不代表任何模型或流程的表现。**", ""]
    for g in groups:
        rows = [r for r in results if r["group"] == g]
        out += [f"## {g} 组", "", _counts(rows), "", case_table(rows), ""]
    if len(groups) == 2:
        out += ["## 两组对照", "", comparison_table(results), ""]
    out += ["## 失败判据", "", criteria_section(results, groups), "",
            "## 未通过的自动检查", "", check_details(results), "",
            "## 待人工复核", "", pending_section(results), "",
            "失败类型说明：" + "；".join(f"`{k}` {v}" for k, v in scoring.FAILURE_TYPES.items()), ""]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    with open(argv[0], encoding="utf-8") as f:
        results = json.load(f)
    if len(argv) > 1:
        with open(argv[1], encoding="utf-8") as f:
            reviews = {(r["case_id"], r["group"]): r for r in json.load(f)}
        results = [scoring.merge_review(r, reviews[(r["case_id"], r["group"])])
                   if (r["case_id"], r["group"]) in reviews else r for r in results]
    sys.stdout.write(render_report(results))


if __name__ == "__main__":
    main()
