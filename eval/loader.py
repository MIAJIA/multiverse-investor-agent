"""读 eval/cases 与 eval/fixtures 下的 JSON。纯数据，不 import catalyst。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

EVAL_DIR = Path(__file__).resolve().parent
CASES_DIR = EVAL_DIR / "cases"
FIXTURES_DIR = EVAL_DIR / "fixtures"

CAUSALT5K_IDS = ["T1", "T2", "T3", "T4", "T5", "T6"]
CUSTOM_IDS = ["C1", "C2", "C3", "C4", "D1"]
B_IDS = ["B1", "B2", "B3", "B4", "B5", "B6"]   # 关键场景（runner 的部分检查待实现）
R_IDS = ["R2", "R3", "K3"]                     # 回测（K3 的资料包 packs/opec2022.json 在 evidence 分支）
W_IDS = ["W1"]                                 # 联网 + 补查（--online）


def load_json(path: Path | str) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_fixture(name: str) -> Any:
    return load_json(FIXTURES_DIR / name)


def load_case(case_id: str) -> dict:
    if case_id in CAUSALT5K_IDS:
        return load_json(CASES_DIR / "causalt5k" / f"{case_id}.json")
    return load_json(CASES_DIR / f"{case_id}.json")


def load_all_cases(ids: list[str] | None = None) -> list[dict]:
    return [load_case(i) for i in (ids or CAUSALT5K_IDS + CUSTOM_IDS)]
