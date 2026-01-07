"""Tests for CV extractor interfaces and implementations."""

import json
from pathlib import Path

import pytest

from cvextract.cli_config import UserConfig
from cvextract.extractors import CVExtractor, DocxCVExtractor
from cvextract.shared import UnitOfWork


class TestCVExtractorInterface:
    """Tests for the CVExtractor abstract interface."""

    def test_cv_extractor_is_abstract(self):
        """CVExtractor cannot be instantiated directly."""
        with pytest.raises(TypeError):
            CVExtractor()

    def test_cv_extractor_requires_extract_method(self):
        """Subclasses must implement the extract method."""

        class IncompleteCVExtractor(CVExtractor):
            pass

        with pytest.raises(TypeError):
            IncompleteCVExtractor()


class TestDocxCVExtractor:
    """Tests for DocxCVExtractor implementation."""

    def test_docx_extractor_instantiation(self):
        """DocxCVExtractor can be instantiated."""
        extractor = DocxCVExtractor()
        assert isinstance(extractor, CVExtractor)
        assert isinstance(extractor, DocxCVExtractor)

    def test_extract_raises_file_not_found_for_missing_file(self, tmp_path):
        """extract() raises FileNotFoundError for non-existent files."""
        extractor = DocxCVExtractor()
        with pytest.raises(FileNotFoundError):
            work = UnitOfWork(
                config=UserConfig(target_dir=tmp_path),
                input=Path("/nonexistent/file.docx"),
                output=tmp_path / "output.json",
            )
            extractor.extract(work)

    def test_extract_raises_value_error_for_non_docx_file(self, tmp_path):
        """extract() raises ValueError for non-.docx files."""
        extractor = DocxCVExtractor()
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("test")
        with pytest.raises(ValueError, match="must be a .docx file"):
            work = UnitOfWork(
                config=UserConfig(target_dir=tmp_path),
                input=txt_file,
                output=tmp_path / "output.json",
            )
            extractor.extract(work)

    def test_extract_returns_dict_with_required_keys(self, tmp_path, monkeypatch):
        """extract() returns a dictionary with identity, sidebar, overview, experiences."""
        from cvextract.extractors import docx_extractor

        docx_path = tmp_path / "test.docx"
        docx_path.write_text("test")

        monkeypatch.setattr(
            docx_extractor,
            "parse_cv_from_docx_body",
            lambda _: ("overview", [{"heading": "Job"}]),
        )
        monkeypatch.setattr(
            docx_extractor, "extract_all_header_paragraphs", lambda _: ["header"]
        )

        class FakeIdentity:
            def as_dict(self):
                return {
                    "title": "Engineer",
                    "full_name": "Test User",
                    "first_name": "Test",
                    "last_name": "User",
                }

        monkeypatch.setattr(
            docx_extractor,
            "split_identity_and_sidebar",
            lambda _: (FakeIdentity(), {"languages": ["English"]}),
        )

        extractor = DocxCVExtractor()
        work = UnitOfWork(
            config=UserConfig(target_dir=tmp_path),
            input=docx_path,
            output=tmp_path / "output.json",
        )
        extractor.extract(work)
        result = json.loads(work.output.read_text(encoding="utf-8"))

        assert set(result.keys()) == {"identity", "sidebar", "overview", "experiences"}
        assert result["identity"]["full_name"] == "Test User"
        assert result["overview"] == "overview"
        assert result["experiences"] == [{"heading": "Job"}]

    def test_docx_extractor_implements_cv_extractor(self):
        """DocxCVExtractor properly implements CVExtractor interface."""
        extractor = DocxCVExtractor()
        assert hasattr(extractor, "extract")
        assert callable(extractor.extract)


class TestExtractorPluggability:
    """Tests for extractor pluggability and interchangeability."""

    def test_custom_extractor_can_be_created(self, tmp_path):
        """Custom extractors can be created by implementing CVExtractor."""

        class MockCVExtractor(CVExtractor):
            def extract(self, work: UnitOfWork) -> UnitOfWork:
                data = {
                    "identity": {
                        "title": "Mock Title",
                        "full_name": "Mock Name",
                        "first_name": "Mock",
                        "last_name": "Name",
                    },
                    "sidebar": {
                        "languages": ["Python"],
                        "tools": ["Tool1"],
                        "industries": ["Tech"],
                        "spoken_languages": ["English"],
                        "academic_background": ["BS"],
                    },
                    "overview": "Mock overview",
                    "experiences": [
                        {
                            "heading": "2020 - Present",
                            "description": "Mock job",
                            "bullets": ["Did stuff"],
                            "environment": ["Python"],
                        }
                    ],
                }
                return self._write_output_json(work, data)

        extractor = MockCVExtractor()
        work = UnitOfWork(
            config=UserConfig(target_dir=tmp_path),
            input=Path("/any/path"),
            output=tmp_path / "output.json",
        )
        extractor.extract(work)
        result = json.loads(work.output.read_text(encoding="utf-8"))
        assert result["identity"]["title"] == "Mock Title"
        assert "Python" in result["sidebar"]["languages"]
