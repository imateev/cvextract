"""Tests for cli_execute_parallel module - parallel directory processing."""

import zipfile
from concurrent.futures import Future
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest

from cvextract.cli_config import (
    AdjusterConfig,
    AdjustStage,
    ExtractStage,
    ParallelStage,
    RenderStage,
    UserConfig,
)
from cvextract.cli_execute_parallel import (
    _build_file_config,
    _emit_parallel_summary,
    _execute_file,
    _load_failed_list,
    _process_future_result,
    _WorkStatus,
    _write_failed_list,
    execute_parallel_pipeline,
    scan_directory_for_files,
)
from cvextract.shared import StepName, StepStatus, UnitOfWork


@pytest.fixture
def mock_docx(tmp_path: Path):
    """Create a minimal valid DOCX file."""
    docx = tmp_path / "test.docx"
    with zipfile.ZipFile(docx, "w") as zf:
        zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
    return docx


@pytest.fixture
def mock_template(tmp_path: Path):
    """Create a minimal template DOCX file."""
    template = tmp_path / "template.docx"
    with zipfile.ZipFile(template, "w") as zf:
        zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
    return template


@pytest.fixture
def test_directory(tmp_path: Path):
    """Create a directory structure with multiple DOCX files."""
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    # Create some DOCX files
    for i in range(3):
        docx = input_dir / f"cv{i}.docx"
        with zipfile.ZipFile(docx, "w") as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")

    # Create a subdirectory with more files
    subdir = input_dir / "subdir"
    subdir.mkdir()
    for i in range(2):
        docx = subdir / f"cv{i}.docx"
        with zipfile.ZipFile(docx, "w") as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")

    # Create a temporary file (should be ignored)
    temp_file = input_dir / "~$temp.docx"
    with zipfile.ZipFile(temp_file, "w") as zf:
        zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")

    return input_dir


def _make_work(tmp_path: Path, warnings: list[str] | None = None) -> UnitOfWork:
    work = UnitOfWork(
        config=UserConfig(target_dir=tmp_path),
        initial_input=Path("input"),
    )
    work.set_step_paths(
        StepName.Extract,
        input_path=Path("input"),
        output_path=Path("output"),
    )
    if warnings:
        work.step_states[StepName.Render] = StepStatus(
            step=StepName.Render,
            warnings=warnings,
        )
    return work


