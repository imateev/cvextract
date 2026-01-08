"""Tests for pipeline helpers."""

import json
from unittest.mock import Mock, patch

import pytest

from cvextract.cli_config import UserConfig
from cvextract.extractors import CVExtractor
from cvextract.pipeline_helpers import extract_cv_data, render_cv_data
from cvextract.shared import StepName, UnitOfWork
from cvextract.verifiers import get_verifier


class _StubExtractor(CVExtractor):
    def __init__(self, data: dict):
        self._data = data

    def extract(self, work: UnitOfWork) -> UnitOfWork:
        return self._write_output_json(work, self._data)


def _make_work(tmp_path, data: dict) -> UnitOfWork:
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


class TestExtractCvData:
    """Tests for extract_cv_data function."""

    def test_extract_cv_data_integrates_all_parsers(self, tmp_path):
        """Test extract_cv_data uses the DocxCVExtractor."""
        mock_docx = tmp_path / "test.docx"
        mock_docx.touch()

        with patch(
            "cvextract.pipeline_helpers.DocxCVExtractor"
        ) as mock_extractor_class:
            work = UnitOfWork(
                config=UserConfig(target_dir=tmp_path),
                input=mock_docx,
                output=tmp_path / "output.json",
            )
            mock_extractor = Mock()
            mock_extractor.extract.return_value = work
            mock_extractor_class.return_value = mock_extractor

            result = extract_cv_data(work)

            assert result == work
            mock_extractor_class.assert_called_once()
            mock_extractor.extract.assert_called_once_with(work)


class TestRenderCvData:
    """Tests for render_cv_data function."""

    def test_render_cv_data_uses_default_renderer(self, tmp_path, make_render_work):
        """Test render_cv_data uses the DocxCVRenderer."""
        mock_template = tmp_path / "template.docx"
        mock_template.touch()
        output_path = tmp_path / "output.docx"

        cv_data = {
            "identity": {
                "title": "Engineer",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe",
            },
            "sidebar": {"languages": ["EN"], "tools": ["Python"]},
            "overview": "Overview text",
            "experiences": [{"heading": "Job", "description": "desc"}],
        }

        work = make_render_work(cv_data, mock_template, output_path)

        with patch("cvextract.pipeline_helpers.get_renderer") as mock_get_renderer:
            mock_renderer = Mock()
            mock_renderer.render.return_value = work
            mock_get_renderer.return_value = mock_renderer

            result = render_cv_data(work)

            assert result == work
            mock_get_renderer.assert_called_once_with("private-internal-renderer")
            mock_renderer.render.assert_called_once_with(work)

    def test_render_cv_data_returns_unit_of_work(self, tmp_path, make_render_work):
        """Test render_cv_data returns the rendered UnitOfWork."""
        mock_template = tmp_path / "template.docx"
        mock_template.touch()
        output_path = tmp_path / "output.docx"

        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}

        work = make_render_work(cv_data, mock_template, output_path)

        with patch("cvextract.pipeline_helpers.get_renderer") as mock_get_renderer:
            mock_renderer = Mock()
            expected_return = work
            mock_renderer.render.return_value = expected_return
            mock_get_renderer.return_value = mock_renderer

            result = render_cv_data(work)

            assert result == expected_return

    def test_render_cv_data_raises_error_when_renderer_not_found(
        self, tmp_path, make_render_work
    ):
        """Test render_cv_data raises ValueError when default renderer is not found."""
        import pytest

        mock_template = tmp_path / "template.docx"
        mock_template.touch()
        output_path = tmp_path / "output.docx"

        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}

        work = make_render_work(cv_data, mock_template, output_path)

        with patch("cvextract.pipeline_helpers.get_renderer") as mock_get_renderer:
            # Simulate renderer not found
            mock_get_renderer.return_value = None

            with pytest.raises(
                ValueError,
                match="Default renderer 'private-internal-renderer' not found",
            ):
                render_cv_data(work)

            mock_get_renderer.assert_called_once_with("private-internal-renderer")


