"""Node labels follow the user's language: an English event with a Chinese label is sent back for a rewrite."""
from catalyst.entrypoints import _label_issues
from catalyst.schema import Claim


def _n(label):
    return Claim.model_validate({"id": "a", "role": "assumption", "statement": "s", "original_statement": "s",
                                 "evidence_status": "unknown", "time_bucket": None, "instruments": [], "label": label})


def test_chinese_label_on_an_english_event_is_blocking():
    errs, _ = _label_issues([_n("低配OSAT")], "TSMC is expanding CoWoS capacity faster than expected")
    assert errs and "must be in English" in errs[0]


def test_english_labels_and_chinese_events_are_fine():
    assert _label_issues([_n("Underweight OSATs")], "TSMC is expanding CoWoS capacity")[0] == []
    assert _label_issues([_n("低配封测")], "台积电 CoWoS 扩产超预期")[0] == []
    assert _label_issues([_n("低配封测")])[0] == []  # no event given: old behaviour
