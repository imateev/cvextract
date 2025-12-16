import pytest

import cvextract.shared

def test_normalize_text_for_processing_replaces_nbsp_soft_hyphen_and_newlines():
    s = "A\u00A0B high\u00ADquality\r\nok\rnice"
    out = cvextract.shared.normalize_text_for_processing(s)
    assert out == "A B high-quality\nok\nnice"

def test_normalize_text_for_processing_strips_invalid_xml_chars():
    # vertical tab is invalid in XML 1.0
    s = "ok\x0bnope"
    out = cvextract.shared.normalize_text_for_processing(s)
    assert out == "oknope"

def test_clean_text_collapses_whitespace_and_strips():
    s = "  A\u00A0B \n  C\t\tD  "
    assert cvextract.shared.clean_text(s) == "A B C D"

def test_sanitize_for_xml_in_obj_recursive():
    obj = {
        "a": "A\u00A0B",
        "b": ["x\u00ADy", {"c": "ok\x0bnope"}],
        "d": 123,
    }
    out = cvextract.shared.sanitize_for_xml_in_obj(obj)
    assert out["a"] == "A B"
    assert out["b"][0] == "x-y"
    assert out["b"][1]["c"] == "oknope"
    assert out["d"] == 123

def test_identity_as_dict():
    ident = cvextract.shared.Identity(title="Senior", full_name="Ada Lovelace", first_name="Ada", last_name="Lovelace")
    assert ident.as_dict() == {
        "title": "Senior",
        "full_name": "Ada Lovelace",
        "first_name": "Ada",
        "last_name": "Lovelace",
    }

def test_experience_builder_finalize_environment_none_when_empty():
    b = cvextract.shared.ExperienceBuilder(heading="H", description_parts=["a", "b"], bullets=["x"])
    d = b.finalize()
    assert d["heading"] == "H"
    assert d["description"] == "a b"
    assert d["bullets"] == ["x"]
    assert d["environment"] is None
