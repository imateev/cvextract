"""Tests for the new verifier architecture."""

import json

import pytest

from cvextract.cli_config import UserConfig
from cvextract.shared import StepName, UnitOfWork
from cvextract.verifiers import (
    CVVerifier,
    get_verifier,
)
from cvextract.verifiers.roundtrip_verifier import RoundtripVerifier
from cvextract.verifiers.default_expected_cv_data_verifier import ExtractedDataVerifier
from cvextract.verifiers.default_cv_schema_verifier import CVSchemaVerifier


def _make_work(tmp_path, data):
    path = tmp_path / "data.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    work = UnitOfWork(config=UserConfig(target_dir=tmp_path))
    work.set_step_paths(StepName.Extract, input_path=path, output_path=path)
    work.current_step = StepName.Extract
    work.ensure_step_status(StepName.Extract)
    return work


def _make_roundtrip_work(tmp_path, source, target):
    source_path = tmp_path / "source.json"
    target_path = tmp_path / "target.json"
    source_path.write_text(json.dumps(source), encoding="utf-8")
    target_path.write_text(json.dumps(target), encoding="utf-8")
    work = UnitOfWork(config=UserConfig(target_dir=tmp_path))
    work.set_step_paths(
        StepName.RoundtripComparer, input_path=source_path, output_path=target_path
    )
    work.current_step = StepName.RoundtripComparer
    work.ensure_step_status(StepName.RoundtripComparer)
    return work


def _verify_data(verifier, tmp_path, data):
    work = _make_work(tmp_path, data)
    return verifier.verify(work)


def _status(work, step: StepName):
    return work.step_states[step]


class TestExtractedDataVerifier:
    """Tests for ExtractedDataVerifier."""

    def test_verifier_accepts_valid_cv_data(self, tmp_path):
        """Valid CV data should pass verification."""
        verifier = get_verifier("private-internal-verifier")
        data = {
            "identity": {
                "title": "Senior Engineer",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe",
            },
            "sidebar": {
                "languages": ["Python", "Java"],
                "tools": ["Docker"],
                "industries": ["Tech"],
                "spoken_languages": ["English"],
                "academic_background": ["BS CS"],
            },
            "experiences": [
                {
                    "heading": "2020-Present | Engineer",
                    "description": "Software development",
                    "bullets": ["Built features"],
                    "environment": ["Python"],
                }
            ],
        }
        work = _make_work(tmp_path, data)
        result = verifier.verify(work)
        status = _status(result, StepName.Extract)
        assert status.errors == []

    def test_verifier_detects_missing_identity_fields(self, tmp_path):
        """Missing identity fields should cause verification to fail."""
        verifier = ExtractedDataVerifier()
        data = {
            "identity": {"title": "Engineer"},  # Missing other required fields
            "sidebar": {"languages": ["Python"]},
            "experiences": [{"heading": "h", "description": "d"}],
        }
        work = _make_work(tmp_path, data)
        result = verifier.verify(work)
        status = _status(result, StepName.Extract)
        assert "identity" in status.errors

    def test_verifier_warns_about_missing_sidebar_sections(self, tmp_path):
        """Missing sidebar sections should generate warnings."""
        verifier = ExtractedDataVerifier()
        data = {
            "identity": {
                "title": "T",
                "full_name": "N",
                "first_name": "F",
                "last_name": "L",
            },
            "sidebar": {"languages": ["Python"]},  # Missing other sections
            "experiences": [{"heading": "h", "description": "d"}],
        }
        work = _make_work(tmp_path, data)
        result = verifier.verify(work)
        status = _status(result, StepName.Extract)
        assert any("missing sidebar" in w for w in status.warnings)

    def test_verifier_reports_missing_output_path(self, tmp_path):
        """Missing output path should surface as error."""
        verifier = ExtractedDataVerifier()
        work = UnitOfWork(config=UserConfig(target_dir=tmp_path))
        status = work.ensure_step_status(StepName.Extract)
        status.input = tmp_path / "input.json"
        work.current_step = StepName.Extract
        result = verifier.verify(work)
        status = _status(result, StepName.Extract)
        assert any("path is not set" in e for e in status.errors)

    def test_verifier_reports_missing_output_file(self, tmp_path):
        """Missing output file should surface as error."""
        verifier = ExtractedDataVerifier()
        output_path = tmp_path / "missing.json"
        work = UnitOfWork(config=UserConfig(target_dir=tmp_path))
        work.set_step_paths(StepName.Extract, input_path=output_path, output_path=output_path)
        work.current_step = StepName.Extract
        result = verifier.verify(work)
        status = _status(result, StepName.Extract)
        assert any("not found" in e for e in status.errors)

    def test_verifier_reports_unreadable_output(self, tmp_path):
        """Unreadable JSON should surface as error."""
        verifier = ExtractedDataVerifier()
        output_path = tmp_path / "bad.json"
        output_path.write_text("{invalid", encoding="utf-8")
        work = UnitOfWork(config=UserConfig(target_dir=tmp_path))
        work.set_step_paths(StepName.Extract, input_path=output_path, output_path=output_path)
        work.current_step = StepName.Extract
        result = verifier.verify(work)
        status = _status(result, StepName.Extract)
        assert any("unreadable" in e for e in status.errors)

    def test_verifier_reports_non_object_json(self, tmp_path):
        """Non-object JSON should surface as error."""
        verifier = ExtractedDataVerifier()
        output_path = tmp_path / "list.json"
        output_path.write_text("[1, 2, 3]", encoding="utf-8")
        work = UnitOfWork(config=UserConfig(target_dir=tmp_path))
        work.set_step_paths(StepName.Extract, input_path=output_path, output_path=output_path)
        work.current_step = StepName.Extract
        result = verifier.verify(work)
        status = _status(result, StepName.Extract)
        assert any("must be an object" in e for e in status.errors)

    def test_verifier_warns_on_incomplete_experience_fields(self, tmp_path):
        """Missing experience fields should be reported in warnings."""
        verifier = ExtractedDataVerifier()
        data = {
            "identity": {
                "title": "T",
                "full_name": "F L",
                "first_name": "F",
                "last_name": "L",
            },
            "sidebar": {
                "languages": ["Python"],
                "tools": ["x"],
                "industries": ["x"],
                "spoken_languages": ["EN"],
                "academic_background": ["x"],
            },
            "experiences": [{"heading": "", "description": ""}],
        }
        work = _make_work(tmp_path, data)
        result = verifier.verify(work)
        status = _status(result, StepName.Extract)
        assert any("incomplete" in w for w in status.warnings)