class TestExecuteParallelPipeline:
    """Tests for execute_parallel_pipeline function."""

    @patch("cvextract.cli_execute_parallel.execute_single")
    def test_parallel_pipeline_all_success(
        self, mock_execute, tmp_path: Path, test_directory: Path
    ):
        """Test parallel pipeline with all files succeeding."""
        mock_execute.return_value = (0, _make_work(tmp_path))

        config = UserConfig(
            extract=ExtractStage(source=Path("."), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=test_directory, n=2),
            target_dir=tmp_path / "out",
            verbosity="minimal",
            log_file=None,
        )

        exit_code = execute_parallel_pipeline(config)

        assert exit_code == 0
        # Should have been called for each file (5 times)
        assert mock_execute.call_count == 5

    @patch("cvextract.cli_execute_parallel.execute_single")
    def test_parallel_pipeline_some_failures(
        self, mock_execute, tmp_path: Path, test_directory: Path
    ):
        """Test parallel pipeline with some files failing - should return 0 (success)."""
        # Alternate between success and failure
        mock_execute.side_effect = [
            (0, _make_work(tmp_path)),
            (1, None),
            (0, _make_work(tmp_path)),
            (1, None),
            (0, _make_work(tmp_path)),
        ]

        config = UserConfig(
            extract=ExtractStage(source=Path("."), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=test_directory, n=2),
            target_dir=tmp_path / "out",
            verbosity="minimal",
            log_file=None,
        )

        exit_code = execute_parallel_pipeline(config)

        # Should return 0 even if some files failed (user requirement)
        assert exit_code == 0
        assert mock_execute.call_count == 5

    def test_parallel_pipeline_no_config(self, tmp_path: Path):
        """Test that calling without parallel config raises error."""
        config = UserConfig(
            extract=ExtractStage(source=Path("."), output=None),
            adjust=None,
            render=None,
            parallel=None,  # No parallel config
            target_dir=tmp_path / "out",
            verbosity="minimal",
            log_file=None,
        )

        with pytest.raises(ValueError, match="without parallel configuration"):
            execute_parallel_pipeline(config)

    def test_parallel_pipeline_directory_not_found(self, tmp_path: Path):
        """Test parallel pipeline with non-existent directory."""
        config = UserConfig(
            extract=ExtractStage(source=Path("."), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=tmp_path / "does_not_exist", n=1),
            target_dir=tmp_path / "out",
            verbosity="minimal",
            log_file=None,
        )

        exit_code = execute_parallel_pipeline(config)
        assert exit_code == 1

    def test_parallel_pipeline_no_docx_files(self, tmp_path: Path):
        """Test parallel pipeline with directory containing no DOCX files."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        config = UserConfig(
            extract=ExtractStage(source=Path("."), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=empty_dir, n=1),
            target_dir=tmp_path / "out",
            log_file=None,
        )

        exit_code = execute_parallel_pipeline(config)
        assert exit_code == 1
        """Input path that exists but is not a directory should return error."""
        not_dir = tmp_path / "single.docx"
        not_dir.write_text("docx")

        config = UserConfig(
            extract=ExtractStage(source=Path("."), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=not_dir, n=1),
            target_dir=tmp_path / "out",
            log_file=None,
        )

        exit_code = execute_parallel_pipeline(config)
        assert exit_code == 1

    @patch("cvextract.cli_execute_parallel.LOG.error")
    @patch("cvextract.cli_execute_parallel.scan_directory_for_files")
    def test_parallel_pipeline_scan_directory_failure_debug_logs(
        self, mock_scan, mock_log_error, tmp_path: Path
    ):
        """Scan failures should log details and return error when debug enabled."""
        mock_scan.side_effect = RuntimeError("scan failed")
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        config = UserConfig(
            extract=ExtractStage(source=Path("."), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=input_dir, n=1),
            target_dir=tmp_path / "out",
            verbosity="debug",
            log_file=None,
        )

        exit_code = execute_parallel_pipeline(config)
        assert exit_code == 1
        mock_scan.assert_called_once_with(input_dir, "*.docx")
        # Two error logs are expected: error message and traceback
        assert mock_log_error.call_count == 2
        assert "Failed to scan directory" in mock_log_error.call_args_list[0][0][0]

    @patch("cvextract.cli_execute_parallel.execute_single")
    def test_parallel_pipeline_with_warnings_returns_zero(
        self, mock_execute, tmp_path: Path, test_directory: Path
    ):
        """Test parallel pipeline with warnings returns exit code 0."""
        mock_execute.return_value = (0, _make_work(tmp_path, warnings=["warnings"]))

        config = UserConfig(
            extract=ExtractStage(source=Path("."), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=test_directory, n=2),
            target_dir=tmp_path / "out",
            verbosity="debug",
            log_file=None,
        )

        exit_code = execute_parallel_pipeline(config)
        assert exit_code == 0  # Warnings no longer affect exit code

    @patch("cvextract.cli_execute_parallel.execute_single")
    def test_parallel_pipeline_partial_success(
        self, mock_execute, tmp_path: Path, test_directory: Path
    ):
        """Test parallel pipeline tracks partial successes (files with warnings)."""
        # Mix of full success, partial success (warnings), and failures
        mock_execute.side_effect = [
            (0, _make_work(tmp_path)),  # Full success
            (0, _make_work(tmp_path, warnings=["warnings"])),  # Partial success
            (1, None),  # Failure
            (0, _make_work(tmp_path)),  # Full success
            (0, _make_work(tmp_path, warnings=["warnings"])),  # Partial success
        ]

        config = UserConfig(
            extract=ExtractStage(source=Path("."), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=test_directory, n=2),
            target_dir=tmp_path / "out",
            verbosity="debug",
            log_file=None,
        )

        exit_code = execute_parallel_pipeline(config)
        assert mock_execute.call_count == 5

    @patch("cvextract.cli_execute_parallel.LOG.error")
    @patch("cvextract.cli_execute_parallel.execute_single")
    def test_parallel_pipeline_future_exception_logged_and_counted(
        self, mock_execute, mock_log_error, tmp_path: Path, test_directory: Path
    ):
        """Exceptions raised by workers should be logged and counted as failures."""
        mock_execute.side_effect = RuntimeError("boom")
        config = UserConfig(
            extract=ExtractStage(source=Path("."), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=test_directory, n=2),
            target_dir=tmp_path / "out",
            verbosity="debug",
            log_file=None,
        )

        exit_code = execute_parallel_pipeline(config)
        assert exit_code == 0
        doc_count = len(scan_directory_for_files(test_directory, "*.docx"))
        # Each exception logs the user-facing message and the traceback
        # Two error logs per exception: error message and traceback
        assert mock_log_error.call_count == doc_count * 2
        assert any(
            "Unexpected error" in call.args[0] for call in mock_log_error.call_args_list
        )

    @patch("cvextract.cli_execute_parallel.LOG.info")
    @patch("cvextract.cli_execute_parallel.execute_single")
    def test_parallel_pipeline_logs_failed_files_in_debug_mode(
        self, mock_execute, mock_log_info, tmp_path: Path, test_directory: Path
    ):
        """Debug mode should list failed files after processing."""
        mock_execute.return_value = (1, None)
        config = UserConfig(
            extract=ExtractStage(source=Path("."), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=test_directory, n=2),
            target_dir=tmp_path / "out",
            verbosity="debug",
            log_file=None,
        )

        exit_code = execute_parallel_pipeline(config)
        assert exit_code == 0
        # Print actual log lines for debugging if needed
        # print([call.args[0] for call in mock_log_info.call_args_list])
        # Accept both the summary and at least one failed file line
        log_lines = [call.args[0] for call in mock_log_info.call_args_list]
        assert any("Failed files:" in line for line in log_lines)
        assert any(line.startswith("  - ") for line in log_lines)


class TestScanDirectoryForFiles:
    """Tests for scan_directory_for_files function - new generic version."""

    def test_scan_directory_for_docx_files(self, test_directory: Path):
        """Test scanning directory for .docx files using generic function."""
        from cvextract.cli_execute_parallel import scan_directory_for_files

        files = scan_directory_for_files(test_directory, "*.docx")

        # Should find 5 files (3 in root, 2 in subdir, ignore temp)
        assert len(files) == 5
        assert all(f.suffix == ".docx" for f in files)

    def test_scan_directory_for_txt_files(self, tmp_path: Path):
        """Test scanning directory for .txt files."""
        from cvextract.cli_execute_parallel import scan_directory_for_files

        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create some TXT files
        for i in range(3):
            txt_file = input_dir / f"cv{i}.txt"
            txt_file.write_text(f"CV content {i}")

        files = scan_directory_for_files(input_dir, "*.txt")

        assert len(files) == 3
        assert all(f.suffix == ".txt" for f in files)

    def test_scan_directory_for_pdf_files(self, tmp_path: Path):
        """Test scanning directory for .pdf files."""
        from cvextract.cli_execute_parallel import scan_directory_for_files

        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create some PDF files (just empty for testing)
        for i in range(2):
            pdf_file = input_dir / f"cv{i}.pdf"
            pdf_file.write_bytes(b"PDF content")

        files = scan_directory_for_files(input_dir, "*.pdf")

        assert len(files) == 2
        assert all(f.suffix == ".pdf" for f in files)

    def test_scan_directory_mixed_file_types(self, tmp_path: Path):
        """Test that pattern matching is precise."""
        from cvextract.cli_execute_parallel import scan_directory_for_files

        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create mixed file types
        (input_dir / "cv1.docx").write_bytes(b"docx")
        (input_dir / "cv2.txt").write_text("txt")
        (input_dir / "cv3.pdf").write_bytes(b"pdf")

        # Should only find .txt files
        txt_files = scan_directory_for_files(input_dir, "*.txt")
        assert len(txt_files) == 1
        assert txt_files[0].suffix == ".txt"

        # Should only find .docx files
        docx_files = scan_directory_for_files(input_dir, "*.docx")
        assert len(docx_files) == 1
        assert docx_files[0].suffix == ".docx"


class TestFileTypeParameter:
    """Tests for the file-type parameter in parallel processing."""

    @patch("cvextract.cli_execute_parallel.execute_single")
    def test_parallel_with_custom_file_type(self, mock_execute, tmp_path: Path):
        """Test parallel processing with custom file type."""
        mock_execute.return_value = (0, _make_work(tmp_path))

        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create TXT files instead of DOCX
        for i in range(3):
            txt_file = input_dir / f"cv{i}.txt"
            txt_file.write_text(f"CV {i}")

        config = UserConfig(
            extract=ExtractStage(
                source=Path("."), output=None, name="openai-extractor"
            ),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=input_dir, n=2, file_type="*.txt"),
            target_dir=tmp_path / "out",
            log_file=None,
        )

        exit_code = execute_parallel_pipeline(config)

        assert exit_code == 0
        # Should have processed all 3 txt files
        assert mock_execute.call_count == 3

    @patch("cvextract.cli_execute_parallel.execute_single")
    def test_parallel_default_file_type(
        self, mock_execute, test_directory: Path, tmp_path: Path
    ):
        """Test parallel processing uses default *.docx file type."""
        mock_execute.return_value = (0, _make_work(tmp_path))

        config = UserConfig(
            extract=ExtractStage(source=Path("."), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(
                source=test_directory, n=2
            ),  # No file_type specified
            target_dir=tmp_path / "out",
            log_file=None,
        )

        exit_code = execute_parallel_pipeline(config)

        assert exit_code == 0
        # Should have processed 5 docx files (default)
        assert mock_execute.call_count == 5

    def test_parallel_no_matching_files(self, tmp_path: Path):
        """Test parallel processing when no files match the pattern."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create only .docx files
        for i in range(2):
            (input_dir / f"cv{i}.docx").write_bytes(b"docx")

        # Try to process .txt files
        config = UserConfig(
            extract=ExtractStage(source=Path("."), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=input_dir, n=2, file_type="*.txt"),
            target_dir=tmp_path / "out",
            log_file=None,
        )

        exit_code = execute_parallel_pipeline(config)

        # Should return error since no matching files found
        assert exit_code == 1


