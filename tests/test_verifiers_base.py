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
from cvextract.shared import StepName, UnitOfWork
from cvextract.verifiers.base import CVVerifier


class TestCVVerifierAbstract:
    """Tests for CVVerifier abstract base class."""

    @staticmethod
    def _make_work(tmp_path, data: Dict[str, Any]) -> UnitOfWork:
        path = tmp_path / "data.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        work = UnitOfWork(
            config=UserConfig(target_dir=tmp_path),
            input=path,
            output=path,
        )
        work.current_step = StepName.Extract
        work.ensure_step_status(StepName.Extract)
        return work

    @staticmethod
    def _status(work: UnitOfWork):
        return work.step_statuses[StepName.Extract]

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

            def verify(self, work: UnitOfWork) -> UnitOfWork:
                return self._record(work, [], [])

        verifier = ConcreteVerifier()
        work = self._make_work(tmp_path, {})
        result = verifier.verify(work)
        assert isinstance(result, UnitOfWork)
        assert self._status(result).errors == []
        assert self._status(result).warnings == []

    def test_verify_method_signature_accepts_unit_of_work(self, tmp_path):
        """Test that verify() accepts a UnitOfWork instance."""

        class TestVerifier(CVVerifier):
            def verify(self, work: UnitOfWork) -> UnitOfWork:
                assert isinstance(work, UnitOfWork)
                return self._record(work, [], [])

        verifier = TestVerifier()
        work = self._make_work(tmp_path, {"identity": {}})
        result = verifier.verify(work)
        assert self._status(result).errors == []

    def test_verify_can_return_errors(self, tmp_path):
        """Test that verify() can record errors."""

        class FailingVerifier(CVVerifier):
            def verify(self, work: UnitOfWork) -> UnitOfWork:
                return self._record(work, ["Missing identity"], [])

        verifier = FailingVerifier()
        work = self._make_work(tmp_path, {})
        result = verifier.verify(work)

        assert "Missing identity" in self._status(result).errors

    def test_verify_can_include_warnings(self, tmp_path):
        """Test that verify() can record warnings."""

        class WarningVerifier(CVVerifier):
            def verify(self, work: UnitOfWork) -> UnitOfWork:
                return self._record(work, [], ["No sidebar data"])

        verifier = WarningVerifier()
        work = self._make_work(tmp_path, {})
        result = verifier.verify(work)

        assert "No sidebar data" in self._status(result).warnings

    def test_verify_method_can_raise_exception(self, tmp_path):
        """Test that verify() can raise Exception for verification errors."""

        class ExceptionVerifier(CVVerifier):
            def verify(self, work: UnitOfWork) -> UnitOfWork:
                raise Exception("Verification crashed")

        verifier = ExceptionVerifier()
        work = self._make_work(tmp_path, {})
        with pytest.raises(Exception) as exc_info:
            verifier.verify(work)
        assert "Verification crashed" in str(exc_info.value)

    def test_verify_processes_unit_of_work(self, tmp_path):
        """Test that verify() can inspect and validate data from UnitOfWork."""

        class DataInspectingVerifier(CVVerifier):
            def verify(self, work: UnitOfWork) -> UnitOfWork:
                with work.output.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                errors = []
                if "identity" not in data:
                    errors.append("Missing identity section")

                return self._record(work, errors, [])

        verifier = DataInspectingVerifier()

        # Test with missing identity
        work1 = self._make_work(tmp_path, {})
        result1 = verifier.verify(work1)
        assert "Missing identity section" in self._status(result1).errors

        # Test with identity
        work2 = self._make_work(tmp_path, {"identity": {}})
        result2 = verifier.verify(work2)
        assert self._status(result2).errors == []

    def test_verify_with_full_cv_schema(self, tmp_path):
        """Test verify() with complete CV schema structure."""

        class SchemaVerifier(CVVerifier):
            def verify(self, work: UnitOfWork) -> UnitOfWork:
                with work.output.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                errors = []

                required_sections = ["identity", "sidebar", "overview", "experiences"]
                for section in required_sections:
                    if section not in data:
                        errors.append(f"Missing {section} section")

                return self._record(work, errors, [])

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
        assert self._status(result).errors == []

    def test_verify_with_multiple_warnings(self, tmp_path):
        """Test that verify() can record warnings based on data."""

        class WarningVerifier(CVVerifier):
            def verify(self, work: UnitOfWork) -> UnitOfWork:
                with work.output.open("r", encoding="utf-8") as f:
                    data = json.load(f)

                warnings = []
                if data.get("strict"):
                    warnings.append("Strict mode enabled")

                return self._record(work, [], warnings)

        verifier = WarningVerifier()

        work = self._make_work(tmp_path, {"strict": True})
        result = verifier.verify(work)
        assert "Strict mode enabled" in self._status(result).warnings[0]

    def test_multiple_verifiers_can_coexist(self, tmp_path):
        """Test that multiple concrete verifiers can be defined independently."""

        class SchemaVerifier(CVVerifier):
            def verify(self, work: UnitOfWork) -> UnitOfWork:
                return self._record(work, [], [])

        class CompletenessVerifier(CVVerifier):
            def verify(self, work: UnitOfWork) -> UnitOfWork:
                return self._record(work, [], [])

        schema = SchemaVerifier()
        completeness = CompletenessVerifier()

        work = self._make_work(tmp_path, {})
        result1 = schema.verify(work)
        result2 = completeness.verify(work)

        assert isinstance(result1, UnitOfWork)
        assert isinstance(result2, UnitOfWork)

    def test_verify_method_override_works(self, tmp_path):
        """Test that verify() method can be properly overridden."""

        class BaseVerifier(CVVerifier):
            def verify(self, work: UnitOfWork) -> UnitOfWork:
                return self._record(work, [], ["Base"])

        class DerivedVerifier(BaseVerifier):
            def verify(self, work: UnitOfWork) -> UnitOfWork:
                work = super().verify(work)
                work.add_warning(StepName.Extract, "Derived")
                return work

        verifier = DerivedVerifier()
        work = self._make_work(tmp_path, {})
        result = verifier.verify(work)

        assert "Base" in self._status(result).warnings
        assert "Derived" in self._status(result).warnings

    def test_is_abstract_base_class(self):
        """Test that CVVerifier is an abstract base class."""
        from abc import ABC

        assert issubclass(CVVerifier, ABC)

    def test_verify_is_abstractmethod(self):
        """Test that verify is marked as abstract."""
        from inspect import isabstract

        assert isabstract(CVVerifier)
        assert hasattr(CVVerifier.verify, "__isabstractmethod__")
        assert CVVerifier.verify.__isabstractmethod__

    def test_verify_with_empty_data(self, tmp_path):
        """Test that verify() can handle empty data dict."""

        class TestVerifier(CVVerifier):
            def verify(self, work: UnitOfWork) -> UnitOfWork:
                with work.output.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if not data:
                    return self._record(work, ["Data is empty"], [])
                return self._record(work, [], [])

        verifier = TestVerifier()
        work = self._make_work(tmp_path, {})
        result = verifier.verify(work)

        assert "Data is empty" in self._status(result).errors

    def test_verify_with_multiple_errors(self, tmp_path):
        """Test that verify() can accumulate multiple errors."""

        class MultiErrorVerifier(CVVerifier):
            def verify(self, work: UnitOfWork) -> UnitOfWork:
                with work.output.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                errors = []

                if "field1" not in data:
                    errors.append("Missing field1")
                if "field2" not in data:
                    errors.append("Missing field2")
                if "field3" not in data:
                    errors.append("Missing field3")

                return self._record(work, errors, [])

        verifier = MultiErrorVerifier()
        work = self._make_work(tmp_path, {})
        result = verifier.verify(work)

        assert len(self._status(result).errors) == 3

    def test_verify_implementations_are_independent(self, tmp_path):
        """Test that different implementations don't interfere."""

        class Impl1(CVVerifier):
            def verify(self, work: UnitOfWork) -> UnitOfWork:
                return self._record(work, [], ["V1"])

        class Impl2(CVVerifier):
            def verify(self, work: UnitOfWork) -> UnitOfWork:
                return self._record(work, [], ["V2"])

        impl1 = Impl1()
        impl2 = Impl2()

        work1 = self._make_work(tmp_path, {})
        work2 = self._make_work(tmp_path, {})
        result1 = impl1.verify(work1)
        result2 = impl2.verify(work2)

        assert "V1" in self._status(result1).warnings
        assert "V2" in self._status(result2).warnings

    def test_verify_with_mocked_implementation(self, tmp_path):
        """Test that verify() works correctly when mocked."""

        class TestVerifier(CVVerifier):
            def verify(self, work: UnitOfWork) -> UnitOfWork:
                return self._record(work, [], [])

        verifier = TestVerifier()
        with patch.object(verifier, "verify") as mock_verify:
            work = self._make_work(tmp_path, {})
            work.add_error(StepName.Extract, "Mocked")
            mock_verify.return_value = work

            result = verifier.verify(work)

            assert "Mocked" in self._status(result).errors
            mock_verify.assert_called_once()

    def test_verify_can_validate_specific_fields(self, tmp_path):
        """Test that verify() can validate specific CV fields."""

        class FieldVerifier(CVVerifier):
            def verify(self, work: UnitOfWork) -> UnitOfWork:
                with work.output.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                errors = []

                identity = data.get("identity", {})
                if not identity.get("full_name"):
                    errors.append("Name is required")

                sidebar = data.get("sidebar", {})
                if not sidebar.get("languages"):
                    errors.append("At least one language is required")

                return self._record(work, errors, [])

        verifier = FieldVerifier()

        work1 = self._make_work(tmp_path, {})
        result1 = verifier.verify(work1)
        assert "Name is required" in self._status(result1).errors

        work2 = self._make_work(
            tmp_path,
            {
                "identity": {"full_name": "John Doe"},
                "sidebar": {"languages": ["Python"]},
            },
        )
        result2 = verifier.verify(work2)
        assert self._status(result2).errors == []