class TestRoundtripVerifier:
    """Tests for RoundtripVerifier."""

    def test_verifier_accepts_identical_structures(self, tmp_path):
        """Identical structures should pass comparison."""
        verifier = RoundtripVerifier()
        data = {"x": 1, "y": [1, 2], "z": {"k": "v"}}
        work = _make_roundtrip_work(tmp_path, data, data)
        result = verifier.verify(work)
        status = _status(result, StepName.RoundtripComparer)
        assert status.errors == []

    def test_verifier_detects_missing_keys(self, tmp_path):
        """Missing keys in target should be detected."""
        verifier = RoundtripVerifier()
        source = {"x": 1, "y": 2}
        target = {"x": 1}
        work = _make_roundtrip_work(tmp_path, source, target)
        result = verifier.verify(work)
        status = _status(result, StepName.RoundtripComparer)
        assert any("missing key" in e for e in status.errors)

    def test_verifier_detects_value_mismatches(self, tmp_path):
        """Value differences should be detected."""
        verifier = RoundtripVerifier()
        source = {"x": 1}
        target = {"x": 2}
        work = _make_roundtrip_work(tmp_path, source, target)
        result = verifier.verify(work)
        status = _status(result, StepName.RoundtripComparer)
        assert any("value mismatch" in e for e in status.errors)

    def test_verifier_normalizes_environment_fields(self, tmp_path):
        """Environment fields with different separators should be equivalent."""
        verifier = RoundtripVerifier()
        source = {
            "experiences": [
                {"environment": ["Java, Python, Docker"]},
            ]
        }
        target = {
            "experiences": [
                {"environment": ["Java • Python • Docker"]},
            ]
        }
        work = _make_roundtrip_work(tmp_path, source, target)
        result = verifier.verify(work)
        status = _status(result, StepName.RoundtripComparer)
        assert status.errors == []

    def test_verifier_requires_target_data_parameter(self, tmp_path):
        """Verifier should report missing target data when output is unset."""
        verifier = RoundtripVerifier()
        source_path = tmp_path / "source.json"
        source_path.write_text(json.dumps({"x": 1}), encoding="utf-8")
        work = UnitOfWork(config=UserConfig(target_dir=tmp_path))
        status = work.ensure_step_status(StepName.RoundtripComparer)
        status.input = source_path
        work.current_step = StepName.RoundtripComparer
        work.ensure_step_status(StepName.RoundtripComparer)
        result = verifier.verify(work)
        status = _status(result, StepName.RoundtripComparer)
        assert any("target" in e for e in status.errors)

    def test_verifier_reports_missing_source_file(self, tmp_path):
        """Missing source file should surface as error."""
        verifier = RoundtripVerifier()
        source_path = tmp_path / "missing.json"
        target_path = tmp_path / "target.json"
        target_path.write_text(json.dumps({"x": 1}), encoding="utf-8")

        work = UnitOfWork(config=UserConfig(target_dir=tmp_path))
        work.set_step_paths(
            StepName.RoundtripComparer, input_path=source_path, output_path=target_path
        )
        work.current_step = StepName.RoundtripComparer
        work.ensure_step_status(StepName.RoundtripComparer)
        result = verifier.verify(work)
        status = _status(result, StepName.RoundtripComparer)
        assert any("source JSON not found" in e for e in status.errors)

    def test_verifier_reports_unreadable_source(self, tmp_path):
        """Unreadable JSON should surface as error."""
        verifier = RoundtripVerifier()
        source_path = tmp_path / "source.json"
        source_path.write_text("{bad", encoding="utf-8")
        target_path = tmp_path / "target.json"
        target_path.write_text(json.dumps({"x": 1}), encoding="utf-8")

        work = UnitOfWork(config=UserConfig(target_dir=tmp_path))
        work.set_step_paths(
            StepName.RoundtripComparer, input_path=source_path, output_path=target_path
        )
        work.current_step = StepName.RoundtripComparer
        work.ensure_step_status(StepName.RoundtripComparer)
        result = verifier.verify(work)
        status = _status(result, StepName.RoundtripComparer)
        assert any("unreadable" in e for e in status.errors)


