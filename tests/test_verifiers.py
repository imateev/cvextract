"""Tests for the new verifier architecture."""

import pytest
from pathlib import Path
import json
import tempfile
from cvextract.verifiers import (
    CVVerifier,
    ExtractedDataVerifier,
    ComparisonVerifier,
    FileComparisonVerifier,
    SchemaVerifier,
)
from cvextract.shared import VerificationResult


class TestExtractedDataVerifier:
    """Tests for ExtractedDataVerifier."""

    def test_verifier_accepts_valid_cv_data(self):
        """Valid CV data should pass verification."""
        verifier = ExtractedDataVerifier()
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
        result = verifier.verify(data)
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
        result = verifier.verify(data)
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
        result = verifier.verify(data)
        assert result.ok is True  # Warnings don't fail verification
        assert any("missing sidebar" in w for w in result.warnings)


class TestComparisonVerifier:
    """Tests for ComparisonVerifier."""

    def test_verifier_accepts_identical_structures(self):
        """Identical structures should pass comparison."""
        verifier = ComparisonVerifier()
        data = {"x": 1, "y": [1, 2], "z": {"k": "v"}}
        result = verifier.verify(data, target_data=data)
        assert result.ok is True
        assert result.errors == []

    def test_verifier_detects_missing_keys(self):
        """Missing keys in target should be detected."""
        verifier = ComparisonVerifier()
        source = {"x": 1, "y": 2}
        target = {"x": 1}
        result = verifier.verify(source, target_data=target)
        assert result.ok is False
        assert any("missing key" in e for e in result.errors)

    def test_verifier_detects_value_mismatches(self):
        """Value differences should be detected."""
        verifier = ComparisonVerifier()
        source = {"x": 1}
        target = {"x": 2}
        result = verifier.verify(source, target_data=target)
        assert result.ok is False
        assert any("value mismatch" in e for e in result.errors)

    def test_verifier_normalizes_environment_fields(self):
        """Environment fields with different separators should be equivalent."""
        verifier = ComparisonVerifier()
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
        result = verifier.verify(source, target_data=target)
        assert result.ok is True

    def test_verifier_requires_target_data_parameter(self):
        """Verifier should raise error if target_data is missing."""
        verifier = ComparisonVerifier()
        with pytest.raises(ValueError, match="target_data"):
            verifier.verify({"x": 1})


class TestFileComparisonVerifier:
    """Tests for FileComparisonVerifier."""

    def test_verifier_compares_json_files(self):
        """Verifier should load and compare JSON files."""
        verifier = FileComparisonVerifier()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "source.json"
            target_file = Path(tmpdir) / "target.json"
            
            data = {"identity": {"title": "Engineer"}, "sidebar": {}, "experiences": []}
            
            with source_file.open("w") as f:
                json.dump(data, f)
            with target_file.open("w") as f:
                json.dump(data, f)
            
            result = verifier.verify({}, source_file=source_file, target_file=target_file)
            assert result.ok is True

    def test_verifier_detects_file_differences(self):
        """Verifier should detect differences between files."""
        verifier = FileComparisonVerifier()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "source.json"
            target_file = Path(tmpdir) / "target.json"
            
            source_data = {"x": 1}
            target_data = {"x": 2}
            
            with source_file.open("w") as f:
                json.dump(source_data, f)
            with target_file.open("w") as f:
                json.dump(target_data, f)
            
            result = verifier.verify({}, source_file=source_file, target_file=target_file)
            assert result.ok is False
            assert any("value mismatch" in e for e in result.errors)

    def test_verifier_requires_file_parameters(self):
        """Verifier should raise error if file parameters are missing."""
        verifier = FileComparisonVerifier()
        with pytest.raises(ValueError, match="source_file.*target_file"):
            verifier.verify({})


class TestSchemaVerifier:
    """Tests for SchemaVerifier."""

    def test_verifier_accepts_valid_schema_data(self):
        """Data conforming to schema should pass validation."""
        verifier = SchemaVerifier()
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
        result = verifier.verify(data)
        assert result.ok is True
        assert result.errors == []

    def test_verifier_detects_missing_required_fields(self):
        """Missing required fields should fail validation."""
        verifier = SchemaVerifier()
        data = {"sidebar": {}}  # Missing required fields
        result = verifier.verify(data)
        assert result.ok is False
        assert any("missing required field" in e for e in result.errors)

    def test_verifier_detects_invalid_types(self):
        """Invalid field types should fail validation."""
        verifier = SchemaVerifier()
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
        result = verifier.verify(data)
        assert result.ok is False
        assert any("must be an array" in e for e in result.errors)

    def test_verifier_validates_experience_structure(self):
        """Experience entries must have required fields."""
        verifier = SchemaVerifier()
        data = {
            "identity": {
                "title": "Engineer",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe",
            },
            "sidebar": {},
            "overview": "Overview",
            "experiences": [
                {"heading": "Title"}  # Missing description
            ],
        }
        result = verifier.verify(data)
        assert result.ok is False
        assert any("description" in e for e in result.errors)


class TestVerifierInterface:
    """Tests for the CVVerifier base interface."""

    def test_custom_verifier_can_be_implemented(self):
        """Custom verifiers can extend CVVerifier."""
        
        class CustomVerifier(CVVerifier):
            def verify(self, data, **kwargs):
                # Simple custom verification
                if "custom_field" in data:
                    return VerificationResult(ok=True, errors=[], warnings=[])
                return VerificationResult(
                    ok=False, errors=["missing custom_field"], warnings=[]
                )
        
        verifier = CustomVerifier()
        
        # Test with field present
        result = verifier.verify({"custom_field": "value"})
        assert result.ok is True
        
        # Test with field missing
        result = verifier.verify({})
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
        
        result = verifier.verify(external_data)
        assert isinstance(result, VerificationResult)

    def test_comparison_verifier_accepts_external_source_and_target(self):
        """Comparison verifier should accept both source and target from outside."""
        verifier = ComparisonVerifier()
        
        # Simulate external data sources
        source_data = {"x": 1, "y": 2}
        target_data = {"x": 1, "y": 2}
        
        result = verifier.verify(source_data, target_data=target_data)
        assert result.ok is True
