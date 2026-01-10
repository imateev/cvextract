"""
Tests for CVExtractor abstract base class.

Tests that the abstract interface is properly defined and enforces
correct implementation patterns for concrete extractors.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cvextract.cli_config import UserConfig
from cvextract.extractors.base import CVExtractor
from cvextract.shared import StepName, UnitOfWork, write_output_json


def _make_work(tmp_path: Path, input_name: str = "input.docx") -> UnitOfWork:
    input_path = tmp_path / input_name
    output_path = tmp_path / f"{input_path.name}.json"
    config = UserConfig(target_dir=tmp_path)
    work = UnitOfWork(config=config, initial_input=input_path)
    work.set_step_paths(
        StepName.Extract, input_path=input_path, output_path=output_path
    )
    return work


class TestCVExtractorAbstract:
    """Tests for CVExtractor abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that CVExtractor cannot be instantiated directly."""
        with pytest.raises(TypeError) as exc_info:
            CVExtractor()
        assert "abstract" in str(exc_info.value).lower()

    def test_extract_method_must_be_implemented(self):
        """Test that extract() is an abstract method requiring implementation."""

        class IncompleteExtractor(CVExtractor):
            """Extractor missing extract() implementation."""

            pass

        with pytest.raises(TypeError):
            IncompleteExtractor()

    def test_extract_method_can_be_implemented(self, tmp_path):
        """Test that extract() can be properly implemented in concrete class."""

        class ConcreteExtractor(CVExtractor):
            """Concrete implementation of CVExtractor."""

            def extract(self, work: UnitOfWork) -> UnitOfWork:
                return write_output_json(work, {"identity": {}}, step=StepName.Extract)

        work = _make_work(tmp_path)
        extractor = ConcreteExtractor()
        result = extractor.extract(work)
        assert isinstance(result, UnitOfWork)
        output_path = work.get_step_output(StepName.Extract)
        assert json.loads(output_path.read_text(encoding="utf-8"))["identity"] == {}

    def test_extract_method_signature_accepts_work(self, tmp_path):
        """Test that extract() accepts a UnitOfWork argument."""

        class TestExtractor(CVExtractor):
            def extract(self, work: UnitOfWork) -> UnitOfWork:
                assert isinstance(work.get_step_input(StepName.Extract), Path)
                return write_output_json(work, {}, step=StepName.Extract)

        extractor = TestExtractor()
        work = _make_work(tmp_path)
        extractor.extract(work)

    def test_extract_method_returns_unit_of_work(self, tmp_path):
        """Test that extract() returns a UnitOfWork."""

        class TestExtractor(CVExtractor):
            def extract(self, work: UnitOfWork) -> UnitOfWork:
                return write_output_json(
                    work,
                    {"identity": {"full_name": "John Doe"}},
                    step=StepName.Extract,
                )

        extractor = TestExtractor()
        work = _make_work(tmp_path)
        result = extractor.extract(work)
        assert isinstance(result, UnitOfWork)

    def test_extract_method_can_raise_file_not_found(self, tmp_path):
        """Test that extract() can raise FileNotFoundError."""

        class TestExtractor(CVExtractor):
            def extract(self, work: UnitOfWork) -> UnitOfWork:
                source = work.get_step_input(StepName.Extract)
                if not source or not source.exists():
                    raise FileNotFoundError(f"File not found: {source}")
                return write_output_json(work, {}, step=StepName.Extract)

        extractor = TestExtractor()
        non_existent = _make_work(tmp_path, input_name="missing.docx")

        with pytest.raises(FileNotFoundError):
            extractor.extract(non_existent)

    def test_extract_method_can_raise_generic_exception(self, tmp_path):
        """Test that extract() can raise generic Exception for extraction errors."""

        class TestExtractor(CVExtractor):
            def extract(self, work: UnitOfWork) -> UnitOfWork:
                raise Exception("Extraction failed")

        extractor = TestExtractor()
        work = _make_work(tmp_path)
        with pytest.raises(Exception) as exc_info:
            extractor.extract(work)
        assert "Extraction failed" in str(exc_info.value)

    def test_concrete_implementation_with_full_schema(self, tmp_path):
        """Test concrete implementation returning full CV schema structure."""

        class FullExtractor(CVExtractor):
            def extract(self, work: UnitOfWork) -> UnitOfWork:
                return write_output_json(
                    work,
                    {
                        "identity": {
                            "title": "Senior Developer",
                            "full_name": "Jane Smith",
                            "first_name": "Jane",
                            "last_name": "Smith",
                        },
                        "sidebar": {
                            "languages": ["Python", "JavaScript"],
                            "tools": ["Git", "Docker"],
                            "certifications": ["AWS"],
                            "industries": ["Tech"],
                            "spoken_languages": ["English", "French"],
                            "academic_background": ["BS Computer Science"],
                        },
                        "overview": "Experienced developer",
                        "experiences": [
                            {
                                "heading": "Software Engineer",
                                "description": "Built systems",
                                "bullets": ["Led team"],
                                "environment": ["Python", "AWS"],
                            }
                        ],
                    },
                    step=StepName.Extract,
                )

        extractor = FullExtractor()
        work = _make_work(tmp_path)
        extractor.extract(work)
        output_path = work.get_step_output(StepName.Extract)
        data = json.loads(output_path.read_text(encoding="utf-8"))

        assert data["identity"]["full_name"] == "Jane Smith"
        assert len(data["sidebar"]["languages"]) == 2
        assert len(data["experiences"]) == 1
        assert data["experiences"][0]["heading"] == "Software Engineer"

    def test_multiple_extractors_can_coexist(self, tmp_path):
        """Test that multiple concrete extractors can be defined independently."""

        class DocxExtractor(CVExtractor):
            def extract(self, work: UnitOfWork) -> UnitOfWork:
                return write_output_json(work, {"format": "docx"}, step=StepName.Extract)

        class PDFExtractor(CVExtractor):
            def extract(self, work: UnitOfWork) -> UnitOfWork:
                return write_output_json(work, {"format": "pdf"}, step=StepName.Extract)

        docx = DocxExtractor()
        pdf = PDFExtractor()

        docx_work = _make_work(tmp_path, input_name="test.docx")
        pdf_work = _make_work(tmp_path, input_name="test.pdf")

        docx.extract(docx_work)
        pdf.extract(pdf_work)

        assert (
            json.loads(
                docx_work.get_step_output(StepName.Extract).read_text(encoding="utf-8")
            )["format"]
            == "docx"
        )
        assert (
            json.loads(
                pdf_work.get_step_output(StepName.Extract).read_text(encoding="utf-8")
            )["format"]
            == "pdf"
        )

    def test_extract_method_can_process_source_path(self, tmp_path):
        """Test that concrete implementation can process the source path."""

        class PathAwareExtractor(CVExtractor):
            def extract(self, work: UnitOfWork) -> UnitOfWork:
                return write_output_json(
                    work,
                    {
                        "source_file": work.get_step_input(StepName.Extract).name,
                        "source_stem": work.get_step_input(StepName.Extract).stem,
                        "source_suffix": work.get_step_input(StepName.Extract).suffix,
                    },
                    step=StepName.Extract,
                )

        extractor = PathAwareExtractor()
        work = _make_work(tmp_path, input_name="my_cv.docx")
        extractor.extract(work)
        output_path = work.get_step_output(StepName.Extract)
        data = json.loads(output_path.read_text(encoding="utf-8"))

        assert data["source_file"] == "my_cv.docx"
        assert data["source_stem"] == "my_cv"
        assert data["source_suffix"] == ".docx"

    def test_extract_with_empty_dict_return(self, tmp_path):
        """Test that extract() can return empty dictionary."""

        class EmptyExtractor(CVExtractor):
            def extract(self, work: UnitOfWork) -> UnitOfWork:
                return write_output_json(work, {}, step=StepName.Extract)

        extractor = EmptyExtractor()
        work = _make_work(tmp_path)
        extractor.extract(work)
        output_path = work.get_step_output(StepName.Extract)
        assert json.loads(output_path.read_text(encoding="utf-8")) == {}

    def test_extract_method_override_works(self, tmp_path):
        """Test that extract() method can be properly overridden."""

        class BaseExtractor(CVExtractor):
            def _build_data(self) -> dict:
                return {"version": 1}

            def extract(self, work: UnitOfWork) -> UnitOfWork:
                return write_output_json(
                    work, self._build_data(), step=StepName.Extract
                )

        class DerivedExtractor(BaseExtractor):
            def _build_data(self) -> dict:
                base_result = super()._build_data()
                base_result["version"] = 2
                return base_result

        extractor = DerivedExtractor()
        work = _make_work(tmp_path)
        extractor.extract(work)
        output_path = work.get_step_output(StepName.Extract)
        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert data["version"] == 2

    def test_is_abstract_base_class(self):
        """Test that CVExtractor is an abstract base class."""
        from abc import ABC

        assert issubclass(CVExtractor, ABC)

    def test_extract_is_abstractmethod(self):
        """Test that extract is marked as abstract."""
        from inspect import isabstract

        # Check that the class is abstract
        assert isabstract(CVExtractor)

        # Check that extract method has abstractmethod marker
        assert hasattr(CVExtractor.extract, "__isabstractmethod__")
        assert CVExtractor.extract.__isabstractmethod__

    def test_extract_can_handle_path_with_spaces(self, tmp_path):
        """Test that extract() can handle paths with spaces."""

        class TestExtractor(CVExtractor):
            def extract(self, work: UnitOfWork) -> UnitOfWork:
                return write_output_json(
                    work,
                    {"filename": work.get_step_input(StepName.Extract).name},
                    step=StepName.Extract,
                )

        extractor = TestExtractor()
        work = _make_work(tmp_path, input_name="My CV File.docx")
        extractor.extract(work)
        output_path = work.get_step_output(StepName.Extract)
        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert data["filename"] == "My CV File.docx"

    def test_concrete_implementations_are_independent(self, tmp_path):
        """Test that different implementations don't interfere."""

        class Impl1(CVExtractor):
            def extract(self, work: UnitOfWork) -> UnitOfWork:
                return write_output_json(work, {"impl": 1}, step=StepName.Extract)

        class Impl2(CVExtractor):
            def extract(self, work: UnitOfWork) -> UnitOfWork:
                return write_output_json(work, {"impl": 2}, step=StepName.Extract)

        impl1 = Impl1()
        impl2 = Impl2()

        work1 = _make_work(tmp_path, input_name="x1.docx")
        work2 = _make_work(tmp_path, input_name="x2.docx")

        impl1.extract(work1)
        impl2.extract(work2)

        assert (
            json.loads(
                work1.get_step_output(StepName.Extract).read_text(encoding="utf-8")
            )["impl"]
            == 1
        )
        assert (
            json.loads(
                work2.get_step_output(StepName.Extract).read_text(encoding="utf-8")
            )["impl"]
            == 2
        )
        assert (
            json.loads(
                work1.get_step_output(StepName.Extract).read_text(encoding="utf-8")
            )["impl"]
            == 1
        )

    def test_extract_with_mocked_implementation(self, tmp_path):
        """Test that extract() works correctly when mocked."""

        class TestExtractor(CVExtractor):
            def extract(self, work: UnitOfWork) -> UnitOfWork:
                return write_output_json(
                    work, {"extracted": True}, step=StepName.Extract
                )

        extractor = TestExtractor()
        work = _make_work(tmp_path)
        with patch.object(extractor, "extract") as mock_extract:
            mock_extract.return_value = work
            result = extractor.extract(work)
            assert result is work
            mock_extract.assert_called_once()
