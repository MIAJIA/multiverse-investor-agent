"""Discover's grounded and hypothesis candidates go to Inspect together, so competing views share one graph."""
from catalyst import api
from catalyst import entrypoints as ep
from tests.core.test_api import scripted  # noqa: F401  (fixture)
from tests.core.test_harness import Scripted, _good, ev  # noqa: F401  (fixture)

C = [{"id": "c1", "direction": "Brent falls after transits recover", "instruments": ["BZ"], "label": "grounded",
      "rationale": "r", "excerpt_ids": ["hz-1"]},
     {"id": "c2", "direction": "Tanker rates lag the reopening", "instruments": ["FRO"], "label": "hypothesis",
      "rationale": "r", "excerpt_ids": []},
     {"id": "c3", "direction": "Oil collapses on the announcement alone", "instruments": ["BZ"],
      "label": "not_recommended", "rationale": "r", "excerpt_ids": []}]


def test_selection_keeps_grounded_and_hypothesis_and_drops_not_recommended():
    assert [c["id"] for c in ep.inspect_candidates(C)] == ["c1", "c2"]
    assert [c["id"] for c in ep.inspect_candidates(C[2:])] == ["c3"]  # nothing else left: keep a direction
    assert ep.inspect_candidates([]) == []


def test_inspect_prompt_lists_every_candidate_and_does_not_claim_the_user_chose(ev):  # noqa: F811
    r = Scripted([_good()])
    ep.inspect("Hormuz reopens next week", None, candidates=ep.inspect_candidates(C), reasoner=r, evidence=ev,
               config=ep.Config(packs=["hz"], today="2026-10-18"))
    prompt = r.prompts[0]
    assert "Candidate directions found by Discover" in prompt and '"c1"' in prompt and '"c2"' in prompt
    assert '"c3"' not in prompt and "chosen by the user" not in prompt
    assert "competing" in prompt


def test_a_single_kept_candidate_is_not_called_the_users_choice(ev):  # noqa: F811
    r = Scripted([_good()])
    ep.inspect("x", None, candidates=[C[0]], reasoner=r, evidence=ev,
               config=ep.Config(packs=["hz"], today="2026-10-18"))
    assert "Candidate directions found by Discover" in r.prompts[0] and "chosen by the user" not in r.prompts[0]


def test_api_passes_all_kept_candidates(scripted):  # noqa: F811
    disc = {"abstained": False, "abstain_reason": None, "candidates": C}
    scripted.outputs.insert(0, disc)
    api.create_run({"event": "Hormuz reopens next week", "today": "2026-10-18"})
    inspect_prompt = scripted.prompts[scripted.stages.index("inspect")]
    assert '"c1"' in inspect_prompt and '"c2"' in inspect_prompt and '"c3"' not in inspect_prompt
