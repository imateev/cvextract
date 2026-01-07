"""Tests for the new verifier architecture."""

import pytest

from cvextract.shared import VerificationResult
from cvextract.verifiers import (
    CVVerifier,
    get_verifier,
)
from cvextract.verifiers.roundtrip_verifier import RoundtripVerifier
from cvextract.verifiers.default_expected_cv_data_verifier import ExtractedDataVerifier
from cvextract.verifiers.default_cv_schema_verifier import CVSchemaVerifier


class TestExtractedDataVerifier:
    """Tests for ExtractedDataVerifier."""

    def test_verifier_accepts_valid_cv_data(self):
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
        result = verifier.verify(data=data)
        assert result.ok is True
        assert result.errors == []

    def test_verifier_detects_missing_identity_fields(self):
        """Missing identity fields should cause verification to fail."""
        verifier = ExtractedDataVerifier()
        data = {
            "identity": {"title": "Engineer"},  # Missing other required fields
            "sidebar": {"languages": ["Python"]},
            "experiences": [{"heading": "h", "description": "d"}],
        }
        result = verifier.verify(data=data)
        assert result.ok is False
        assert "identity" in result.errors

    def test_verifier_warns_about_missing_sidebar_sections(self):
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
        result = verifier.verify(data=data)
        assert result.ok is True  # Warnings don't fail verification
        assert any("missing sidebar" in w for w in result.warnings)


class TestRoundtripVerifier:
    """Tests for RoundtripVerifier."""

    def test_verifier_accepts_identical_structures(self):
        """Identical structures should pass comparison."""
        verifier = RoundtripVerifier()
        data = {"x": 1, "y": [1, 2], "z": {"k": "v"}}
        result = verifier.verify(data=data, target_data=data)
        assert result.ok is True
        assert result.errors == []

    def test_verifier_detects_missing_keys(self):
        """Missing keys in target should be detected."""
        verifier = RoundtripVerifier()
        source = {"x": 1, "y": 2}
        target = {"x": 1}
        result = verifier.verify(data=source, target_data=target)
        assert result.ok is False
        assert any("missing key" in e for e in result.errors)

    def test_verifier_detects_value_mismatches(self):
        """Value differences should be detected."""
        verifier = RoundtripVerifier()
        source = {"x": 1}
        target = {"x": 2}
        result = verifier.verify(data=source, target_data=target)
        assert result.ok is False
        assert any("value mismatch" in e for e in result.errors)

    def test_verifier_normalizes_environment_fields(self):
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
        result = verifier.verify(data=source, target_data=target)
        assert result.ok is True

    def test_verifier_requires_target_data_parameter(self):
        """Verifier should raise error if target_data is missing."""
        verifier = RoundtripVerifier()
        with pytest.raises(ValueError, match="target_data"):
            verifier.verify(data={"x": 1})


