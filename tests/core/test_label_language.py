"""A node label is in the language of its own statement: a Chinese label on an English statement is sent back."""
from catalyst.entrypoints import _label_issues
from catalyst.schema import Claim


def _n(label, statement="Amkor's advanced packaging revenue slows as TSMC keeps more CoWoS work in-house"):
    return Claim.model_validate({"id": "a", "role": "assumption", "statement": statement, "original_statement": statement,
                                 "evidence_status": "unknown", "time_bucket": None, "instruments": [], "label": label})


def test_chinese_label_on_an_english_statement_is_blocking():
    errs, _ = _label_issues([_n("低配OSAT")])
    assert errs and "must be in English" in errs[0]


def test_matching_languages_are_fine():
    assert _label_issues([_n("Underweight OSATs")])[0] == []
    assert _label_issues([_n("低配封测", statement="台积电扩产挤压封测厂的外溢订单")])[0] == []
