"""Tests for improved coverage of pipeline module critical paths."""

import json
from unittest.mock import patch

from cvextract.cli_config import ExtractStage, UserConfig
from cvextract.pipeline_helpers import (
    categorize_result,
    extract_single,
    infer_source_root,
)
from cvextract.shared import (
    StepName,
    StepStatus,
    UnitOfWork,
    get_status_icons,
)


def _write_output(work: UnitOfWork, data: dict) -> UnitOfWork:
    output_path = work.get_step_output(StepName.Extract)
    output_path.write_text(json.dumps(data), encoding="utf-8")
    return work


class TestExtractSingle:
    """Tests for extract_single function."""

    def testextract_single_success(self, tmp_path):
        """Test successful extraction."""
        docx_path = tmp_path / "test.docx"
        out_json = tmp_path / "out.json"
        docx_path.touch()

        # Mock the extraction pipeline
        mock_data = {
            "identity": {
                "title": "Engineer",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe",
            },
            "sidebar": {"languages": ["EN"]},
            "overview": "Text",
            "experiences": [
                {"heading": "Job", "description": "Work", "bullets": ["Item"]}
            ],
        }

        with patch("cvextract.pipeline_helpers.extract_cv_data") as mock_extract:

            def _process(work, extractor=None):
                return _write_output(work, mock_data)

            mock_extract.side_effect = _process
            work = UnitOfWork(
                config=UserConfig(
                    target_dir=tmp_path, extract=ExtractStage(source=docx_path)
                ),
                initial_input=docx_path,
            )
            work.set_step_paths(
                StepName.Extract, input_path=docx_path, output_path=out_json
            )
            result = extract_single(work)
            extract_status = result.step_states[StepName.Extract]

            assert extract_status.errors == []
            assert extract_status.warnings == []

    def testextract_single_invalid_data(self, tmp_path):
        """Test extract_single does not validate extracted content."""
        docx_path = tmp_path / "test.docx"
        out_json = tmp_path / "out.json"
        docx_path.touch()

        mock_data = {"identity": {}}  # Missing required fields

        with patch("cvextract.pipeline_helpers.extract_cv_data") as mock_extract:

            def _process(work, extractor=None):
                return _write_output(work, mock_data)

            mock_extract.side_effect = _process

            work = UnitOfWork(
                config=UserConfig(
                    target_dir=tmp_path, extract=ExtractStage(source=docx_path)
                ),
                initial_input=docx_path,
            )
            work.set_step_paths(
                StepName.Extract, input_path=docx_path, output_path=out_json
            )
            result = extract_single(work)

            extract_status = result.step_states[StepName.Extract]
            assert extract_status.errors == []
            assert extract_status.warnings == []
            output_path = result.get_step_output(StepName.Extract)
            assert output_path and output_path.exists()

    def testextract_single_exception_no_debug(self, tmp_path):
        """Test exception handling without debug mode."""
        docx_path = tmp_path / "test.docx"
        out_json = tmp_path / "out.json"
        docx_path.touch()

        with patch("cvextract.pipeline_helpers.extract_cv_data") as mock_extract:
            mock_extract.side_effect = ValueError("Bad file")

            work = UnitOfWork(
                config=UserConfig(
                    target_dir=tmp_path, extract=ExtractStage(source=docx_path)
                ),
                initial_input=docx_path,
            )
            work.set_step_paths(
                StepName.Extract, input_path=docx_path, output_path=out_json
            )
            result = extract_single(work)
            extract_status = result.step_states[StepName.Extract]

            assert any(
                "exception" in e.lower() or "ValueError" in e
                for e in extract_status.errors
            )

    def testextract_single_exception_with_debug(self, tmp_path):
        """Test exception logging with debug mode enabled."""
        docx_path = tmp_path / "test.docx"
        out_json = tmp_path / "out.json"
        docx_path.touch()

        with patch("cvextract.pipeline_helpers.extract_cv_data") as mock_extract, patch(
            "cvextract.pipeline_helpers.dump_body_sample"
        ):

            mock_extract.side_effect = ValueError("Bad file")

            work = UnitOfWork(
                config=UserConfig(
                    target_dir=tmp_path,
                    extract=ExtractStage(source=docx_path),
                    verbosity="debug",
                ),
                initial_input=docx_path,
            )
            work.set_step_paths(
                StepName.Extract, input_path=docx_path, output_path=out_json
            )
            result = extract_single(work)
            extract_status = result.step_states[StepName.Extract]

            assert extract_status.errors

    def testextract_single_with_warnings(self, tmp_path):
        """Test extract_single does not generate verification warnings."""
        docx_path = tmp_path / "test.docx"
        out_json = tmp_path / "out.json"
        docx_path.touch()

        mock_data = {
            "identity": {
                "title": "T",
                "full_name": "A B",
                "first_name": "A",
                "last_name": "B",
            },
            "sidebar": {"languages": ["EN"]},
            "overview": "Text",
            "experiences": [],
        }

        with patch("cvextract.pipeline_helpers.extract_cv_data") as mock_extract:

            def _process(work, extractor=None):
                return _write_output(work, mock_data)

            mock_extract.side_effect = _process
            work = UnitOfWork(
                config=UserConfig(
                    target_dir=tmp_path, extract=ExtractStage(source=docx_path)
                ),
                initial_input=docx_path,
            )
            work.set_step_paths(
                StepName.Extract, input_path=docx_path, output_path=out_json
            )
            result = extract_single(work)
            extract_status = result.step_states[StepName.Extract]

            assert extract_status.warnings == []


