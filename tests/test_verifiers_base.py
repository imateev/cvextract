"""
Tests for CVVerifier abstract base class.

Tests that the abstract interface is properly defined and enforces
correct implementation patterns for concrete verifiers.
"""

from typing import Any, Dict
from unittest.mock import patch

import pytest

from cvextract.shared import VerificationResult
from cvextract.verifiers.base import CVVerifier


class TestCVVerifierAbstract:
    """Tests for CVVerifier abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that CVVerifier cannot be instantiated directly."""
        with pytest.raises(TypeError) as exc_info:
            CVVerifier()
        assert "abstract" in str(exc_info.value).lower()

    def test_verify_method_must_be_implemented(self):
        """Test that verify() is an abstract method requiring implementation."""

        class IncompleteVerifier(CVVerifier):
            """Verifier missing verify() implementation."""

            pass

        with pytest.raises(TypeError):
            IncompleteVerifier()

    def test_verify_method_can_be_implemented(self):
        """Test that verify() can be properly implemented in concrete class."""

        class ConcreteVerifier(CVVerifier):
            """Concrete implementation of CVVerifier."""

            def verify(self, **kwargs) -> VerificationResult:
                return VerificationResult(ok=True, errors=[], warnings=[])

        verifier = ConcreteVerifier()
        result = verifier.verify(data={})
        assert isinstance(result, VerificationResult)
        assert result.ok is True

    def test_verify_method_signature_accepts_data_and_kwargs(self):
        """Test that verify() accepts data dict and kwargs."""

        class TestVerifier(CVVerifier):
            def verify(self, **kwargs) -> VerificationResult:
                data = kwargs.get("data")
                assert isinstance(data, dict)
                return VerificationResult(ok=True, errors=[], warnings=[])

        verifier = TestVerifier()
        result = verifier.verify(data={"identity": {}}, strict=True, version="1.0")
        assert result.ok is True

    def test_verify_method_returns_verification_result(self):
        """Test that verify() returns a VerificationResult object."""

        class TestVerifier(CVVerifier):
            def verify(self, **kwargs) -> VerificationResult:
                return VerificationResult(ok=True, errors=[], warnings=[])

        verifier = TestVerifier()
        result = verifier.verify(data={})

        assert isinstance(result, VerificationResult)
        assert hasattr(result, "ok")
        assert hasattr(result, "errors")
        assert hasattr(result, "warnings")

    def test_verify_can_return_failed_result(self):
        """Test that verify() can return a failed VerificationResult."""

        class FailingVerifier(CVVerifier):
            def verify(self, **kwargs) -> VerificationResult:
                return VerificationResult(
                    ok=False, errors=["Missing identity"], warnings=[]
                )

        verifier = FailingVerifier()
        result = verifier.verify(data={})

        assert result.ok is False
        assert len(result.errors) == 1
        assert "Missing identity" in result.errors

    def test_verify_can_include_warnings(self):
        """Test that verify() can return warnings."""

        class WarningVerifier(CVVerifier):
            def verify(self, **kwargs) -> VerificationResult:
                return VerificationResult(
                    ok=True, errors=[], warnings=["No sidebar data"]
                )

        verifier = WarningVerifier()
        result = verifier.verify(data={})

        assert result.ok is True
        assert len(result.warnings) == 1
        assert "No sidebar data" in result.warnings

    def test_verify_method_can_raise_exception(self):
        """Test that verify() can raise Exception for verification errors."""

        class ExceptionVerifier(CVVerifier):
            def verify(self, **kwargs) -> VerificationResult:
                raise Exception("Verification crashed")

        verifier = ExceptionVerifier()
        with pytest.raises(Exception) as exc_info:
            verifier.verify(data={})
        assert "Verification crashed" in str(exc_info.value)

    def test_verify_processes_data_parameter(self):
        """Test that verify() can inspect and validate data."""

        class DataInspectingVerifier(CVVerifier):
            def verify(self, **kwargs) -> VerificationResult:
                data = kwargs.get("data") or {}
                errors = []
                if "identity" not in data:
                    errors.append("Missing identity section")

                return VerificationResult(
                    ok=len(errors) == 0, errors=errors, warnings=[]
                )

        verifier = DataInspectingVerifier()

        # Test with missing identity
        result1 = verifier.verify(data={})
        assert result1.ok is False
        assert "Missing identity section" in result1.errors

        # Test with identity
        result2 = verifier.verify(data={"identity": {}})
        assert result2.ok is True
        assert len(result2.errors) == 0

    def test_verify_with_full_cv_schema(self):
        """Test verify() with complete CV schema structure."""

        class SchemaVerifier(CVVerifier):
            def verify(self, **kwargs) -> VerificationResult:
                data = kwargs.get("data") or {}
                errors = []

                # Check main sections
                required_sections = ["identity", "sidebar", "overview", "experiences"]
                for section in required_sections:
                    if section not in data:
                        errors.append(f"Missing {section} section")

                return VerificationResult(
                    ok=len(errors) == 0, errors=errors, warnings=[]
                )

        verifier = SchemaVerifier()

        complete_data = {
            "identity": {
                "title": "Engineer",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe",
            },
            "sidebar": {
                "languages": ["Python"],
                "tools": ["Git"],
                "certifications": [],
                "industries": [],
                "spoken_languages": [],
                "academic_background": [],
            },
            "overview": "Experienced engineer",
            "experiences": [],
        }

        result = verifier.verify(data=complete_data)
        assert result.ok is True

    def test_verify_with_kwargs_parameters(self):
        """Test that verify() handles additional kwargs correctly."""

        class KwargsAwareVerifier(CVVerifier):
            def verify(self, **kwargs) -> VerificationResult:
                strict = kwargs.get("strict", False)
                version = kwargs.get("version", "1.0")

                # Simple verification based on kwargs
                warnings = []
                if strict:
                    warnings.append(f"Strict mode enabled with version {version}")

                return VerificationResult(ok=True, errors=[], warnings=warnings)

        verifier = KwargsAwareVerifier()

        # Test with kwargs
        result = verifier.verify(data={}, strict=True, version="2.0")
        assert result.ok is True
        assert "Strict mode enabled" in result.warnings[0]

    def test_multiple_verifiers_can_coexist(self):
        """Test that multiple concrete verifiers can be defined independently."""

        class SchemaVerifier(CVVerifier):
            def verify(self, **kwargs) -> VerificationResult:
                return VerificationResult(ok=True, errors=[], warnings=[])

        class CompletenessVerifier(CVVerifier):
            def verify(self, **kwargs) -> VerificationResult:
                return VerificationResult(ok=True, errors=[], warnings=[])

        schema = SchemaVerifier()
        completeness = CompletenessVerifier()

        result1 = schema.verify(data={})
        result2 = completeness.verify(data={})

        assert isinstance(result1, VerificationResult)
        assert isinstance(result2, VerificationResult)

    def test_verify_method_override_works(self):
        """Test that verify() method can be properly overridden."""

        class BaseVerifier(CVVerifier):
            def verify(self, **kwargs) -> VerificationResult:
                return VerificationResult(ok=True, errors=[], warnings=["Base"])

        class DerivedVerifier(BaseVerifier):
            def verify(self, **kwargs) -> VerificationResult:
                base_result = super().verify(**kwargs)
                return VerificationResult(
                    ok=base_result.ok,
                    errors=base_result.errors,
                    warnings=base_result.warnings + ["Derived"],
                )

        verifier = DerivedVerifier()
        result = verifier.verify(data={})

        assert len(result.warnings) == 2
        assert "Base" in result.warnings
        assert "Derived" in result.warnings

    def test_is_abstract_base_class(self):
        """Test that CVVerifier is an abstract base class."""
        from abc import ABC

        assert issubclass(CVVerifier, ABC)

    def test_verify_is_abstractmethod(self):
        """Test that verify is marked as abstract."""
        from inspect import isabstract

        # Check that the class is abstract
        assert isabstract(CVVerifier)

        # Check that verify method has abstractmethod marker
        assert hasattr(CVVerifier.verify, "__isabstractmethod__")
        assert CVVerifier.verify.__isabstractmethod__

    def test_verify_with_empty_data(self):
        """Test that verify() can handle empty data dict."""

        class TestVerifier(CVVerifier):
            def verify(self, **kwargs) -> VerificationResult:
                data = kwargs.get("data") or {}
                if not data:
                    return VerificationResult(
                        ok=False, errors=["Data is empty"], warnings=[]
                    )
                return VerificationResult(ok=True, errors=[], warnings=[])

        verifier = TestVerifier()
        result = verifier.verify(data={})

        assert result.ok is False
        assert "Data is empty" in result.errors

    def test_verify_with_multiple_errors(self):
        """Test that verify() can accumulate multiple errors."""

        class MultiErrorVerifier(CVVerifier):
            def verify(self, **kwargs) -> VerificationResult:
                data = kwargs.get("data") or {}
                errors = []

                if "field1" not in data:
                    errors.append("Missing field1")
                if "field2" not in data:
                    errors.append("Missing field2")
                if "field3" not in data:
                    errors.append("Missing field3")

                return VerificationResult(
                    ok=len(errors) == 0, errors=errors, warnings=[]
                )

        verifier = MultiErrorVerifier()
        result = verifier.verify(data={})

        assert result.ok is False
        assert len(result.errors) == 3

    def test_verify_implementations_are_independent(self):
        """Test that different implementations don't interfere."""

        class Impl1(CVVerifier):
            def verify(self, **kwargs) -> VerificationResult:
                return VerificationResult(ok=True, errors=[], warnings=["V1"])

        class Impl2(CVVerifier):
            def verify(self, **kwargs) -> VerificationResult:
                return VerificationResult(ok=True, errors=[], warnings=["V2"])

        impl1 = Impl1()
        impl2 = Impl2()

        result1 = impl1.verify(data={})
        result2 = impl2.verify(data={})

        assert "V1" in result1.warnings
        assert "V2" in result2.warnings
        assert "V2" not in result1.warnings
        assert "V1" not in result2.warnings

    def test_verify_with_mocked_implementation(self):
        """Test that verify() works correctly when mocked."""

        class TestVerifier(CVVerifier):
            def verify(self, **kwargs) -> VerificationResult:
                return VerificationResult(ok=True, errors=[], warnings=[])

        verifier = TestVerifier()
        with patch.object(verifier, "verify") as mock_verify:
            mock_result = VerificationResult(ok=False, errors=["Mocked"], warnings=[])
            mock_verify.return_value = mock_result

            result = verifier.verify(data={})

            assert result.ok is False
            assert "Mocked" in result.errors
            mock_verify.assert_called_once()

    def test_verify_can_validate_specific_fields(self):
        """Test that verify() can validate specific CV fields."""

        class FieldVerifier(CVVerifier):
            def verify(self, **kwargs) -> VerificationResult:
                data = kwargs.get("data") or {}
                errors = []

                # Check identity fields
                identity = data.get("identity", {})
                if not identity.get("full_name"):
                    errors.append("Name is required")

                # Check sidebar
                sidebar = data.get("sidebar", {})
                if not sidebar.get("languages"):
                    errors.append("At least one language is required")

                return VerificationResult(
                    ok=len(errors) == 0, errors=errors, warnings=[]
                )

        verifier = FieldVerifier()

        # Test with missing fields
        result1 = verifier.verify(data={})
        assert result1.ok is False
        assert "Name is required" in result1.errors

        # Test with complete data
        result2 = verifier.verify(data={
                "identity": {"full_name": "John Doe"},
                "sidebar": {"languages": ["Python"]},
            }
        )
        assert result2.ok is True