class TestCVSchemaVerifier:
    """Tests for CVSchemaVerifier."""

    def test_verifier_accepts_valid_schema_data(self):
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
        result = verifier.verify(data=data)
        assert result.ok is True
        assert result.errors == []

    def test_verifier_detects_missing_required_fields(self):
        """Missing required fields should fail validation."""
        verifier = CVSchemaVerifier()
        data = {"sidebar": {}}  # Missing required fields
        result = verifier.verify(data=data)
        assert result.ok is False
        assert any("missing required field" in e for e in result.errors)

    def test_verifier_detects_invalid_types(self):
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
        result = verifier.verify(data=data)
        assert result.ok is False
        assert any("must be an array" in e for e in result.errors)

    def test_verifier_validates_experience_structure(self):
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
        result = verifier.verify(data=data)
        assert result.ok is False
        assert any("description" in e for e in result.errors)

    def test_identity_missing_field_when_identity_is_none(self):
        """When identity is None, should detect missing required field."""
        verifier = CVSchemaVerifier()
        data = {
            "identity": None,  # None instead of object
            "sidebar": {},
            "overview": "",
            "experiences": [],
        }
        result = verifier.verify(data=data)
        assert result.ok is False

    def test_identity_field_empty_string_fails_validation(self):
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
        result = verifier.verify(data=data)
        assert result.ok is False
        assert any("must be a non-empty string" in e for e in result.errors)

    def test_identity_field_not_string_fails_validation(self):
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
        result = verifier.verify(data=data)
        assert result.ok is False

    def test_sidebar_not_dict_fails_validation(self):
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
        result = verifier.verify(data=data)
        assert result.ok is False
        assert any("sidebar must be an object" in e for e in result.errors)

    def test_overview_not_string_fails_validation(self):
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
        result = verifier.verify(data=data)
        assert result.ok is False
        assert any("overview must be a string" in e for e in result.errors)

    def test_experiences_not_array_fails_validation(self):
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
        result = verifier.verify(data=data)
        assert result.ok is False
        assert any("must be an array" in e for e in result.errors)

    def test_experience_item_not_dict_fails_validation(self):
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
        result = verifier.verify(data=data)
        assert result.ok is False
        assert any("must be an object" in e for e in result.errors)

    def test_experience_missing_heading_fails_validation(self):
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
        result = verifier.verify(data=data)
        assert result.ok is False
        assert any("heading" in e for e in result.errors)

    def test_experience_heading_not_string_fails_validation(self):
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
        result = verifier.verify(data=data)
        assert result.ok is False
        assert any("heading must be a string" in e for e in result.errors)

    def test_experience_missing_description_fails_validation(self):
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
        result = verifier.verify(data=data)
        assert result.ok is False
        assert any("description" in e for e in result.errors)

    def test_experience_description_not_string_fails_validation(self):
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
        result = verifier.verify(data=data)
        assert result.ok is False
        assert any("description must be a string" in e for e in result.errors)

    def test_experience_bullets_not_array_fails_validation(self):
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
        result = verifier.verify(data=data)
        assert result.ok is False
        assert any("bullets must be an array" in e for e in result.errors)

    def test_experience_bullets_items_not_strings_fails_validation(self):
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
        result = verifier.verify(data=data)
        assert result.ok is False
        assert any("bullets items must be strings" in e for e in result.errors)

    def test_experience_environment_not_array_or_none_fails_validation(self):
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
        result = verifier.verify(data=data)
        assert result.ok is False
        assert any("environment must be an array or null" in e for e in result.errors)

    def test_experience_environment_items_not_strings_fails_validation(self):
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
        result = verifier.verify(data=data)
        assert result.ok is False
        assert any("environment items must be strings" in e for e in result.errors)

    def test_experience_environment_none_passes_validation(self):
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
        result = verifier.verify(data=data)
        assert result.ok is True

    def test_empty_bullets_array_passes_validation(self):
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
        result = verifier.verify(data=data)
        assert result.ok is True

    def test_empty_environment_array_passes_validation(self):
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
        result = verifier.verify(data=data)
        assert result.ok is True


class TestVerifierInterface:
    """Tests for the CVVerifier base interface."""

    def test_custom_verifier_can_be_implemented(self):
        """Custom verifiers can extend CVVerifier."""

        class CustomVerifier(CVVerifier):
            def verify(self, **kwargs):
                data = kwargs.get("data")
                if data is None:
                    raise ValueError("CustomVerifier requires a 'data' parameter.")
                # Simple custom verification
                if "custom_field" in data:
                    return VerificationResult(ok=True, errors=[], warnings=[])
                return VerificationResult(
                    ok=False, errors=["missing custom_field"], warnings=[]
                )

        verifier = CustomVerifier()

        # Test with field present
        result = verifier.verify(data={"custom_field": "value"})
        assert result.ok is True

        # Test with field missing
        result = verifier.verify(data={})
        assert result.ok is False
        assert "missing custom_field" in result.errors


class TestParameterPassing:
    """Tests for passing data as parameters from external sources."""

    def test_extracted_verifier_accepts_external_data(self):
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

        result = verifier.verify(data=external_data)
        assert isinstance(result, VerificationResult)

    def test_roundtrip_verifier_accepts_external_source_and_target(self):
        """Roundtrip verifier should accept both source and target from outside."""
        verifier = RoundtripVerifier()

        # Simulate external data sources
        source_data = {"x": 1, "y": 2}
        target_data = {"x": 1, "y": 2}

        result = verifier.verify(data=source_data, target_data=target_data)
        assert result.ok is True