class TestCategorizeResult:
    """Tests for categorize_result function."""

    def test_categorize_extract_failed(self):
        """Test when extraction failed."""
        fully_ok, partial_ok, failed = categorize_result(
            extract_ok=False, has_warns=False, apply_ok=None
        )
        assert (fully_ok, partial_ok, failed) == (0, 0, 1)

    def test_categorize_apply_failed(self):
        """Test when apply failed."""
        fully_ok, partial_ok, failed = categorize_result(
            extract_ok=True, has_warns=False, apply_ok=False
        )
        assert (fully_ok, partial_ok, failed) == (0, 1, 0)

    def test_categorize_with_warnings(self):
        """Test when result has warnings."""
        fully_ok, partial_ok, failed = categorize_result(
            extract_ok=True, has_warns=True, apply_ok=True
        )
        assert (fully_ok, partial_ok, failed) == (0, 1, 0)

    def test_categorize_fully_ok(self):
        """Test fully successful result."""
        fully_ok, partial_ok, failed = categorize_result(
            extract_ok=True, has_warns=False, apply_ok=True
        )
        assert (fully_ok, partial_ok, failed) == (1, 0, 0)

    def test_categorize_apply_none_with_warns(self):
        """Test when apply is None but has warnings."""
        fully_ok, partial_ok, failed = categorize_result(
            extract_ok=True, has_warns=True, apply_ok=None
        )
        assert (fully_ok, partial_ok, failed) == (0, 1, 0)


