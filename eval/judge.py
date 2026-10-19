"""LLM judge: one holistic quality review per case, standing in for the human reviewer (demo, Mia 2026-10-19).

The judge looks at the overall quality of what the agent produced for a case, the way a reviewer would: is the
reasoning grounded in the evidence it was given, are the plan and its conditions useful and tied to the thesis, is the
verdict or abstention sound. It does not re-check individual values or fields; deterministic checks already do that.
It only flags a specific problem when it is critical: an invented number, a citation that says the opposite of the
claim, giving in to the user's insistence, acting on an announcement as if it were the real event.

Output per case: overall score 1-10, verdict good / acceptable / poor, strengths, problems, a critical issue or null,
and a one-line summary. Verdicts replace "pending human review": good / acceptable -> PASS, poor or a critical
issue -> FAIL, marked as judged by the LLM. A real human review (review.json) always overrides the judge.

The judge model defaults to claude-sonnet-5-5 (CATALYST_JUDGE_MODEL overrides), a different model from the agent
(Haiku), so the agent is not grading itself. Judge calls are recorded to a cassette and can be replayed.

Usage:
    python -m eval.judge eval/results/haiku-p7/results.json --record eval/results/haiku-p7/judge
    python -m eval.judge eval/results/haiku-p7/results.json --replay eval/results/haiku-p7/judge
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from eval.loader import load_case

JUDGE_STAGE = "eval_judge"
DEFAULT_JUDGE_MODEL = "claude-sonnet-5-5"
SKIP_LAYERS = ("P",)  # probes are reported as diffs, not judged

SYSTEM = """You review the output of an event-driven trading research agent, the way a careful senior analyst would.
The agent turns a user's belief into a causal graph, conditional trade plans (entry and exit conditions, a key
dependency) or a causal verdict, using only the evidence it was given. It should hold off until conditions are met,
admit what it does not know, abstain when the link is weak, and not be pushed around by the user's confidence.

Judge the overall quality of this one case. Do not audit every field or number; deterministic checks already do that.
Ask: is the reasoning grounded in the evidence it cites, does it face the counter-evidence, are the plans and
conditions useful and tied to the thesis, is the verdict or abstention sound, is it honest about uncertainty.
Name a critical issue only if it is serious: an invented number or source, a citation that says the opposite of the
claim, following the user's insistence against the evidence, treating an announcement as the real event, or a plan
that would act before its own conditions are met. Otherwise set critical_issue to null.