class TestCVSchemaVerifier:
    """Tests for CVSchemaVerifier."""

    def test_verifier_accepts_valid_schema_data(self, tmp_path):
        """Data conforming to schema should pass validation."""
        verifier = CVSchemaVerifier()
        data = {
            "identity": {
                "title": "Engineer",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe",
            },
            "sidebar": {
                "languages": ["Python"],
            },
            "overview": "Experienced engineer",
            "experiences": [
                {
                    "heading": "2020-Present | Engineer",
                    "description": "Development work",
                    "bullets": ["Feature 1"],
                    "environment": ["Python", "Docker"],
                }
            ],
        }
        result = _verify_data(verifier, tmp_path, data)
        status = _status(result, StepName.Extract)
        assert status.errors == []

    def test_schema_verifier_reports_missing_output_path(self, tmp_path):
        """Missing output path should surface as error."""
        verifier = CVSchemaVerifier()
        work = UnitOfWork(config=UserConfig(target_dir=tmp_path))
        status = work.ensure_step_status(StepName.Extract)
        status.input = tmp_path / "input.json"
        work.current_step = StepName.Extract
        result = verifier.verify(work)
        status = _status(result, StepName.Extract)
        assert any("path is not set" in e for e in status.errors)

    def test_schema_verifier_reports_missing_output_file(self, tmp_path):
        """Missing output file should surface as error."""
        verifier = CVSchemaVerifier()
        output_path = tmp_path / "missing.json"
        work = UnitOfWork(config=UserConfig(target_dir=tmp_path))
        work.set_step_paths(StepName.Extract, input_path=output_path, output_path=output_path)
        work.current_step = StepName.Extract
        result = verifier.verify(work)
        status = _status(result, StepName.Extract)
        assert any("not found" in e for e in status.errors)

    def test_schema_verifier_reports_unreadable_output(self, tmp_path):
        """Unreadable JSON should surface as error."""
        verifier = CVSchemaVerifier()
        output_path = tmp_path / "bad.json"
        output_path.write_text("{invalid", encoding="utf-8")
        work = UnitOfWork(config=UserConfig(target_dir=tmp_path))
        work.set_step_paths(StepName.Extract, input_path=output_path, output_path=output_path)
        work.current_step = StepName.Extract
        result = verifier.verify(work)
        status = _status(result, StepName.Extract)
        assert any("unreadable" in e for e in status.errors)

    def test_schema_verifier_reports_non_object_json(self, tmp_path):
        """Non-object JSON should surface as error."""
        verifier = CVSchemaVerifier()
        output_path = tmp_path / "list.json"
        output_path.write_text("[1, 2, 3]", encoding="utf-8")
        work = UnitOfWork(config=UserConfig(target_dir=tmp_path))
        work.set_step_paths(StepName.Extract, input_path=output_path, output_path=output_path)
        work.current_step = StepName.Extract
        result = verifier.verify(work)
        status = _status(result, StepName.Extract)
        assert any("must be an object" in e for e in status.errors)

    def test_verifier_detects_missing_required_fields(self, tmp_path):
        """Missing required fields should fail validation."""
        verifier = CVSchemaVerifier()
        data = {"sidebar": {}}  # Missing required fields
        result = _verify_data(verifier, tmp_path, data)
        status = _status(result, StepName.Extract)
        assert any("missing required field" in e for e in status.errors)

    def test_verifier_detects_invalid_types(self, tmp_path):
        """Invalid field types should fail validation."""
        verifier = CVSchemaVerifier()
        data = {
            "identity": {
                "title": "Engineer",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe",
            },
            "sidebar": {
                "languages": ["Python"],
            },
            "overview": "Overview",
            "experiences": "not an array",  # Should be array
        }
        result = _verify_data(verifier, tmp_path, data)
        status = _status(result, StepName.Extract)
        assert any("must be an array" in e for e in status.errors)

    def test_verifier_validates_experience_structure(self, tmp_path):
        """Experience entries must have required fields."""
        verifier = CVSchemaVerifier()
        data = {
            "identity": {
                "title": "Engineer",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe",
            },
            "sidebar": {},
            "overview": "Overview",
            "experiences": [{"heading": "Title"}],  # Missing description
        }
        result = _verify_data(verifier, tmp_path, data)
        status = _status(result, StepName.Extract)
        assert any("description" in e for e in status.errors)

    def test_identity_missing_field_when_identity_is_none(self, tmp_path):
        """When identity is None, should detect missing required field."""
        verifier = CVSchemaVerifier()
        data = {
            "identity": None,  # None instead of object
            "sidebar": {},
            "overview": "",
            "experiences": [],
        }
        result = _verify_data(verifier, tmp_path, data)
        status = _status(result, StepName.Extract)
        assert status.errors

    def test_identity_field_empty_string_fails_validation(self, tmp_path):
        """Identity fields must be non-empty strings."""
        verifier = CVSchemaVerifier()
        data = {
            "identity": {
                "title": "",  # Empty string
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe",
            },
            "sidebar": {},
            "overview": "",
            "experiences": [],
        }
        result = _verify_data(verifier, tmp_path, data)
        status = _status(result, StepName.Extract)
        assert any("must be a non-empty string" in e for e in status.errors)

    def test_identity_field_not_string_fails_validation(self, tmp_path):
        """Identity fields must be strings."""
        verifier = CVSchemaVerifier()
        data = {
            "identity": {
                "title": 123,  # Not a string
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe",
            },
            "sidebar": {},
            "overview": "",
            "experiences": [],
        }
        result = _verify_data(verifier, tmp_path, data)
        status = _status(result, StepName.Extract)
        assert status.errors

    def test_sidebar_not_dict_fails_validation(self, tmp_path):
        """Sidebar must be a dict or None."""
        verifier = CVSchemaVerifier()
        data = {
            "identity": {
                "title": "Engineer",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe",
            },
            "sidebar": "not a dict",  # Should be dict or None
            "overview": "",
            "experiences": [],
        }
        result = _verify_data(verifier, tmp_path, data)
        status = _status(result, StepName.Extract)
        assert any("sidebar must be an object" in e for e in status.errors)

    def test_overview_not_string_fails_validation(self, tmp_path):
        """Overview must be string or None."""
        verifier = CVSchemaVerifier()
        data = {
            "identity": {
                "title": "Engineer",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe",
            },
            "sidebar": {},
            "overview": 123,  # Should be string or None
            "experiences": [],
        }
        result = _verify_data(verifier, tmp_path, data)
        status = _status(result, StepName.Extract)
        assert any("overview must be a string" in e for e in status.errors)

    def test_experiences_not_array_fails_validation(self, tmp_path):
        """Experiences must be a list."""
        verifier = CVSchemaVerifier()
        data = {
            "identity": {
                "title": "Engineer",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe",
            },
            "sidebar": {},
            "overview": "",
            "experiences": {"not": "array"},
        }
        result = _verify_data(verifier, tmp_path, data)
        status = _status(result, StepName.Extract)
        assert any("must be an array" in e for e in status.errors)

    def test_experience_item_not_dict_fails_validation(self, tmp_path):
        """Each experience must be a dict."""
        verifier = CVSchemaVerifier()
        data = {
            "identity": {
                "title": "Engineer",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe",
            },
            "sidebar": {},
            "overview": "",
            "experiences": ["not a dict"],
        }
        result = _verify_data(verifier, tmp_path, data)
        status = _status(result, StepName.Extract)
        assert any("must be an object" in e for e in status.errors)

    def test_experience_missing_heading_fails_validation(self, tmp_path):
        """Experience must have heading field."""
        verifier = CVSchemaVerifier()
        data = {
            "identity": {
                "title": "Engineer",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe",
            },
            "sidebar": {},
            "overview": "",
            "experiences": [{"description": "desc"}],
        }
        result = _verify_data(verifier, tmp_path, data)
        status = _status(result, StepName.Extract)
        assert any("heading" in e for e in status.errors)

    def test_experience_heading_not_string_fails_validation(self, tmp_path):
        """Experience heading must be string."""
        verifier = CVSchemaVerifier()
        data = {
            "identity": {
                "title": "Engineer",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe",
            },
            "sidebar": {},
            "overview": "",
            "experiences": [{"heading": 123, "description": "desc"}],
        }
        result = _verify_data(verifier, tmp_path, data)
        status = _status(result, StepName.Extract)
        assert any("heading must be a string" in e for e in status.errors)

    def test_experience_missing_description_fails_validation(self, tmp_path):
        """Experience must have description field."""
        verifier = CVSchemaVerifier()
        data = {
            "identity": {
                "title": "Engineer",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe",
            },
            "sidebar": {},
            "overview": "",
            "experiences": [{"heading": "Title"}],
        }
        result = _verify_data(verifier, tmp_path, data)
        status = _status(result, StepName.Extract)
        assert any("description" in e for e in status.errors)

    def test_experience_description_not_string_fails_validation(self, tmp_path):
        """Experience description must be string."""
        verifier = CVSchemaVerifier()
        data = {
            "identity": {
                "title": "Engineer",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe",
            },
            "sidebar": {},
            "overview": "",
            "experiences": [{"heading": "Title", "description": 123}],
        }
        result = _verify_data(verifier, tmp_path, data)
        status = _status(result, StepName.Extract)
        assert any("description must be a string" in e for e in status.errors)

    def test_experience_bullets_not_array_fails_validation(self, tmp_path):
        """Experience bullets must be array or missing."""
        verifier = CVSchemaVerifier()
        data = {
            "identity": {
                "title": "Engineer",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe",
            },
            "sidebar": {},
            "overview": "",
            "experiences": [
                {"heading": "Title", "description": "desc", "bullets": "not an array"}
            ],
        }
        result = _verify_data(verifier, tmp_path, data)
        status = _status(result, StepName.Extract)
        assert any("bullets must be an array" in e for e in status.errors)

    def test_experience_bullets_items_not_strings_fails_validation(self, tmp_path):
        """Experience bullets items must be strings."""
        verifier = CVSchemaVerifier()
        data = {
            "identity": {
                "title": "Engineer",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe",
            },
            "sidebar": {},
            "overview": "",
            "experiences": [
                {"heading": "Title", "description": "desc", "bullets": [123, "string"]}
            ],
        }
        result = _verify_data(verifier, tmp_path, data)
        status = _status(result, StepName.Extract)
        assert any("bullets items must be strings" in e for e in status.errors)

    def test_experience_environment_not_array_or_none_fails_validation(self, tmp_path):
        """Experience environment must be array, None, or missing."""
        verifier = CVSchemaVerifier()
        data = {
            "identity": {
                "title": "Engineer",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe",
            },
            "sidebar": {},
            "overview": "",
            "experiences": [
                {
                    "heading": "Title",
                    "description": "desc",
                    "environment": "not an array",
                }
            ],
        }
        result = _verify_data(verifier, tmp_path, data)
        status = _status(result, StepName.Extract)
        assert any("environment must be an array or null" in e for e in status.errors)

    def test_experience_environment_items_not_strings_fails_validation(self, tmp_path):
        """Experience environment items must be strings."""
        verifier = CVSchemaVerifier()
        data = {
            "identity": {
                "title": "Engineer",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe",
            },
            "sidebar": {},
            "overview": "",
            "experiences": [
                {
                    "heading": "Title",
                    "description": "desc",
                    "environment": [123, "Python"],
                }
            ],
        }
        result = _verify_data(verifier, tmp_path, data)
        status = _status(result, StepName.Extract)
        assert any("environment items must be strings" in e for e in status.errors)

    def test_experience_environment_none_passes_validation(self, tmp_path):
        """Experience environment can be None."""
        verifier = CVSchemaVerifier()
        data = {
            "identity": {
                "title": "Engineer",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe",
            },
            "sidebar": {},
            "overview": "",
            "experiences": [
                {"heading": "Title", "description": "desc", "environment": None}
            ],
        }
        result = _verify_data(verifier, tmp_path, data)
        status = _status(result, StepName.Extract)
        assert status.errors == []

    def test_empty_bullets_array_passes_validation(self, tmp_path):
        """Empty bullets array should pass validation."""
        verifier = CVSchemaVerifier()
        data = {
            "identity": {
                "title": "Engineer",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe",
            },
            "sidebar": {},
            "overview": "",
            "experiences": [{"heading": "Title", "description": "desc", "bullets": []}],
        }
        result = _verify_data(verifier, tmp_path, data)
        status = _status(result, StepName.Extract)
        assert status.errors == []

    def test_empty_environment_array_passes_validation(self, tmp_path):
        """Empty environment array should pass validation."""
        verifier = CVSchemaVerifier()
        data = {
            "identity": {
                "title": "Engineer",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe",
            },
            "sidebar": {},
            "overview": "",
            "experiences": [
                {"heading": "Title", "description": "desc", "environment": []}
            ],
        }
        result = _verify_data(verifier, tmp_path, data)
        status = _status(result, StepName.Extract)
        assert status.errors == []