class TestGetStatusIcons:
    """Tests for get_status_icons function."""

    def test_extract_ok_with_warnings(self, tmp_path):
        """Test extract ok but with warnings."""
        work = UnitOfWork(config=UserConfig(target_dir=tmp_path))
        work.step_states[StepName.Extract] = StepStatus(
            step=StepName.Extract,
            warnings=["warning"],
        )
        work.step_states[StepName.Render] = StepStatus(step=StepName.Render)
        work.step_states[StepName.RoundtripComparer] = StepStatus(
            step=StepName.RoundtripComparer
        )
        icons = get_status_icons(work)
        assert "❎" in icons[StepName.Extract]  # Warning icon for extract

    def test_extract_ok_no_warnings(self, tmp_path):
        """Test extract ok without warnings."""
        work = UnitOfWork(config=UserConfig(target_dir=tmp_path))
        work.step_states[StepName.Extract] = StepStatus(step=StepName.Extract)
        work.step_states[StepName.Render] = StepStatus(step=StepName.Render)
        work.step_states[StepName.RoundtripComparer] = StepStatus(
            step=StepName.RoundtripComparer
        )
        icons = get_status_icons(work)
        assert "🟢" in icons[StepName.Extract]  # Green icon

    def test_extract_failed(self, tmp_path):
        """Test extract failed."""
        work = UnitOfWork(config=UserConfig(target_dir=tmp_path))
        work.step_states[StepName.Extract] = StepStatus(
            step=StepName.Extract,
            errors=["error"],
        )
        work.step_states[StepName.Render] = StepStatus(
            step=StepName.Render,
            errors=["render error"],
        )
        work.step_states[StepName.RoundtripComparer] = StepStatus(
            step=StepName.RoundtripComparer,
            errors=["compare error"],
        )
        icons = get_status_icons(work)
        assert "❌" in icons[StepName.Extract]  # Fail icon

    def test_apply_none(self, tmp_path):
        """Test apply not executed."""
        work = UnitOfWork(config=UserConfig(target_dir=tmp_path))
        work.step_states[StepName.Extract] = StepStatus(step=StepName.Extract)
        icons = get_status_icons(work)
        assert "➖" in icons[StepName.Render]  # Neutral icon for apply

    def test_compare_ok(self, tmp_path):
        """Test compare successful."""
        work = UnitOfWork(config=UserConfig(target_dir=tmp_path))
        work.step_states[StepName.Extract] = StepStatus(step=StepName.Extract)
        work.step_states[StepName.Render] = StepStatus(step=StepName.Render)
        work.step_states[StepName.RoundtripComparer] = StepStatus(
            step=StepName.RoundtripComparer
        )
        icons = get_status_icons(work)
        assert (
            "✅" in icons[StepName.RoundtripComparer]
            or "✓" in icons[StepName.RoundtripComparer]
        )

    def test_compare_failed(self, tmp_path):
        """Test compare found differences."""
        work = UnitOfWork(config=UserConfig(target_dir=tmp_path))
        work.step_states[StepName.Extract] = StepStatus(step=StepName.Extract)
        work.step_states[StepName.Render] = StepStatus(step=StepName.Render)
        work.step_states[StepName.RoundtripComparer] = StepStatus(
            step=StepName.RoundtripComparer,
            errors=["compare mismatch"],
        )
        icons = get_status_icons(work)
        assert "❌" in icons[StepName.RoundtripComparer]  # Error for compare mismatch

    def test_compare_none(self, tmp_path):
        """Test compare not executed."""
        work = UnitOfWork(config=UserConfig(target_dir=tmp_path))
        work.step_states[StepName.Extract] = StepStatus(step=StepName.Extract)
        work.step_states[StepName.Render] = StepStatus(step=StepName.Render)
        icons = get_status_icons(work)
        assert "➖" in icons[StepName.RoundtripComparer]


class TestInferSourceRoot:
    """Tests for infer_source_root function."""

    def test_infer_from_single_file(self, tmp_path):
        """Test inferring root from single JSON file."""
        json_file = tmp_path / "data.json"
        json_file.touch()

        root = infer_source_root([json_file])
        assert root == tmp_path

    def test_infer_from_nested_files(self, tmp_path):
        """Test inferring root from nested JSON files."""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        file1 = dir1 / "data1.json"
        file2 = dir2 / "data2.json"
        file1.touch()
        file2.touch()

        root = infer_source_root([file1, file2])
        assert root == tmp_path

    def test_infer_with_deeply_nested_files(self, tmp_path):
        """Test inferring root with deeply nested files."""
        deep_dir = tmp_path / "a" / "b" / "c"
        deep_dir.mkdir(parents=True)

        file1 = tmp_path / "file1.json"
        file2 = deep_dir / "file2.json"
        file1.touch()
        file2.touch()

        root = infer_source_root([file1, file2])
        assert root == tmp_path
