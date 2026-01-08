"""
Tests for CVVerifier abstract base class.

Tests that the abstract interface is properly defined and enforces
correct implementation patterns for concrete verifiers.
"""

import json
from typing import Any, Dict
from unittest.mock import patch

import pytest

from cvextract.cli_config import UserConfig
from cvextract.shared import UnitOfWork, VerificationResult
from cvextract.verifiers.base import CVVerifier


class TestCVVerifierAbstract:
    """Tests for CVVerifier abstract base class."""

    @staticmethod
    def _make_work(tmp_path, data: Dict[str, Any]) -> UnitOfWork:
        path = tmp_path / "data.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return UnitOfWork(
            config=UserConfig(target_dir=tmp_path),
            input=path,
            output=path,
        )

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

    def test_verify_method_can_be_implemented(self, tmp_path):
        """Test that verify() can be properly implemented in concrete class."""

        class ConcreteVerifier(CVVerifier):
            """Concrete implementation of CVVerifier."""

            def verify(self, work: UnitOfWork) -> VerificationResult:
                return VerificationResult(errors=[], warnings=[])

        verifier = ConcreteVerifier()
        work = self._make_work(tmp_path, {})
        result = verifier.verify(work)
        assert isinstance(result, VerificationResult)
        assert result.ok is True

    def test_verify_method_signature_accepts_unit_of_work(self, tmp_path):
        """Test that verify() accepts a UnitOfWork instance."""

        class TestVerifier(CVVerifier):
            def verify(self, work: UnitOfWork) -> VerificationResult:
                assert isinstance(work, UnitOfWork)
                return VerificationResult(errors=[], warnings=[])

        verifier = TestVerifier()
        work = self._make_work(tmp_path, {"identity": {}})
        result = verifier.verify(work)
        assert result.ok is True

    def test_verify_method_returns_verification_result(self, tmp_path):
        """Test that verify() returns a VerificationResult object."""

        class TestVerifier(CVVerifier):
            def verify(self, work: UnitOfWork) -> VerificationResult:
                return VerificationResult(errors=[], warnings=[])

        verifier = TestVerifier()
        work = self._make_work(tmp_path, {})
        result = verifier.verify(work)

        assert isinstance(result, VerificationResult)
        assert hasattr(result, "ok")
        assert hasattr(result, "errors")
        assert hasattr(result, "warnings")

    def test_verify_can_return_failed_result(self, tmp_path):
        """Test that verify() can return a failed VerificationResult."""

        class FailingVerifier(CVVerifier):
            def verify(self, work: UnitOfWork) -> VerificationResult:
                return VerificationResult(errors=["Missing identity"], warnings=[])

        verifier = FailingVerifier()
        work = self._make_work(tmp_path, {})
        result = verifier.verify(work)

        assert result.ok is False
        assert len(result.errors) == 1
        assert "Missing identity" in result.errors

    def test_verify_can_include_warnings(self, tmp_path):
        """Test that verify() can return warnings."""

        class WarningVerifier(CVVerifier):
            def verify(self, work: UnitOfWork) -> VerificationResult:
                return VerificationResult(errors=[], warnings=["No sidebar data"])

        verifier = WarningVerifier()
        work = self._make_work(tmp_path, {})
        result = verifier.verify(work)

        assert result.ok is True
        assert len(result.warnings) == 1
        assert "No sidebar data" in result.warnings

    def test_verify_method_can_raise_exception(self, tmp_path):
        """Test that verify() can raise Exception for verification errors."""

        class ExceptionVerifier(CVVerifier):
            def verify(self, work: UnitOfWork) -> VerificationResult:
                raise Exception("Verification crashed")

        verifier = ExceptionVerifier()
        work = self._make_work(tmp_path, {})
        with pytest.raises(Exception) as exc_info:
            verifier.verify(work)
        assert "Verification crashed" in str(exc_info.value)

    def test_verify_processes_unit_of_work(self, tmp_path):
        """Test that verify() can inspect and validate data from UnitOfWork."""

        class DataInspectingVerifier(CVVerifier):
            def verify(self, work: UnitOfWork) -> VerificationResult:
                with work.output.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                errors = []
                if "identity" not in data:
                    errors.append("Missing identity section")

                return VerificationResult(errors=errors, warnings=[])

        verifier = DataInspectingVerifier()

        # Test with missing identity
        work1 = self._make_work(tmp_path, {})
        result1 = verifier.verify(work1)
        assert result1.ok is False
        assert "Missing identity section" in result1.errors

        # Test with identity
        work2 = self._make_work(tmp_path, {"identity": {}})
        result2 = verifier.verify(work2)
        assert result2.ok is True
        assert len(result2.errors) == 0

    def test_verify_with_full_cv_schema(self, tmp_path):
        """Test verify() with complete CV schema structure."""

        class SchemaVerifier(CVVerifier):
            def verify(self, work: UnitOfWork) -> VerificationResult:
                with work.output.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                errors = []

                # Check main sections
                required_sections = ["identity", "sidebar", "overview", "experiences"]
                for section in required_sections:
                    if section not in data:
                        errors.append(f"Missing {section} section")

                return VerificationResult(errors=errors, warnings=[])

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

        work = self._make_work(tmp_path, complete_data)
        result = verifier.verify(work)
        assert result.ok is True

    def test_verify_with_multiple_warnings(self, tmp_path):
        """Test that verify() can return warnings based on data."""

        class KwargsAwareVerifier(CVVerifier):
            def verify(self, work: UnitOfWork) -> VerificationResult:
                with work.output.open("r", encoding="utf-8") as f:
                    data = json.load(f)

                warnings = []
                if data.get("strict"):
                    warnings.append("Strict mode enabled")

                return VerificationResult(errors=[], warnings=warnings)

        verifier = KwargsAwareVerifier()

        work = self._make_work(tmp_path, {"strict": True})
        result = verifier.verify(work)
        assert result.ok is True
        assert "Strict mode enabled" in result.warnings[0]

    def test_multiple_verifiers_can_coexist(self, tmp_path):
        """Test that multiple concrete verifiers can be defined independently."""

        class SchemaVerifier(CVVerifier):
            def verify(self, work: UnitOfWork) -> VerificationResult:
                return VerificationResult(errors=[], warnings=[])

        class CompletenessVerifier(CVVerifier):
            def verify(self, work: UnitOfWork) -> VerificationResult:
                return VerificationResult(errors=[], warnings=[])

        schema = SchemaVerifier()
        completeness = CompletenessVerifier()

        work = self._make_work(tmp_path, {})
        result1 = schema.verify(work)
        result2 = completeness.verify(work)

        assert isinstance(result1, VerificationResult)
        assert isinstance(result2, VerificationResult)

    def test_verify_method_override_works(self, tmp_path):
        """Test that verify() method can be properly overridden."""

        class BaseVerifier(CVVerifier):
            def verify(self, work: UnitOfWork) -> VerificationResult:
                return VerificationResult(errors=[], warnings=["Base"])

        class DerivedVerifier(BaseVerifier):
            def verify(self, work: UnitOfWork) -> VerificationResult:
                base_result = super().verify(work)
                return VerificationResult(
                    errors=base_result.errors,
                    warnings=base_result.warnings + ["Derived"],
                )

        verifier = DerivedVerifier()
        work = self._make_work(tmp_path, {})
        result = verifier.verify(work)

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

    def test_verify_with_empty_data(self, tmp_path):
        """Test that verify() can handle empty data dict."""

        class TestVerifier(CVVerifier):
            def verify(self, work: UnitOfWork) -> VerificationResult:
                with work.output.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if not data:
                    return VerificationResult(errors=["Data is empty"], warnings=[])
                return VerificationResult(errors=[], warnings=[])

        verifier = TestVerifier()
        work = self._make_work(tmp_path, {})
        result = verifier.verify(work)

        assert result.ok is False
        assert "Data is empty" in result.errors

    def test_verify_with_multiple_errors(self, tmp_path):
        """Test that verify() can accumulate multiple errors."""

        class MultiErrorVerifier(CVVerifier):
            def verify(self, work: UnitOfWork) -> VerificationResult:
                with work.output.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                errors = []

                if "field1" not in data:
                    errors.append("Missing field1")
                if "field2" not in data:
                    errors.append("Missing field2")
                if "field3" not in data:
                    errors.append("Missing field3")

                return VerificationResult(errors=errors, warnings=[])

        verifier = MultiErrorVerifier()
        work = self._make_work(tmp_path, {})
        result = verifier.verify(work)

        assert result.ok is False
        assert len(result.errors) == 3

    def test_verify_implementations_are_independent(self, tmp_path):
        """Test that different implementations don't interfere."""

        class Impl1(CVVerifier):
            def verify(self, work: UnitOfWork) -> VerificationResult:
                return VerificationResult(errors=[], warnings=["V1"])

        class Impl2(CVVerifier):
            def verify(self, work: UnitOfWork) -> VerificationResult:
                return VerificationResult(errors=[], warnings=["V2"])

        impl1 = Impl1()
        impl2 = Impl2()

        work = self._make_work(tmp_path, {})
        result1 = impl1.verify(work)
        result2 = impl2.verify(work)

        assert "V1" in result1.warnings
        assert "V2" in result2.warnings
        assert "V2" not in result1.warnings
        assert "V1" not in result2.warnings

    def test_verify_with_mocked_implementation(self, tmp_path):
        """Test that verify() works correctly when mocked."""

        class TestVerifier(CVVerifier):
            def verify(self, work: UnitOfWork) -> VerificationResult:
                return VerificationResult(errors=[], warnings=[])

        verifier = TestVerifier()
        with patch.object(verifier, "verify") as mock_verify:
            mock_result = VerificationResult(errors=["Mocked"], warnings=[])
            mock_verify.return_value = mock_result

            work = self._make_work(tmp_path, {})
            result = verifier.verify(work)

            assert result.ok is False
            assert "Mocked" in result.errors
            mock_verify.assert_called_once()

    def test_verify_can_validate_specific_fields(self, tmp_path):
        """Test that verify() can validate specific CV fields."""

        class FieldVerifier(CVVerifier):
            def verify(self, work: UnitOfWork) -> VerificationResult:
                with work.output.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                errors = []

                # Check identity fields
                identity = data.get("identity", {})
                if not identity.get("full_name"):
                    errors.append("Name is required")

                # Check sidebar
                sidebar = data.get("sidebar", {})
                if not sidebar.get("languages"):
                    errors.append("At least one language is required")

                return VerificationResult(errors=errors, warnings=[])

        verifier = FieldVerifier()

        # Test with missing fields
        work1 = self._make_work(tmp_path, {})
        result1 = verifier.verify(work1)
        assert result1.ok is False
        assert "Name is required" in result1.errors

        # Test with complete data
        work2 = self._make_work(
            tmp_path,
            {
                "identity": {"full_name": "John Doe"},
                "sidebar": {"languages": ["Python"]},
            },
        )
        result2 = verifier.verify(work2)
        assert result2.ok is True
