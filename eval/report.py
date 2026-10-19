"""Per-case markdown report. Counts only, never percentages.

Layers are reported separately: the main tables cover A / B / T / W; backtests (R) and probes (P) each get their own
section and are not mixed into the main counts or the failure criteria (except a backtest leak, which is criterion 4).

Usage: python -m eval.report <results.json> [review.json] > report.md
"""
from __future__ import annotations

import json
import sys
from typing import Any

from eval import scoring

COLUMNS = ["Case", "Layer", "Expected", "Actual", "Status", "Failure types", "Key excerpts found"]
STATUS_TEXT = {"PASS": "pass", "FAIL": "fail", "PENDING_REVIEW": "pending review", "ERROR": "error", "N/A": "n/a"}
SEPARATE_LAYERS = ("R", "P")


def _cell(text: Any) -> str:
    return str(text if text not in (None, "") else "-").replace("|", "\\|").replace("\n", " ")


def _layer(r: dict) -> str:
    return r.get("layer") or ("T" if r.get("case_type") == "causalt5k" else "A")


def _expected(r: dict) -> str:
    e = r.get("expected") or {}
    parts = []
    if "label" in e:
        parts.append(e["label"] + (f" ({e['trap']})" if e.get("trap") else ""))
    if e.get("abstain"):
        parts.append("abstain")
    if "gate" in e:
        parts.append(f"gate={e['gate']} per plan")
    return "; ".join(parts) or (e.get("behavior") or "")[:60]


def _actual(r: dict) -> str:
    a = r.get("actual") or {}
    if "error" in a:
        return a["error"]
    if "summary" in a:
        return a["summary"]
    if "raw" in a:
        return f"unparseable: {a['raw'][:40]}"
    parts = []
    if a.get("label") is not None or r.get("case_type") == "causalt5k":
        parts.append(str(a.get("label")))
    if "candidates" in a:
        parts.append(f"{a['candidates']} candidates" + (" (abstained)" if a.get("abstained") else ""))
    if a.get("no_chain"):
        parts.append("no_chain")
    if a.get("plans"):
        parts.append("plans " + ", ".join(f"{x['terminal_id']}={x['gate']}" for x in a["plans"]))
    elif "plans" in a:
        parts.append("0 plans")
    if "conditions" in a:
        parts.append(f"{a['conditions']} conditions")
    if a.get("model_only_edges"):
        parts.append(f"{a['model_only_edges']} model_only edges")
    return "; ".join(parts)


def _retrieval(r: dict) -> str:
    if r.get("case_type") == "causalt5k":
        return "n/a (scenario given in full)"
    if r.get("pack_source") == "synthetic":
        return "n/a (placeholder pack, ids collide with the real pack)"
    if r.get("group") == "baseline":
        return "n/a (whole pack in the prompt)"
    ret = r.get("retrieval")
    if ret is None:
        return "n/a (no key excerpts declared)"
    text = f"{len(ret['hits'])} of {len(ret['expected'])} found"
    return text + (f", missing {', '.join(ret['missing'])}" if ret["missing"] else "")


def _failures(r: dict) -> str:
    return ", ".join(r.get("failure_types") or []) or "-"


def case_table(results: list[dict]) -> str:
    lines = ["| " + " | ".join(COLUMNS) + " |", "| " + " | ".join("---" for _ in COLUMNS) + " |"]
    for r in results:
        row = [r["case_id"], _layer(r), _expected(r), _actual(r),
               STATUS_TEXT.get(r.get("status"), r.get("status")), _failures(r), _retrieval(r)]
        lines.append("| " + " | ".join(_cell(c) for c in row) + " |")
    return "\n".join(lines)


def comparison_table(results: list[dict]) -> str:
    by_case: dict[str, dict[str, dict]] = {}
    for r in results:
        by_case.setdefault(r["case_id"], {})[r["group"]] = r
    lines = ["| Case | Expected | pipeline | baseline |", "| --- | --- | --- | --- |"]
    for case_id, groups in by_case.items():
        any_r = next(iter(groups.values()))
        cells = []
        for g in ("pipeline", "baseline"):
            r = groups.get(g)
            cells.append("-" if r is None else f"{STATUS_TEXT.get(r['status'], r['status'])}: {_actual(r)}")
        lines.append("| " + " | ".join(_cell(c) for c in [case_id, _expected(any_r), *cells]) + " |")
    return "\n".join(lines)


def _counts(results: list[dict]) -> str:
    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    order = ["PASS", "FAIL", "PENDING_REVIEW", "ERROR", "N/A"]
    return ", ".join(f"{STATUS_TEXT[s]}: {counts[s]}" for s in order if counts.get(s))


def criteria_section(results: list[dict], groups: list[str]) -> str:
    lines = []
    for g in groups:
        c = scoring.failure_criteria(results, g)
        verdict = "**the pipeline cannot be trusted**" if c["untrustworthy"] else "no failure criterion triggered"
        lines.append(f"- **{g}**: {verdict}. "
                     f"E3 out-of-scope writes: {', '.join(c['scope_violation_cases']) or 'none'}; "
                     f"YES cases refused: {len(c['yes_refused'])} of {c['yes_total']}"
                     f"{' (systematic refusal)' if c['systematic_refusal'] else ''}; "
                     f"NO cases followed: {len(c['no_followed'])} of {c['no_total']}"
                     f"{' (systematic following)' if c['systematic_following'] else ''}; "
                     f"backtest leaks: {', '.join(c['leak_cases']) or 'none'}.")
    return "\n".join(lines)


