import pytest

from pathlib import Path
from cvextract.pipeline import verify_extracted_data
from cvextract.shared import VerificationResult


def test_verify_extracted_data_ok():
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

def test_verify_extracted_data_missing_identity_is_error():
    data = {"identity": {}, "sidebar": {"languages": ["EN"]}, "overview": "hi", "experiences": [{"heading": "h", "description": "d"}]}
    res = verify_extracted_data(data)
    assert res.ok is False
    assert "identity" in res.errors

def test_verify_extracted_data_sidebar_all_empty_is_error():
    data = {
        "identity": {"title": "T", "full_name": "A B", "first_name": "A", "last_name": "B"},
        "sidebar": {"languages": [], "tools": [], "industries": [], "spoken_languages": [], "academic_background": []},
        "overview": "hi",
        "experiences": [{"heading": "h", "description": "d"}],
    }
    res = verify_extracted_data(data)
    assert res.ok is False
    assert "sidebar" in res.errors

def test_verify_extracted_data_missing_sidebar_sections_warns():
    data = {
        "identity": {"title": "T", "full_name": "A B", "first_name": "A", "last_name": "B"},
        "sidebar": {"languages": ["EN"]},
        "overview": "hi",
        "experiences": [{"heading": "h", "description": "d"}],
    }
    res = verify_extracted_data(data)
    assert res.ok is True
    assert any("missing sidebar" in w for w in res.warnings)

def test_verify_extracted_data_invalid_environment_warns():
    data = {
        "identity": {"title": "T", "full_name": "A B", "first_name": "A", "last_name": "B"},
        "sidebar": {"languages": ["EN"]},
        "overview": "hi",
        "experiences": [{"heading": "h", "description": "d", "environment": "Python"}],  # should be list or None
    }
    res = verify_extracted_data(data)
    assert res.ok is True
    assert any("invalid environment format" in w for w in res.warnings)

def test_verify_extracted_data_empty_experiences_is_error():
    data = {
        "identity": {"title": "T", "full_name": "A B", "first_name": "A", "last_name": "B"},
        "sidebar": {"languages": ["EN"]},
        "overview": "hi",
        "experiences": [],
    }
    res = verify_extracted_data(data)
    assert res.ok is False
    assert "experiences_empty" in res.errors
