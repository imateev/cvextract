import pytest
from cvextract.verification import compare_data_structures, verify_extracted_data
from cvextract.shared import VerificationResult


def test_compare_data_structures_equal():
    a = {"x": 1, "y": [1, 2], "z": {"k": "v"}}
    res = compare_data_structures(a, a)
    assert res.ok is True
    assert res.errors == []


def test_compare_data_structures_missing_key():
    a = {"x": 1, "y": {"k": 2}}
    b = {"x": 1}
    res = compare_data_structures(a, b)
    assert res.ok is False
    assert any("missing key" in e for e in res.errors)


def test_compare_data_structures_value_mismatch():
    a = {"x": [1, 2]}
    b = {"x": [1, 3]}
    res = compare_data_structures(a, b)
    assert res.ok is False
    assert any("value mismatch" in e for e in res.errors)


def test_verify_extracted_data_warns_missing_sidebar():
    data = {
        "identity": {"title": "T", "full_name": "F N", "first_name": "F", "last_name": "N"},
        "sidebar": {"languages": []},
        "experiences": [{"heading": "h", "description": "d"}],
    }
    res = verify_extracted_data(data)
    assert res.ok is True
    assert any("missing sidebar" in w for w in res.warnings)


def test_compare_environment_separators_equivalent():
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


def test_compare_environment_separators_detects_real_diff():
    original = {"experiences": [{"environment": ["Java", "Python"]}]}
    roundtrip = {"experiences": [{"environment": ["Java", "Go"]}]}
    res = compare_data_structures(original, roundtrip)
    assert res.ok is False
    assert any("environment mismatch" in e for e in res.errors)