class TestProgressIndicator:
    """Tests for progress indicator in parallel processing."""

    @staticmethod
    def _extract_progress_indicators(mock_log_info):
        """
        Helper to extract progress indicators from mock log calls.

        Progress logs include a progress string like "[1/5 | 20%]".
        """
        indicators = []
        for call in mock_log_info.call_args_list:
            for arg in call.args:
                if isinstance(arg, str) and "[" in arg and "/" in arg:
                    indicators.append(arg)
                    break
        return indicators

    @patch("cvextract.cli_execute_parallel.execute_single")
    @patch("cvextract.cli_execute_parallel.LOG.info")
    def test_progress_indicator_shown(
        self, mock_log_info, mock_execute, test_directory: Path, tmp_path: Path
    ):
        """Test that progress indicator is included in log output."""
        mock_execute.return_value = (0, _make_work(tmp_path))

        config = UserConfig(
            extract=ExtractStage(source=Path("."), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=test_directory, n=2),
            target_dir=tmp_path / "out",
            log_file=None,
        )

        exit_code = execute_parallel_pipeline(config)

        assert exit_code == 0

        # Extract progress indicators
        progress_indicators = self._extract_progress_indicators(mock_log_info)

        # Should have 5 progress log entries (one per file)
        assert len(progress_indicators) == 5

    @patch("cvextract.cli_execute_parallel.execute_single")
    @patch("cvextract.cli_execute_parallel.LOG.info")
    def test_progress_percentage_calculated(
        self, mock_log_info, mock_execute, tmp_path: Path
    ):
        """Test that progress percentage is calculated correctly."""
        mock_execute.return_value = (0, _make_work(tmp_path))

        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create exactly 4 files for easy percentage calculation
        for i in range(4):
            (input_dir / f"cv{i}.docx").write_bytes(b"docx")

        config = UserConfig(
            extract=ExtractStage(source=Path("."), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=input_dir, n=1),
            target_dir=tmp_path / "out",
            log_file=None,
        )

        exit_code = execute_parallel_pipeline(config)
        assert exit_code == 0

        # Extract progress indicators using helper
        progress_indicators = self._extract_progress_indicators(mock_log_info)

        # Verify that we see expected progress indicators
        # With 4 files: [1/4 | 25%], [2/4 | 50%], [3/4 | 75%], [4/4 | 100%]
        assert "[1/4 |  25%]" in progress_indicators
        assert "[4/4 | 100%]" in progress_indicators