class TestVerifierInterface:
    """Tests for the CVVerifier base interface."""

    def test_custom_verifier_can_be_implemented(self, tmp_path):
        """Custom verifiers can extend CVVerifier."""

        class CustomVerifier(CVVerifier):
            def verify(self, work: UnitOfWork):
                output_path = work.get_step_output(StepName.Extract)
                with output_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                # Simple custom verification
                if "custom_field" in data:
                    return self._record(work, [], [])
                return self._record(work, ["missing custom_field"], [])

        verifier = CustomVerifier()

        # Test with field present
        result = _verify_data(verifier, tmp_path, {"custom_field": "value"})
        status = _status(result, StepName.Extract)
        assert status.errors == []

        # Test with field missing
        result = _verify_data(verifier, tmp_path, {})
        status = _status(result, StepName.Extract)
        assert "missing custom_field" in status.errors


class TestParameterPassing:
    """Tests for passing data as parameters from external sources."""

    def test_extracted_verifier_accepts_external_data(self, tmp_path):
        """Verifier should accept data from any source."""
        verifier = ExtractedDataVerifier()

        # Simulate loading from external source
        external_data = {
            "identity": {
                "title": "T",
                "full_name": "N",
                "first_name": "F",
                "last_name": "L",
            },
            "sidebar": {"languages": ["Python"]},
            "experiences": [{"heading": "h", "description": "d"}],
        }

        result = _verify_data(verifier, tmp_path, external_data)
        assert isinstance(result, UnitOfWork)

    def test_roundtrip_verifier_accepts_external_source_and_target(self, tmp_path):
        """Roundtrip verifier should accept both source and target from outside."""
        verifier = RoundtripVerifier()

        # Simulate external data sources
        source_data = {"x": 1, "y": 2}
        target_data = {"x": 1, "y": 2}

        work = _make_roundtrip_work(tmp_path, source_data, target_data)
        result = verifier.verify(work)
        status = _status(result, StepName.RoundtripComparer)
        assert status.errors == []
