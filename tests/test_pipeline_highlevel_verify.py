"""Tests for high-level pipeline verification."""

import pytest
from pathlib import Path
from cvextract.pipeline import verify_extracted_data
from cvextract.shared import VerificationResult


class TestExtractedDataVerification:
    """Tests for verifying extracted CV data structure."""

    def test_verify_complete_valid_data_returns_ok(self):
        """When all required fields are present and valid, should return ok=True."""
        data = {
            "identity": {"title": "T", "full_name": "A B", "first_name": "A", "last_name": "B"},
            "sidebar": {"languages": ["EN"], "tools": ["X"], "industries": ["Y"], "spoken_languages": ["EN"], "academic_background": ["Z"]},
            "overview": "hi",
            "experiences": [{"heading": "Jan 2020 - Present", "description": "d", "bullets": ["b"], "environment": ["Python"]}],
        }
        res = verify_extracted_data(data)
        assert isinstance(res, VerificationResult)
        assert res.ok is True
        assert res.errors == []

    def test_verify_with_missing_identity_returns_error(self):
        """When identity is missing or empty, should return ok=False with error."""
        data = {"identity": {}, "sidebar": {"languages": ["EN"]}, "overview": "hi", "experiences": [{"heading": "h", "description": "d"}]}
        res = verify_extracted_data(data)
        assert res.ok is False
        assert "identity" in res.errors

    def test_verify_with_all_empty_sidebar_sections_returns_error(self):
        """When all sidebar sections are empty, should return ok=False with error."""
        data = {
            "identity": {"title": "T", "full_name": "A B", "first_name": "A", "last_name": "B"},
            "sidebar": {"languages": [], "tools": [], "industries": [], "spoken_languages": [], "academic_background": []},
            "overview": "hi",
            "experiences": [{"heading": "h", "description": "d"}],
        }
        res = verify_extracted_data(data)
        assert res.ok is False
        assert "sidebar" in res.errors

    def test_verify_with_some_missing_sidebar_sections_returns_warning(self):
        """When some sidebar sections are missing, should return ok=True with warning."""
        data = {
            "identity": {"title": "T", "full_name": "A B", "first_name": "A", "last_name": "B"},
            "sidebar": {"languages": ["EN"]},
            "overview": "hi",
            "experiences": [{"heading": "h", "description": "d"}],
        }
        res = verify_extracted_data(data)
        assert res.ok is True
        assert any("missing sidebar" in w for w in res.warnings)

    def test_verify_with_invalid_environment_format_returns_warning(self):
        """When environment is not a list or None, should return ok=True with warning."""
        data = {
            "identity": {"title": "T", "full_name": "A B", "first_name": "A", "last_name": "B"},
            "sidebar": {"languages": ["EN"]},
            "overview": "hi",
            "experiences": [{"heading": "h", "description": "d", "environment": "Python"}],  # should be list or None
        }
        res = verify_extracted_data(data)
        assert res.ok is True
        assert any("invalid environment format" in w for w in res.warnings)

    def test_verify_with_no_experiences_returns_error(self):
        """When experiences list is empty, should return ok=False with error."""
        data = {
            "identity": {"title": "T", "full_name": "A B", "first_name": "A", "last_name": "B"},
            "sidebar": {"languages": ["EN"]},
            "overview": "hi",
            "experiences": [],
        }
        res = verify_extracted_data(data)
        assert res.ok is False
        assert "experiences_empty" in res.errors