class TestParallelHelperFunctions:
    """Tests for helper functions used in parallel execution."""

    def test_load_failed_list_parses_entries(self, tmp_path: Path):
        """_load_failed_list should ignore comments and prefixes."""
        failed_list = tmp_path / "failed.txt"
        doc_a = tmp_path / "a.docx"
        doc_b = tmp_path / "b.docx"
        failed_list.write_text(f"# comment\n\n- {doc_a}\n{doc_b}\n", encoding="utf-8")

        files = _load_failed_list(failed_list)

        assert files == [doc_a, doc_b]

    def test_write_failed_list_writes_newline(self, tmp_path: Path):
        """_write_failed_list should write one entry per line."""
        output = tmp_path / "failed.txt"

        _write_failed_list(output, ["a", "b"])

        assert output.read_text(encoding="utf-8") == "a\nb\n"

    def test_build_file_config_updates_extract_source(self, tmp_path: Path):
        """_build_file_config should replace extract source and set flags."""
        source_dir = tmp_path / "input"
        config = UserConfig(
            extract=ExtractStage(source=Path("old.docx")),
            parallel=ParallelStage(source=source_dir, n=1),
            target_dir=tmp_path,
        )
        file_path = tmp_path / "new.docx"

        result = _build_file_config(config, file_path)

        assert result.extract is not None
        assert result.extract.source == file_path
        assert result.parallel is None
        assert result.suppress_summary is True
        assert result.suppress_file_logging is True
        assert result.input_dir == source_dir

    def test_build_file_config_updates_render_data(self, tmp_path: Path):
        """_build_file_config should replace render data when no extract."""
        template = tmp_path / "template.docx"
        template.touch()
        source_dir = tmp_path / "input"
        config = UserConfig(
            render=RenderStage(template=template, data=tmp_path / "old.json"),
            parallel=ParallelStage(source=source_dir, n=1),
            target_dir=tmp_path,
        )
        new_data = tmp_path / "new.json"

        result = _build_file_config(config, new_data)

        assert result.render is not None
        assert result.render.data == new_data
        assert result.parallel is None
        assert result.input_dir == source_dir

    def test_build_file_config_updates_adjust_data(self, tmp_path: Path):
        """_build_file_config should replace adjust data when no extract/render."""
        source_dir = tmp_path / "input"
        config = UserConfig(
            adjust=AdjustStage(
                adjusters=[AdjusterConfig(name="noop", params={})],
                data=tmp_path / "old.json",
            ),
            parallel=ParallelStage(source=source_dir, n=1),
            target_dir=tmp_path,
        )
        new_data = tmp_path / "new.json"

        result = _build_file_config(config, new_data)

        assert result.adjust is not None
        assert result.adjust.data == new_data
        assert result.parallel is None
        assert result.input_dir == source_dir

    def test_execute_file_uses_file_context(self, tmp_path: Path):
        """_execute_file should run execute_single inside file context."""
        file_path = tmp_path / "input.docx"
        file_path.touch()

        config = UserConfig(
            extract=ExtractStage(source=Path("old.docx")),
            parallel=ParallelStage(source=tmp_path, n=1),
            target_dir=tmp_path,
        )
        work = UnitOfWork(config=config, initial_input=file_path)

        class DummyController:
            def __init__(self) -> None:
                self.seen: list[Path] = []

            @contextmanager
            def file_context(self, path: Path):
                self.seen.append(path)
                yield

        controller = DummyController()

        with patch(
            "cvextract.cli_execute_parallel.get_output_controller",
            return_value=controller,
        ), patch(
            "cvextract.cli_execute_parallel.execute_single",
            return_value=(0, work),
        ) as mock_execute:
            result = _execute_file(file_path, config)

        assert result == (0, work)
        assert controller.seen == [file_path]
        passed_config = mock_execute.call_args[0][0]
        assert passed_config.extract is not None
        assert passed_config.extract.source == file_path

    def test_process_future_result_success_trims_summary(self, tmp_path: Path):
        """_process_future_result should drop empty issue placeholder."""
        file_path = tmp_path / "input.docx"
        config = UserConfig(target_dir=tmp_path)
        work = UnitOfWork(config=config, initial_input=file_path)

        future = Future()
        future.set_result((0, work))

        class DummyController:
            def __init__(self) -> None:
                self.summary_line = ""

            def flush_file(self, _path: Path, summary_line: str) -> None:
                self.summary_line = summary_line

        controller = DummyController()
        status, failed_file = _process_future_result(
            future,
            file_path,
            "[1/1 | 100%]",
            controller,
            config,
        )

        assert status == _WorkStatus.FULL
        assert failed_file is None
        assert controller.summary_line
        assert not controller.summary_line.endswith(" | -")

    def test_process_future_result_exception_marks_failed(self, tmp_path: Path):
        """_process_future_result should mark failures on exceptions."""
        file_path = tmp_path / "input.docx"
        config = UserConfig(target_dir=tmp_path, verbosity="debug")

        future = Future()
        future.set_exception(RuntimeError("boom"))

        class DummyController:
            def __init__(self) -> None:
                self.summary_line = ""

            def flush_file(self, _path: Path, summary_line: str) -> None:
                self.summary_line = summary_line

        controller = DummyController()
        status, failed_file = _process_future_result(
            future,
            file_path,
            "[1/1 | 100%]",
            controller,
            config,
        )

        assert status == _WorkStatus.FAILED
        assert failed_file == str(file_path)
        assert "Unexpected error:" in controller.summary_line

    def test_emit_parallel_summary_writes_failed_list(self, tmp_path: Path):
        """_emit_parallel_summary should write failed list when configured."""
        output = tmp_path / "failed.txt"
        config = UserConfig(
            target_dir=tmp_path,
            parallel=ParallelStage(source=tmp_path, n=1),
            log_failed=output,
            verbosity="debug",
        )

        class DummyController:
            def direct_print(self, _line: str) -> None:
                return None

        with patch("cvextract.cli_execute_parallel._write_failed_list") as mock_write:
            _emit_parallel_summary(
                total_files=3,
                full_success_count=1,
                partial_success_count=1,
                failed_count=1,
                failed_files=["a.docx"],
                config=config,
                controller=DummyController(),
            )

        mock_write.assert_called_once_with(output, ["a.docx"])


def test_execute_parallel_pipeline_rerun_failed_uses_list(tmp_path: Path):
    """execute_parallel_pipeline should honor rerun_failed list."""
    failed_list = tmp_path / "failed.txt"
    doc_a = tmp_path / "a.docx"
    doc_b = tmp_path / "b.docx"
    failed_list.write_text(f"{doc_a}\n{doc_b}\n", encoding="utf-8")

    config = UserConfig(
        extract=ExtractStage(source=doc_a, output=None),
        parallel=ParallelStage(source=tmp_path, n=1),
        rerun_failed=failed_list,
        target_dir=tmp_path,
    )

    with patch(
        "cvextract.cli_execute_parallel._execute_parallel_pipeline", return_value=0
    ) as mock_parallel:
        exit_code = execute_parallel_pipeline(config)

    assert exit_code == 0
    args, _kwargs = mock_parallel.call_args
    assert [str(p) for p in args[0]] == [str(doc_a), str(doc_b)]