class TestExtractCvDataOutput:
    """Tests for extract_cv_data output behavior."""

    def test_extract_cv_data_requires_output(self, tmp_path):
        """Test extract_cv_data raises when output is not set."""
        mock_docx = tmp_path / "test.docx"
        mock_docx.touch()

        work = UnitOfWork(
            config=UserConfig(target_dir=tmp_path), input=mock_docx, output=None
        )
        extractor = _StubExtractor({"identity": {}})
        with pytest.raises(ValueError, match="output path is not set"):
            extract_cv_data(work, extractor)

    def test_extract_cv_data_with_output_creates_file(self, tmp_path):
        """Test extract_cv_data writes JSON to specified output path."""
        mock_docx = tmp_path / "test.docx"
        mock_docx.touch()
        output_file = tmp_path / "output.json"

        mock_data = {
            "identity": {
                "title": "Senior Dev",
                "full_name": "Bob Smith",
                "first_name": "Bob",
                "last_name": "Smith",
            },
            "sidebar": {"tools": ["Python", "Rust"]},
            "overview": "Experienced developer",
            "experiences": [{"heading": "2020-Present", "description": "Senior role"}],
        }

        work = UnitOfWork(
            config=UserConfig(target_dir=tmp_path),
            input=mock_docx,
            output=output_file,
        )
        extractor = _StubExtractor(mock_data)
        result = extract_cv_data(work, extractor)

        assert result == work
        assert output_file.exists()

        with output_file.open("r", encoding="utf-8") as f:
            saved_data = json.load(f)

        assert saved_data == mock_data

    def test_extract_cv_data_creates_parent_directories(self, tmp_path):
        """Test extract_cv_data creates parent directories if needed."""
        mock_docx = tmp_path / "test.docx"
        mock_docx.touch()

        # Output path with non-existent parent directories
        deep_output = tmp_path / "deep" / "nested" / "dirs" / "output.json"

        mock_data = {
            "identity": {
                "title": "T",
                "full_name": "A B",
                "first_name": "A",
                "last_name": "B",
            },
            "sidebar": {},
            "overview": "",
            "experiences": [],
        }

        work = UnitOfWork(
            config=UserConfig(target_dir=tmp_path),
            input=mock_docx,
            output=deep_output,
        )
        extractor = _StubExtractor(mock_data)
        result = extract_cv_data(work, extractor)

        assert result == work
        assert deep_output.parent.exists()
        assert deep_output.exists()

    def test_extract_cv_data_with_unicode_characters(self, tmp_path):
        """Test extract_cv_data handles Unicode in data correctly."""
        mock_docx = tmp_path / "test.docx"
        mock_docx.touch()
        output_file = tmp_path / "output.json"

        mock_data = {
            "identity": {
                "title": "工程师 (Engineer)",
                "full_name": "José García",
                "first_name": "José",
                "last_name": "García",
            },
            "sidebar": {"languages": ["中文", "English", "Français"]},
            "overview": "Multilingual developer with emoji 🚀",
            "experiences": [{"heading": "2020-Present", "description": "Ðoing çöðé"}],
        }

        work = UnitOfWork(
            config=UserConfig(target_dir=tmp_path),
            input=mock_docx,
            output=output_file,
        )
        extractor = _StubExtractor(mock_data)
        result = extract_cv_data(work, extractor)

        assert result == work

        with output_file.open("r", encoding="utf-8") as f:
            saved_data = json.load(f)

            # Verify Unicode is preserved (ensure_ascii=False)
            assert saved_data["identity"]["title"] == "工程师 (Engineer)"
            assert saved_data["sidebar"]["languages"] == ["中文", "English", "Français"]
            assert "🚀" in saved_data["overview"]

    def test_extract_cv_data_json_formatting(self, tmp_path):
        """Test extract_cv_data writes formatted JSON with proper indentation."""
        mock_docx = tmp_path / "test.docx"
        mock_docx.touch()
        output_file = tmp_path / "output.json"

        mock_data = {
            "identity": {
                "title": "Dev",
                "full_name": "A B",
                "first_name": "A",
                "last_name": "B",
            },
            "sidebar": {"tools": ["Python"]},
            "overview": "Text",
            "experiences": [{"heading": "2020-Now", "description": "Work"}],
        }

        work = UnitOfWork(
            config=UserConfig(target_dir=tmp_path),
            input=mock_docx,
            output=output_file,
        )
        extractor = _StubExtractor(mock_data)
        extract_cv_data(work, extractor)

        with output_file.open("r", encoding="utf-8") as f:
            content = f.read()

            # Verify formatting with indentation
            assert "\n" in content  # Multi-line format
            assert "    " in content  # 2-level indent (indent=2 becomes spaces)


