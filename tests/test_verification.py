"""Tests for data verification and comparison."""

import pytest
from cvextract.verification import compare_data_structures, verify_extracted_data
from cvextract.shared import VerificationResult


class TestDataStructureComparison:
    """Tests for comparing data structures."""

    def test_compare_identical_structures_returns_ok(self):
        """When structures are identical, should return ok=True with no errors."""
        a = {"x": 1, "y": [1, 2], "z": {"k": "v"}}
        res = compare_data_structures(a, a)
        assert res.ok is True
        assert res.errors == []

    def test_compare_with_missing_key_returns_error(self):
        """When second structure is missing a key, should return ok=False with error."""
        a = {"x": 1, "y": {"k": 2}}
        b = {"x": 1}
        res = compare_data_structures(a, b)
        assert res.ok is False
        assert any("missing key" in e for e in res.errors)

    def test_compare_with_value_mismatch_returns_error(self):
        """When values differ between structures, should return ok=False with error."""
        a = {"x": [1, 2]}
        b = {"x": [1, 3]}
        res = compare_data_structures(a, b)
        assert res.ok is False
        assert any("value mismatch" in e for e in res.errors)

    def test_compare_environment_with_different_separators_returns_ok(self):
        """Environment fields with different separators (comma vs bullet) should be considered equivalent."""
        original = {
            "experiences": [
                {"environment": ["Java 17, Quarkus, Payara Enterprise, PostgreSQL"]},
            ]
        }
        roundtrip = {
            "experiences": [
                {"environment": ["Java 17 • Quarkus • Payara Enterprise • PostgreSQL"]},
            ]
        }
        res = compare_data_structures(original, roundtrip)
        assert res.ok is True

    def test_compare_environment_with_real_differences_returns_error(self):
        """Environment fields with actual content differences should return error."""
        original = {"experiences": [{"environment": ["Java", "Python"]}]}
        roundtrip = {"experiences": [{"environment": ["Java", "Go"]}]}
        res = compare_data_structures(original, roundtrip)
        assert res.ok is False
        assert any("environment mismatch" in e for e in res.errors)


class TestExtractedDataVerification:
    """Tests for verifying extracted CV data."""

    def test_verify_with_missing_sidebar_sections_returns_warning(self):
        """When some sidebar sections are missing, should return ok=True with warnings."""
        data = {
            "identity": {"title": "T", "full_name": "F N", "first_name": "F", "last_name": "N"},
            "sidebar": {"languages": []},
            "experiences": [{"heading": "h", "description": "d"}],
        }
        res = verify_extracted_data(data)
        assert res.ok is True
        assert any("missing sidebar" in w for w in res.warnings)
