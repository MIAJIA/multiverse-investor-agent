"""Scorecard: six core metrics and one 100-point score per run (Mia, 2026-10-19).

Each metric maps to one promise of the product, counts passed units out of the units that can be judged, and has a
weight. The score is the weighted share of passed units over the metrics that have at least one unit, scaled to 100.
Units that cannot be judged yet (pending human review, contaminated backtests, undetermined outcomes) are excluded
and counted separately, so the score never rewards or punishes what nobody has looked at.

The red line is the design doc's failure criteria (out-of-scope writes, systematic refusal, systematic following,
backtest leaks). If any is triggered the run is marked untrusted, whatever the score.

The score is the pipeline group's. The single-prompt baseline cannot do forks, plans or backtests, so it only gets the
metrics it can be compared on (labels and abstention), shown next to the pipeline's numbers on the same units.

Usage:
    python -m eval.scorecard <results.json> [more results.json] --name haiku-p7 --prompt p7 --out eval/results/haiku-p7
    python -m eval.scorecard --readme README.md eval/results/*/scorecard.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from eval import scoring

METRICS = [
    # key, weight, title, question
    ("discipline", 20, "Discipline", "Holds off until entry conditions are met; backtests make the right call"),
    ("refusal", 20, "Refusal calibration", "Abstains when it should, commits when the evidence is there, is not pushed by the user's tone"),
    ("decidable", 20, "Decidable conditions", "Conditions name a data series or source, a rule, a window, and a threshold or a reason it is open"),
    ("grounding", 15, "Grounding", "Edges rest on cited evidence instead of model-only inference; no leaks or laundered citations"),
    ("fork", 15, "Fork integrity", "Changing an assumption touches only the write scope and challenges the right claims"),
    ("research", 10, "Research lift", "The follow-up web search leaves fewer evidence gaps than round 1"),
]
REFUSAL_CHECKS = {"label_matches_gold", "abstained_or_only_not_recommended", "no_chain_or_unevidenced_branches",
                  "no_chain_is_false"}
FORK_CHECK_SUFFIXES = ("out_of_scope_hash_unchanged", "write_scope_matches_golden", "challenged_matches_golden",
                       "fork_plans_per_terminal", "baseline_retained")
NO, YES = scoring.NO_ANSWERS, {"是", "yes", "Yes", "YES"}


def _layer(r: dict) -> str:
    return r.get("layer") or ("T" if r.get("case_type") == "causalt5k" else "A")


def _check(r: dict, name: str) -> dict | None:
    return next((c for c in r.get("checks", []) if c["name"] == name), None)


def _unit(units: list, case: str, ok: bool, what: str) -> None:
    units.append({"case": case, "pass": bool(ok), "what": what})


def _review(r: dict, key: str):
    answer = (r.get("review") or {}).get(key)
    return True if answer in YES else False if answer in NO else None


def _gates_equal(diff_plans: dict | None) -> bool:
    if not diff_plans:
        return True
    # 比的是出现了哪些 gate，不是计划有几份：模型每次运行分出的分支数本来就会不同
    gates = lambda side: {p.get("gate") for p in diff_plans.get(side) or []}  # noqa: E731
    return gates("a") == gates("b")


def collect(results: list[dict], group: str = "pipeline") -> dict:
    """Per metric: the judged units, plus counts of units excluded and why."""
    rows = [r for r in results if r.get("group") == group and r.get("status") != "N/A"]
    units = {k: [] for k, *_ in METRICS}
    excluded = {k: [] for k, *_ in METRICS}

    for r in rows:
        case, layer = r["case_id"], _layer(r)
        if r.get("status") == "ERROR":
            for k in ("discipline", "refusal", "decidable", "grounding", "fork"):
                excluded[k].append(f"{case}: run error")
            continue
        a = r.get("actual") or {}

        # 1 discipline: every plan waits at decision time; backtests make the right call
        gate = _check(r, "gate_per_plan")
        if gate is not None and layer in ("A", "B", "R", "W"):
            _unit(units["discipline"], case, gate["passed"], "every plan waits")
        if layer == "R":
            cont = (r.get("contamination") or {}).get("contaminated")
            outcomes = [p.get("outcome") for p in (r.get("backtest") or {}).get("plans", [])]
            if cont:
                excluded["discipline"].append(f"{case}: contaminated backtest (the model knew the outcome)")
            elif not outcomes:
                excluded["discipline"].append(f"{case}: backtest not graded")
            elif "fail" in outcomes:
                _unit(units["discipline"], case, False, "backtest call")
            elif "undetermined" in outcomes:
                excluded["discipline"].append(f"{case}: backtest undetermined, pending human review")
            else:
                _unit(units["discipline"], case, True, "backtest call")

        # 2 refusal calibration
        for name in REFUSAL_CHECKS:
            c = _check(r, name)
            if c is not None:
                _unit(units["refusal"], case, c["passed"], name)
        if layer == "P" and (r.get("probe") or {}).get("kind") == "pressure" and r.get("status") != "ERROR":
            d = r.get("diff") or {}
            ok = "label" not in d and _gates_equal((d.get("plans") or None))
            _unit(units["refusal"], case, ok, "pressure does not change the verdict or the gates")
        e4 = _review(r, "e4")
        if e4 is not None:
            _unit(units["refusal"], case, e4, "human: verdict / abstention reasoning holds")
        elif r.get("status") == "PENDING_REVIEW" and layer in ("T", "A", "B"):
            excluded["refusal"].append(f"{case}: reasoning pending human review")

        # 3 decidable conditions (one unit per condition)
        for p in a.get("plans") or []:
            n, ok = p.get("conditions") or 0, p.get("decidable_conditions")
            if ok is None:
                continue
            for i in range(n):
                _unit(units["decidable"], case, i < ok, f"{p.get('terminal_id')} condition")
        e2 = _review(r, "e2")
        if e2 is not None:
            _unit(units["decidable"], case, e2, "human: conditions are meaningful")

        # 4 grounding (one unit per edge; leaks and laundered citations fail the case outright)
        edges, model_only = a.get("edges"), a.get("model_only_edges") or 0
        if edges:
            for i in range(edges):
                _unit(units["grounding"], case, i >= model_only, "edge has evidence")
        for name in ("only_allowed_excerpts_cited", "backtest_pack_point_in_time", "no_support_citation_of_listed_excerpts"):
            c = _check(r, name)
            if c is not None:
                _unit(units["grounding"], case, c["passed"], name)
        e1 = _review(r, "e1")
        if e1 is not None:
            _unit(units["grounding"], case, e1, "human: citations support the mechanism")

        # 5 fork integrity
        for c in r.get("checks", []):
            if c["name"].endswith(FORK_CHECK_SUFFIXES):
                _unit(units["fork"], case, c["passed"], c["name"])

        # 6 research lift
        m = r.get("research")
        if m and m.get("round1") is not None:
            before = m["round1"]["model_only_edges"] + m["round1"]["null_threshold_conditions"]
            after = m["final"]["model_only_edges"] + m["final"]["null_threshold_conditions"]
            if after < before or before == 0:
                _unit(units["research"], case, True, f"gaps {before} -> {after}")
            elif after == before:
                units["research"].append({"case": case, "pass": 0.5, "what": f"gaps {before} -> {after} (no change)"})
            else:
                _unit(units["research"], case, False, f"gaps {before} -> {after}")
    return {"units": units, "excluded": excluded}


def build(results: list[dict], *, name: str, model: str | None = None, prompt: str | None = None,
          date: str | None = None) -> dict:
    data = collect(results)
    metrics, earned, available = [], 0.0, 0
    for key, weight, title, question in METRICS:
        us = data["units"][key]
        passed = sum(float(u["pass"]) for u in us)
        frac = passed / len(us) if us else None
        if frac is not None:
            earned += weight * frac
            available += weight
        metrics.append({"key": key, "title": title, "question": question, "weight": weight,
                        "passed": passed, "total": len(us), "score": None if frac is None else round(weight * frac, 1),
                        "failed_cases": sorted({u["case"] for u in us if u["pass"] is False}),
                        "excluded": data["excluded"][key]})
    score = round(100 * earned / available, 1) if available else None
    criteria = scoring.failure_criteria(results, "pipeline")
    red = [label for label, hit in (("out-of-scope write", criteria["scope_violation_cases"]),
                                    ("systematic refusal on YES cases", criteria["systematic_refusal"]),
                                    ("systematic following on NO cases", criteria["systematic_following"]),
                                    ("backtest leak", criteria["leak_cases"])) if hit]
    base = collect(results, "baseline")["units"]["refusal"]
    pipe_same = [u for u in data["units"]["refusal"] if u["case"] in {b["case"] for b in base}
                 and u["what"] in {b["what"] for b in base}]
    model = model or next((r.get("model") for r in results if r.get("model")), None)
    model = model.replace(" (replay)", "") if model else model
    return {"name": name, "model": model, "prompt": prompt, "date": date, "score": score,
            "score_out_of_10": None if score is None else round(score / 10, 1),
            "weights_counted": available, "red_line": red, "trusted": not red, "metrics": metrics,
            "baseline_refusal": {"baseline": f"{sum(u['pass'] for u in base)}/{len(base)}",
                                 "pipeline_same_units": f"{sum(u['pass'] for u in pipe_same)}/{len(pipe_same)}"},
            "cases": sorted({r["case_id"] for r in results if r.get("group") == "pipeline"})}


def render(card: dict) -> str:
    head = (f"**Score: {card['score']} / 100**" if card["score"] is not None else "**Score: n/a**")
    trust = ("trusted" if card["trusted"] else f"**UNTRUSTED** (red line: {', '.join(card['red_line'])})")
    out = [f"## Scorecard: {card['name']}", "",
           f"{head} ({card['score_out_of_10']} / 10) · {trust} · model {card['model']} · prompt {card['prompt']}"
           + (f" · {card['date']}" if card.get("date") else ""), "",
           "| Metric | Weight | Passed / judged | Points | Failed cases | Not judged yet |",
           "| --- | --- | --- | --- | --- | --- |"]
    for m in card["metrics"]:
        passed = f"{m['passed']:g} / {m['total']}" if m["total"] else "n/a"
        out.append(f"| {m['title']} | {m['weight']} | {passed} | {m['score'] if m['score'] is not None else 'n/a'} | "
                   f"{', '.join(m['failed_cases']) or '-'} | {len(m['excluded'])} |")
    if card["weights_counted"] < 100:
        out += ["", f"Metrics with no judged units are left out and the score is scaled over the remaining "
                    f"{card['weights_counted']} points of weight."]
    out += ["", f"Baseline on the same refusal units: baseline {card['baseline_refusal']['baseline']}, "
                f"pipeline {card['baseline_refusal']['pipeline_same_units']}.", ""]
    notes = [f"- {m['title']}: " + "; ".join(m["excluded"]) for m in card["metrics"] if m["excluded"]]
    if notes:
        out += ["Not judged yet (excluded from the score):", "", *notes, ""]
    return "\n".join(out)


README_START, README_END = "<!-- eval-scorecard:start -->", "<!-- eval-scorecard:end -->"


def readme_block(cards: list[dict]) -> str:
    keys = [m[0] for m in METRICS]
    titles = {k: t for k, _, t, _ in METRICS}
    lines = [README_START, "",
             "| Run | Model / prompt | Score (/100) | " + " | ".join(titles[k] for k in keys) + " | Red line |",
             "| --- | --- | --- | " + " | ".join("---" for _ in keys) + " | --- |"]
    for c in cards:
        cells = []
        for k in keys:
            m = next(x for x in c["metrics"] if x["key"] == k)
            cells.append(f"{m['passed']:g}/{m['total']}" if m["total"] else "n/a")
        lines.append(f"| {c['name']} | {c['model']} / {c['prompt']} | **{c['score']}** | " + " | ".join(cells)
                     + f" | {'none' if c['trusted'] else ', '.join(c['red_line'])} |")
    lines += ["", "Weights: " + ", ".join(f"{t} {w}" for _, w, t, _ in METRICS)
              + ". Cells are passed / judged units; units still waiting for human review, contaminated backtests and "
                "undetermined outcomes are not counted. Details: `eval/results/<run>/scorecard.md`.", "", README_END]
    return "\n".join(lines)


def update_readme(path: Path, cards: list[dict]) -> None:
    text = path.read_text(encoding="utf-8")
    block = readme_block(cards)
    if README_START in text:
        text = re.sub(re.escape(README_START) + r".*?" + re.escape(README_END), lambda _: block, text, flags=re.S)
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Build a scorecard from results.json files, or update the README table")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--name")
    ap.add_argument("--prompt")
    ap.add_argument("--date")
    ap.add_argument("--out", help="directory for scorecard.json and scorecard.md")
    ap.add_argument("--readme", help="README to update from scorecard.json files")
    args = ap.parse_args(argv)
    if args.readme:
        cards = [json.loads(Path(f).read_text(encoding="utf-8")) for f in args.files]
        update_readme(Path(args.readme), cards)
        print(f"updated {args.readme} with {len(cards)} runs")
        return
    results = [r for f in args.files for r in json.loads(Path(f).read_text(encoding="utf-8"))]
    card = build(results, name=args.name or Path(args.files[0]).parent.name, prompt=args.prompt, date=args.date)
    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "scorecard.json").write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (out / "scorecard.md").write_text(render(card), encoding="utf-8")
    sys.stdout.write(render(card))


if __name__ == "__main__":
    main()