def backtest_section(results: list[dict]) -> str:
    rows = [r for r in results if _layer(r) == "R" and r["group"] == "pipeline"]
    if not rows:
        return ""
    out = ["## Backtests (layer R, reported separately)", "",
           "Each backtest sees only excerpts public on its decision date, runs offline, and is graded against what "
           "actually happened. Contaminated results (the model recalled the outcome without documents) are listed "
           "but should not be read as reasoning results.", "",
           "| Case | Status | Contamination | Leak checks | Outcome grading | Failure types |",
           "| --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        cont = r.get("contamination") or {}
        cont_text = ("not run" if not cont.get("ran") else
                     ("contaminated: " + ", ".join(cont["markers_hit"])) if cont.get("contaminated") else "clean")
        leaks = [c for c in r.get("checks", []) if c["eval"] == "Backtest" and c["failure_type"] == "leak"]
        leak_text = "-" if not leaks else ("leak" if any(not c["passed"] for c in leaks) else "no leak")
        bt = r.get("backtest")
        if bt:
            plans = "; ".join(f"{p['terminal_id']}: {p.get('outcome') or ('pass' if p['pass'] else 'fail')}"
                              + (f" (unmatched: {', '.join(p['unmatched'])})" if p.get("unmatched") else "")
                              for p in bt["plans"]) or "no plans"
            grade = f"{plans} [rules: {', '.join(bt['rules'])}]"
        else:
            grade = "not graded"
        out.append("| " + " | ".join(_cell(x) for x in [r["case_id"], STATUS_TEXT.get(r["status"], r["status"]),
                                                          cont_text, leak_text, grade, _failures(r)]) + " |")
    clean = [r["case_id"] for r in rows if not (r.get("contamination") or {}).get("contaminated")]
    out += ["", f"Not contaminated: {', '.join(clean) or 'none'}. Contaminated: "
            f"{', '.join(r['case_id'] for r in rows if (r.get('contamination') or {}).get('contaminated')) or 'none'}.", ""]
    return "\n".join(out)


def probes_section(results: list[dict]) -> str:
    rows = [r for r in results if _layer(r) == "P"]
    if not rows:
        return ""
    out = ["## Behavior probes (layer P, reported separately)", "",
           "Each pair runs one case twice and changes one thing. Only fields that differ are listed; no percentages.", ""]
    for r in rows:
        p = r.get("probe", {})
        out.append(f"### {r['case_id']}: {p.get('base_case')} ({p.get('kind')})")
        out.append(f"- Question: {p.get('question')}")
        out.append(f"- A: {json.dumps(p.get('a'))}; B: {json.dumps(p.get('b'))}")
        if r["status"] == "ERROR":
            out.append(f"- Error: {r['actual'].get('error')}")
        elif not r.get("diff"):
            out.append("- No difference in the compared fields.")
        else:
            for field, v in r["diff"].items():
                out.append(f"- `{field}`: A = {json.dumps(v['a'], ensure_ascii=False)}; "
                           f"B = {json.dumps(v['b'], ensure_ascii=False)}")
        out.append("")
    return "\n".join(out)


def pending_section(results: list[dict]) -> str:
    lines = []
    for r in results:
        if r["status"] == "PENDING_REVIEW":
            lines.append(f"- {r['case_id']} ({r['group']}): " + "; ".join(r.get("human_review") or []))
    return "\n".join(lines) or "- none"


def check_details(results: list[dict]) -> str:
    lines = []
    for r in results:
        failed = [c for c in r.get("checks", []) if not c["passed"]]
        for c in failed:
            lines.append(f"- {r['case_id']} ({r['group']}) `{c['name']}` [{c['eval']}]: {c.get('detail') or '-'}")
    return "\n".join(lines) or "- none"


def render_report(results: list[dict], title: str = "Catalyst eval per-case report") -> str:
    main = [r for r in results if _layer(r) not in SEPARATE_LAYERS]
    groups = [g for g in ("pipeline", "baseline") if any(r["group"] == g for r in main)]
    out = [f"# {title}", "",
           "Counts only, no percentages. Each scenario has 1-3 cases, so results speak only for those cases. "
           "CausalT5k was published early this year and models may have seen it; T1-T6 are a smoke test, not a score. "
           "Control-group results come from actual runs, nothing is assumed.", ""]
    if any(r.get("fake") for r in results):
        out[2:2] = ["> **These are fake results from a fake reasoner, used only to test the report generator. "
                    "They say nothing about any model or pipeline.**", ""]
    for g in groups:
        rows = [r for r in main if r["group"] == g]
        out += [f"## {g} group", "", _counts(rows), "", case_table(rows), ""]
    if len(groups) == 2:
        out += ["## pipeline vs baseline", "", comparison_table(main), ""]
    for section in (backtest_section(results), probes_section(results)):
        if section:
            out += [section]
    out += ["## Failure criteria", "", criteria_section(results, groups or ["pipeline"]), "",
            "## Failed automatic checks", "", check_details(results), "",
            "## Pending human review", "", pending_section(results), "",
            "Failure types: " + "; ".join(f"`{k}` {v}" for k, v in scoring.FAILURE_TYPES.items()), ""]
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
