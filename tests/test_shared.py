import pytest

import cvextract.shared

class TestTextNormalization:
    """Tests for text normalization functions."""
    
    def test_normalize_text_with_special_chars_replaces_with_standard_equivalents(self):
        """Non-breaking spaces, soft hyphens, and line endings should be normalized."""
        s = "A\u00A0B high\u00ADquality\r\nok\rnice"
        out = cvextract.shared.normalize_text_for_processing(s)
        assert out == "A B high-quality\nok\nnice"

    def test_normalize_text_with_invalid_xml_chars_removes_them(self):
        """Invalid XML 1.0 characters like vertical tab should be stripped."""
        s = "ok\x0bnope"
        out = cvextract.shared.normalize_text_for_processing(s)
        assert out == "oknope"

    def test_clean_text_with_excess_whitespace_collapses_and_trims(self):
        """Multiple spaces, tabs, and newlines should collapse to single spaces."""
        s = "  A\u00A0B \n  C\t\tD  "
        assert cvextract.shared.clean_text(s) == "A B C D"


class TestXMLSanitization:
    """Tests for XML sanitization in data structures."""
    
    def test_sanitize_nested_object_recursively_normalizes_all_strings(self):
        """Sanitization should traverse nested dicts, lists, and preserve non-strings."""
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


class TestIdentity:
    """Tests for Identity dataclass."""
    
    def test_identity_as_dict_returns_all_fields(self):
        """Identity object should convert to dictionary with all fields."""
        ident = cvextract.shared.Identity(title="Senior", full_name="Ada Lovelace", first_name="Ada", last_name="Lovelace")
        assert ident.as_dict() == {
            "title": "Senior",
            "full_name": "Ada Lovelace",
            "first_name": "Ada",
            "last_name": "Lovelace",
        }


class TestExperienceBuilder:
    """Tests for ExperienceBuilder."""
    
    def test_finalize_with_no_environment_returns_none_for_environment(self):
        """When environment list is empty, finalized dict should have environment=None."""
        b = cvextract.shared.ExperienceBuilder(heading="H", description_parts=["a", "b"], bullets=["x"])
        d = b.finalize()
        assert d["heading"] == "H"
        assert d["description"] == "a b"
        assert d["bullets"] == ["x"]
        assert d["environment"] is None