class TestExtractedDataVerification:
    """Tests for verifying extracted CV data structure."""

    def test_verify_complete_valid_data_returns_ok(self, tmp_path):
        """When all required fields are present and valid, should return ok=True."""
        data = {
            "identity": {
                "title": "T",
                "full_name": "A B",
                "first_name": "A",
                "last_name": "B",
            },
            "sidebar": {
                "languages": ["EN"],
                "tools": ["X"],
                "industries": ["Y"],
                "spoken_languages": ["EN"],
                "academic_background": ["Z"],
            },
            "overview": "hi",
            "experiences": [
                {
                    "heading": "Jan 2020 - Present",
                    "description": "d",
                    "bullets": ["b"],
                    "environment": ["Python"],
                }
            ],
        }
        verifier = get_verifier("private-internal-verifier")
        work = _make_work(tmp_path, data)
        res = verifier.verify(work)
        status = res.step_statuses[StepName.Extract]
        assert status.errors == []

    def test_verify_with_missing_identity_returns_error(self, tmp_path):
        """When identity is missing or empty, should return ok=False with error."""
        data = {
            "identity": {},
            "sidebar": {"languages": ["EN"]},
            "overview": "hi",
            "experiences": [{"heading": "h", "description": "d"}],
        }
        verifier = get_verifier("private-internal-verifier")
        work = _make_work(tmp_path, data)
        res = verifier.verify(work)
        status = res.step_statuses[StepName.Extract]
        assert "identity" in status.errors

    def test_verify_with_all_empty_sidebar_sections_returns_error(self, tmp_path):
        """When all sidebar sections are empty, should return ok=False with error."""
        data = {
            "identity": {
                "title": "T",
                "full_name": "A B",
                "first_name": "A",
                "last_name": "B",
            },
            "sidebar": {
                "languages": [],
                "tools": [],
                "industries": [],
                "spoken_languages": [],
                "academic_background": [],
            },
            "overview": "hi",
            "experiences": [{"heading": "h", "description": "d"}],
        }
        verifier = get_verifier("private-internal-verifier")
        work = _make_work(tmp_path, data)
        res = verifier.verify(work)
        status = res.step_statuses[StepName.Extract]
        assert "sidebar" in status.errors

    def test_verify_with_some_missing_sidebar_sections_returns_warning(self, tmp_path):
        """When some sidebar sections are missing, should return ok=True with warning."""
        data = {
            "identity": {
                "title": "T",
                "full_name": "A B",
                "first_name": "A",
                "last_name": "B",
            },
            "sidebar": {"languages": ["EN"]},
            "overview": "hi",
            "experiences": [{"heading": "h", "description": "d"}],
        }
        verifier = get_verifier("private-internal-verifier")
        work = _make_work(tmp_path, data)
        res = verifier.verify(work)
        status = res.step_statuses[StepName.Extract]
        assert any("missing sidebar" in w for w in status.warnings)

    def test_verify_with_invalid_environment_format_returns_warning(self, tmp_path):
        """When environment is not a list or None, should return ok=True with warning."""
        data = {
            "identity": {
                "title": "T",
                "full_name": "A B",
                "first_name": "A",
                "last_name": "B",
            },
            "sidebar": {"languages": ["EN"]},
            "overview": "hi",
            "experiences": [
                {"heading": "h", "description": "d", "environment": "Python"}
            ],  # should be list or None
        }
        verifier = get_verifier("private-internal-verifier")
        work = _make_work(tmp_path, data)
        res = verifier.verify(work)
        status = res.step_statuses[StepName.Extract]
        assert any("invalid environment format" in w for w in status.warnings)

    def test_verify_with_no_experiences_returns_error(self, tmp_path):
        """When experiences list is empty, should return ok=False with error."""
        data = {
            "identity": {
                "title": "T",
                "full_name": "A B",
                "first_name": "A",
                "last_name": "B",
            },
            "sidebar": {"languages": ["EN"]},
            "overview": "hi",
            "experiences": [],
        }
        verifier = get_verifier("private-internal-verifier")
        work = _make_work(tmp_path, data)
        res = verifier.verify(work)
        status = res.step_statuses[StepName.Extract]
        assert "experiences_empty" in status.errors