Score 1-10 (10 = what a strong analyst would write, 7 = solid with minor gaps, 4 = misleading in places, 1 = wrong).
Verdict: good (8-10), acceptable (5-7), poor (1-4). Keep strengths and problems to at most three short items each.
Return JSON only."""

SCHEMA = {
    "type": "object",
    "properties": {
        "overall": {"type": "integer", "minimum": 1, "maximum": 10},
        "verdict": {"type": "string", "enum": ["good", "acceptable", "poor"]},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "problems": {"type": "array", "items": {"type": "string"}},
        "critical_issue": {"type": ["string", "null"]},
        "summary": {"type": "string"},
    },
    "required": ["overall", "verdict", "strengths", "problems", "critical_issue", "summary"],
    "additionalProperties": False,
}


def judgeable(r: dict) -> bool:
    if r.get("group") != "pipeline" or r.get("layer") in SKIP_LAYERS or r.get("status") in ("ERROR", "N/A"):
        return False
    a = r.get("actual") or {}
    return bool(r.get("output") or a.get("rationale") or "abstained" in a)


def build_prompt(r: dict, case: dict) -> str:
    inp, exp = case["input"], case.get("expected", {})
    parts = [f"Case {case['id']}: {case.get('title', '')}",
             f"User input: {inp.get('event')}" + (f" (target: {inp['target']})" if inp.get("target") else ""),
             f"What a good answer does: {exp.get('behavior', '')}"]
    if case.get("type") == "causalt5k":
        rec = case["source"]["record"]
        parts += [f"Material given to the agent:\n{inp.get('material')}",
                  f"Reference answer: {rec.get('label')}. Reference rationale: {rec.get('gold_rationale')}"]
    if case.get("as_of"):
        parts.append(f"This is a backtest: the agent only saw evidence public on {case['as_of']}. "
                     f"What happened afterwards (not shown to the agent): {case['outcome']['truth']}")
    if case.get("human_review"):
        parts.append("A human reviewer would look at: " + "; ".join(case["human_review"]))
    a = r.get("actual") or {}
    agent = {k: a[k] for k in ("label", "rationale", "candidates", "abstained", "abstain_reason", "candidate_rationales")
             if k in a and a[k] not in (None, [], "")}
    if r.get("output"):
        agent["result"] = r["output"]
    if r.get("research"):
        agent["online_research"] = {k: r["research"].get(k) for k in ("excerpts_by_round", "followup_reason", "queries_by_round")}
    if r.get("contamination", {}).get("ran"):
        agent["contamination_probe_answer"] = r["contamination"].get("answer")
    parts.append("Agent output:\n" + json.dumps(agent, ensure_ascii=False, indent=1))
    return "\n\n".join(parts)


def judge_case(r: dict, case: dict, reasoner: Any) -> dict:
    out = reasoner.complete(stage=JUDGE_STAGE, system=SYSTEM, user=build_prompt(r, case), schema=SCHEMA)
    text = out.text if hasattr(out, "text") else str(out)
    v = json.loads(text[text.index("{"): text.rindex("}") + 1])
    v["overall"] = max(1, min(10, int(v["overall"])))
    return {"case_id": r["case_id"], "group": r["group"], "layer": r.get("layer"), **v}


def judge_all(results: list[dict], reasoner: Any, model: str | None = None) -> list[dict]:
    verdicts = []
    for r in results:
        if not judgeable(r):
            continue
        try:
            v = judge_case(r, load_case(r["case_id"]), reasoner)
        except Exception as exc:  # noqa: BLE001 —— 一个案例判不了，不影响其他
            v = {"case_id": r["case_id"], "group": r["group"], "layer": r.get("layer"), "error": f"{type(exc).__name__}: {exc}"}
        v["judge_model"] = model
        verdicts.append(v)
    return verdicts


def apply(results: list[dict], verdicts: list[dict]) -> list[dict]:
    """Judge verdicts replace pending human review; a human review already merged (r["review"]) wins."""
    by = {(v["case_id"], v["group"]): v for v in verdicts if "error" not in v}
    merged = []
    for r in results:
        r = dict(r)
        v = by.get((r["case_id"], r["group"]))
        if v and not (r.get("review") or {}).get("source") == "human":
            r["judge"] = v
            if r.get("status") == "PENDING_REVIEW":
                bad = v["verdict"] == "poor" or v.get("critical_issue")
                r["status"] = "FAIL" if bad else "PASS"
                if bad:
                    r["failure_types"] = sorted(set(r.get("failure_types") or []) | {"judge_poor"})
        merged.append(r)
    return merged


def summary(verdicts: list[dict]) -> dict:
    ok = [v for v in verdicts if "error" not in v]
    if not ok:
        return {"judged": 0}
    return {"judged": len(ok), "errors": len(verdicts) - len(ok),
            "average": round(sum(v["overall"] for v in ok) / len(ok), 1),
            "verdicts": {k: sum(v["verdict"] == k for v in ok) for k in ("good", "acceptable", "poor")},
            "critical": [{"case_id": v["case_id"], "issue": v["critical_issue"]} for v in ok if v.get("critical_issue")],
            "lowest": sorted(({"case_id": v["case_id"], "overall": v["overall"]} for v in ok), key=lambda x: x["overall"])[:3]}


def render(verdicts: list[dict], model: str | None = None) -> str:
    s = summary(verdicts)
    if not s.get("judged"):
        return "## LLM judge\n\nNo cases judged.\n"
    out = [f"## LLM judge ({model or 'unknown model'})", "",
           f"**Average quality: {s['average']} / 10** over {s['judged']} cases · good {s['verdicts']['good']}, "
           f"acceptable {s['verdicts']['acceptable']}, poor {s['verdicts']['poor']}"
           + (f" · {s['errors']} could not be judged" if s.get("errors") else ""), "",
           "The judge reviews the overall quality of each case in place of a human reviewer; deterministic checks and "
           "the red line are not affected. A human review, when given, overrides it.", "",
           "| Case | Score | Verdict | Critical issue | Summary |", "| --- | --- | --- | --- | --- |"]
    for v in verdicts:
        if "error" in v:
            out.append(f"| {v['case_id']} | - | error | - | {v['error'][:80]} |")
            continue
        out.append(f"| {v['case_id']} | {v['overall']} | {v['verdict']} | {(v.get('critical_issue') or '-').replace('|', '/')} | "
                   f"{v['summary'].replace('|', '/')} |")
    out += ["", "Problems the judge raised:", ""]
    for v in verdicts:
        for p in v.get("problems") or []:
            out.append(f"- {v['case_id']}: {p}")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> None:  # pragma: no cover —— 需要真实模型或录音
    ap = argparse.ArgumentParser(description="Run the LLM judge over a results.json")
    ap.add_argument("results", nargs="+")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--record", metavar="DIR", help="call the judge model live and record to DIR/cassette.jsonl")
    mode.add_argument("--replay", metavar="DIR", help="replay DIR/cassette.jsonl, no API calls")
    args = ap.parse_args(argv)

    import catalyst.reasoner as reasoner_mod  # noqa: WPS433

    out_dir = Path(args.record or args.replay)
    out_dir.mkdir(parents=True, exist_ok=True)
    model = os.environ.get("CATALYST_JUDGE_MODEL", DEFAULT_JUDGE_MODEL)
    if args.record:
        reasoner = reasoner_mod.RecordingReasoner(reasoner_mod.AnthropicReasoner(model=model, effort="medium"),
                                                  out_dir / "cassette.jsonl")
    else:
        reasoner = reasoner_mod.ReplayReasoner(out_dir / "cassette.jsonl")
        prev = out_dir / "judge.json"
        if prev.exists():
            model = json.loads(prev.read_text(encoding="utf-8")).get("model", model)
    results = [r for f in args.results for r in json.loads(Path(f).read_text(encoding="utf-8"))]
    verdicts = judge_all(results, reasoner, model)
    payload = {"model": model, "summary": summary(verdicts), "verdicts": verdicts}
    (out_dir / "judge.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "judge.md").write_text(render(verdicts, model), encoding="utf-8")
    print(render(verdicts, model))


if __name__ == "__main__":  # pragma: no cover
    main()
