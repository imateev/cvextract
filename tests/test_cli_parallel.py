"""Tests for cli_parallel module - parallel directory processing."""

import zipfile
import pytest
from pathlib import Path
from unittest.mock import patch

from cvextract.cli_config import UserConfig, ExtractStage, AdjustStage, AdjusterConfig, ParallelStage
from cvextract.cli_parallel import (
    execute_parallel_pipeline,
    process_single_file_wrapper,
    _perform_upfront_research,
    scan_directory_for_files,
)
from cvextract.shared import StepName, StepStatus, UnitOfWork


@pytest.fixture
def mock_docx(tmp_path: Path):
    """Create a minimal valid DOCX file."""
    docx = tmp_path / "test.docx"
    with zipfile.ZipFile(docx, 'w') as zf:
        zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
    return docx


@pytest.fixture
def mock_template(tmp_path: Path):
    """Create a minimal template DOCX file."""
    template = tmp_path / "template.docx"
    with zipfile.ZipFile(template, 'w') as zf:
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
        with zipfile.ZipFile(docx, 'w') as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
    
    # Create a subdirectory with more files
    subdir = input_dir / "subdir"
    subdir.mkdir()
    for i in range(2):
        docx = subdir / f"cv{i}.docx"
        with zipfile.ZipFile(docx, 'w') as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
    
    # Create a temporary file (should be ignored)
    temp_file = input_dir / "~$temp.docx"
    with zipfile.ZipFile(temp_file, 'w') as zf:
        zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
    
    return input_dir


class TestProcessSingleFileWrapper:
    """Tests for process_single_file_wrapper function."""
    
    @patch('cvextract.cli_parallel._execute_pipeline_single')
    def test_process_single_file_success(self, mock_execute, tmp_path: Path, mock_docx: Path):
        """Test processing single file successfully."""
        work = UnitOfWork(config=UserConfig(target_dir=tmp_path), input=mock_docx, output=mock_docx)
        mock_execute.return_value = (0, work)
        
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=tmp_path, n=1),
            target_dir=tmp_path / "out",
            verbosity="minimal",
            log_file=None
        )
        
        success, message, exit_code, has_warnings = process_single_file_wrapper(mock_docx, config)
        
        assert success
        assert message == ""
        assert exit_code == 0
        assert not has_warnings
        mock_execute.assert_called_once()
    
    @patch('cvextract.cli_parallel._execute_pipeline_single')
    def test_process_single_file_with_warnings(self, mock_execute, tmp_path: Path, mock_docx: Path):
        """Test processing file with warnings (exit code 0, but has_warnings set)."""
        work = UnitOfWork(config=UserConfig(target_dir=tmp_path), input=mock_docx, output=mock_docx)
        work.step_statuses[StepName.Render] = StepStatus(
            step=StepName.Render,
            warnings=["warning message"],
        )
        mock_execute.return_value = (0, work)
        
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=tmp_path, n=1),
            target_dir=tmp_path / "out",
            verbosity="minimal",
            log_file=None
        )
        
        success, message, exit_code, has_warnings = process_single_file_wrapper(mock_docx, config)
        
        assert success
        assert exit_code == 0
        assert has_warnings
    
    @patch('cvextract.cli_parallel._execute_pipeline_single')
    def test_process_single_file_failure(self, mock_execute, tmp_path: Path, mock_docx: Path):
        """Test processing file that fails."""
        work = UnitOfWork(config=UserConfig(target_dir=tmp_path), input=mock_docx, output=mock_docx)
        mock_execute.return_value = (1, work)
        
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=tmp_path, n=1),
            target_dir=tmp_path / "out",
            verbosity="minimal",
            log_file=None
        )
        
        success, message, exit_code, has_warnings = process_single_file_wrapper(mock_docx, config)
        
        assert not success
        assert "failed" in message.lower()
        assert exit_code == 1
        assert not has_warnings
    
    @patch('cvextract.cli_parallel._execute_pipeline_single')
    def test_process_single_file_exception(self, mock_execute, tmp_path: Path, mock_docx: Path):
        """Test processing file that raises exception."""
        mock_execute.side_effect = Exception("Test error")
        
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=tmp_path, n=1),
            target_dir=tmp_path / "out",
            verbosity="minimal",
            log_file=None
        )
        
        success, message, exit_code, has_warnings = process_single_file_wrapper(mock_docx, config)
        
        assert not success
        assert "Test error" in message
        assert exit_code == 1
        assert not has_warnings


class TestExecuteParallelPipeline:
    """Tests for execute_parallel_pipeline function."""
    
    @patch('cvextract.cli_parallel.process_single_file_wrapper')
    def test_parallel_pipeline_all_success(self, mock_process, tmp_path: Path, test_directory: Path):
        """Test parallel pipeline with all files succeeding."""
        mock_process.return_value = (True, "", 0, False)
        
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=test_directory, n=2),
            target_dir=tmp_path / "out",
            verbosity="minimal",
            log_file=None
        )
        
        exit_code = execute_parallel_pipeline(config)
        
        assert exit_code == 0
        # Should have been called for each file (5 times)
        assert mock_process.call_count == 5
    
    @patch('cvextract.cli_parallel.process_single_file_wrapper')
    def test_parallel_pipeline_some_failures(self, mock_process, tmp_path: Path, test_directory: Path):
        """Test parallel pipeline with some files failing - should return 0 (success)."""
        # Alternate between success and failure
        mock_process.side_effect = [
            (True, "", 0, False),
            (False, "Error", 1, False),
            (True, "", 0, False),
            (False, "Error", 1, False),
            (True, "", 0, False),
        ]
        
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=test_directory, n=2),
            target_dir=tmp_path / "out",
            verbosity="minimal",
            log_file=None
        )
        
        exit_code = execute_parallel_pipeline(config)
        
        # Should return 0 even if some files failed (user requirement)
        assert exit_code == 0
        assert mock_process.call_count == 5
    
    def test_parallel_pipeline_no_config(self, tmp_path: Path):
        """Test that calling without parallel config raises error."""
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=None,
            render=None,
            parallel=None,  # No parallel config
            target_dir=tmp_path / "out",
            verbosity="minimal",
            log_file=None
        )
        
        with pytest.raises(ValueError, match="without parallel configuration"):
            execute_parallel_pipeline(config)
    
    def test_parallel_pipeline_directory_not_found(self, tmp_path: Path):
        """Test parallel pipeline with non-existent directory."""
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=tmp_path / "does_not_exist", n=1),
            target_dir=tmp_path / "out",
            verbosity="minimal",
            log_file=None
        )
        
        exit_code = execute_parallel_pipeline(config)
        assert exit_code == 1
    
    def test_parallel_pipeline_no_docx_files(self, tmp_path: Path):
        """Test parallel pipeline with directory containing no DOCX files."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=empty_dir, n=1),
            target_dir=tmp_path / "out",
            log_file=None
        )
        
        exit_code = execute_parallel_pipeline(config)
        assert exit_code == 1
        """Input path that exists but is not a directory should return error."""
        not_dir = tmp_path / "single.docx"
        not_dir.write_text("docx")
        
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=not_dir, n=1),
            target_dir=tmp_path / "out",
            log_file=None
        )
        
        exit_code = execute_parallel_pipeline(config)
        assert exit_code == 1

    @patch('cvextract.cli_parallel.LOG.error')
    @patch('cvextract.cli_parallel.scan_directory_for_files')
    def test_parallel_pipeline_scan_directory_failure_debug_logs(self, mock_scan, mock_log_error, tmp_path: Path):
        """Scan failures should log details and return error when debug enabled."""
        mock_scan.side_effect = RuntimeError("scan failed")
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=input_dir, n=1),
            target_dir=tmp_path / "out",
            verbosity="debug",
            log_file=None
        )
        
        exit_code = execute_parallel_pipeline(config)
        assert exit_code == 1
        mock_scan.assert_called_once_with(input_dir, "*.docx")
        verbosity="debug",
        # Two error logs are expected: error message and traceback
        assert mock_log_error.call_count == 2
        assert "Failed to scan directory" in mock_log_error.call_args_list[0][0][0]
    
    @patch('cvextract.cli_parallel.process_single_file_wrapper')
    @patch('cvextract.cli_parallel._perform_upfront_research')
    def test_parallel_pipeline_with_adjust(self, mock_research, mock_process, tmp_path: Path, test_directory: Path):
        """Test parallel pipeline with adjust stage performs upfront research."""
        mock_research.return_value = tmp_path / "research.json"
        mock_process.return_value = (True, "", 0, False)
        
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=AdjustStage(
                adjusters=[AdjusterConfig(
                    name="openai-company-research",
                    params={"customer-url": "https://example.com"},
                    openai_model=None
                )],
                data=None,
                output=None,
                dry_run=False
            ),
            render=None,
            parallel=ParallelStage(source=test_directory, n=2),
            target_dir=tmp_path / "out",
            log_file=None
        )
        
        exit_code = execute_parallel_pipeline(config)
        
        assert exit_code == 0
        verbosity="minimal",
        mock_research.assert_called_once_with(config)
    
    @patch('cvextract.cli_parallel.process_single_file_wrapper')
    def test_parallel_pipeline_with_warnings_returns_zero(self, mock_process, tmp_path: Path, test_directory: Path):
        """Test parallel pipeline with warnings returns exit code 0."""
        mock_process.return_value = (True, "warnings", 0, True)
        
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=test_directory, n=2),
            target_dir=tmp_path / "out",
            verbosity="debug",
            log_file=None
        )
        
        exit_code = execute_parallel_pipeline(config)
        assert exit_code == 0  # Warnings no longer affect exit code

    @patch('cvextract.cli_parallel.process_single_file_wrapper')
    def test_parallel_pipeline_partial_success(self, mock_process, tmp_path: Path, test_directory: Path):
        """Test parallel pipeline tracks partial successes (files with warnings)."""
        # Mix of full success, partial success (warnings), and failures
        mock_process.side_effect = [
            (True, "", 0, False),  # Full success
            (True, "warnings", 0, True),  # Partial success
            (False, "Error", 1, False),  # Failure
            (True, "", 0, False),  # Full success
            (True, "warnings", 0, True),  # Partial success
        ]
        
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=test_directory, n=2),
            target_dir=tmp_path / "out",
            verbosity="debug",
            log_file=None
        )
        
        exit_code = execute_parallel_pipeline(config)
        assert mock_process.call_count == 5

    @patch('cvextract.cli_parallel.LOG.error')
    @patch('cvextract.cli_parallel.process_single_file_wrapper')
    def test_parallel_pipeline_future_exception_logged_and_counted(self, mock_process, mock_log_error,
                                                                   tmp_path: Path, test_directory: Path):
        """Exceptions raised by workers should be logged and counted as failures."""
        mock_process.side_effect = RuntimeError("boom")
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=test_directory, n=2),
            target_dir=tmp_path / "out",
            verbosity="debug",
            log_file=None
        )
        
        exit_code = execute_parallel_pipeline(config)
        assert exit_code == 0
        doc_count = len(scan_directory_for_files(test_directory, "*.docx"))
        # Each exception logs the user-facing message and the traceback
        # Two error logs per exception: error message and traceback
        assert mock_log_error.call_count == doc_count * 2
        assert any("Unexpected error" in call.args[0] for call in mock_log_error.call_args_list)

    @patch('cvextract.cli_parallel.LOG.info')
    @patch('cvextract.cli_parallel.process_single_file_wrapper')
    def test_parallel_pipeline_logs_failed_files_in_debug_mode(self, mock_process, mock_log_info,
                                                               tmp_path: Path, test_directory: Path):
        """Debug mode should list failed files after processing."""
        mock_process.return_value = (False, "Error", 1, False)
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=test_directory, n=2),
            target_dir=tmp_path / "out",
            verbosity="debug",
            log_file=None
        )
        
        exit_code = execute_parallel_pipeline(config)
        assert exit_code == 0
        # Print actual log lines for debugging if needed
        # print([call.args[0] for call in mock_log_info.call_args_list])
        # Accept both the summary and at least one failed file line
        log_lines = [call.args[0] for call in mock_log_info.call_args_list]
        assert any("Failed files:" in line for line in log_lines)
        assert any(line.startswith("  - ") for line in log_lines)


class TestPerformUpfrontResearch:
    """Tests for _perform_upfront_research function."""
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    @patch('cvextract.cli_parallel._research_company_profile')
    def test_upfront_research_success(self, mock_research, tmp_path: Path):
        """Test successful upfront research."""
        mock_research.return_value = {"name": "Example Corp", "domains": ["software"]}
        
        config = UserConfig(
            extract=None,
            adjust=AdjustStage(
                adjusters=[AdjusterConfig(
                    name="openai-company-research",
                    params={"customer-url": "https://example.com"},
                    openai_model=None
                )],
                data=None,
                output=None,
                dry_run=False
            ),
            render=None,
            parallel=None,
            target_dir=tmp_path / "out",
            log_file=None
        )
        
        cache_path = _perform_upfront_research(config)
        
        assert cache_path is not None
        assert cache_path.parent.name == "research_data"
        mock_research.assert_called_once()
    
    def test_upfront_research_no_adjust(self, tmp_path: Path):
        """Test upfront research with no adjust stage returns None."""
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=None,  # No adjust stage
            render=None,
            parallel=None,
            target_dir=tmp_path / "out",
            log_file=None
        )
        
        cache_path = _perform_upfront_research(config)
        assert cache_path is None
    
    @patch.dict('os.environ', {}, clear=True)
    def test_upfront_research_no_api_key(self, tmp_path: Path):
        """Test upfront research without API key returns None."""
        config = UserConfig(
            extract=None,
            adjust=AdjustStage(
                adjusters=[AdjusterConfig(
                    name="openai-company-research",
                    params={"customer-url": "https://example.com"},
                    openai_model=None
                )],
                data=None,
                output=None,
                dry_run=False
            ),
            render=None,
            parallel=None,
            target_dir=tmp_path / "out",
            log_file=None
        )
        
        cache_path = _perform_upfront_research(config)
        assert cache_path is None
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    @patch('cvextract.cli_parallel._research_company_profile')
    def test_upfront_research_failure(self, mock_research, tmp_path: Path):
        """Test upfront research that fails returns None."""
        mock_research.return_value = None  # Research failed
        
        config = UserConfig(
            extract=None,
            adjust=AdjustStage(
                adjusters=[AdjusterConfig(
                    name="openai-company-research",
                    params={"customer-url": "https://example.com"},
                    openai_model=None
                )],
                data=None,
                output=None,
                dry_run=False
            ),
            render=None,
            parallel=None,
            target_dir=tmp_path / "out",
            log_file=None
        )
        
        cache_path = _perform_upfront_research(config)
        assert cache_path is None


class TestScanDirectoryForFiles:
    """Tests for scan_directory_for_files function - new generic version."""
    
    def test_scan_directory_for_docx_files(self, test_directory: Path):
        """Test scanning directory for .docx files using generic function."""
        from cvextract.cli_parallel import scan_directory_for_files
        
        files = scan_directory_for_files(test_directory, "*.docx")
        
        # Should find 5 files (3 in root, 2 in subdir, ignore temp)
        assert len(files) == 5
        assert all(f.suffix == ".docx" for f in files)
    
    def test_scan_directory_for_txt_files(self, tmp_path: Path):
        """Test scanning directory for .txt files."""
        from cvextract.cli_parallel import scan_directory_for_files
        
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
        from cvextract.cli_parallel import scan_directory_for_files
        
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
        from cvextract.cli_parallel import scan_directory_for_files
        
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
    
    @patch('cvextract.cli_parallel.process_single_file_wrapper')
    def test_parallel_with_custom_file_type(self, mock_process, tmp_path: Path):
        """Test parallel processing with custom file type."""
        mock_process.return_value = (True, "", 0, False)
        
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        
        # Create TXT files instead of DOCX
        for i in range(3):
            txt_file = input_dir / f"cv{i}.txt"
            txt_file.write_text(f"CV {i}")
        
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None, name="openai-extractor"),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=input_dir, n=2, file_type="*.txt"),
            target_dir=tmp_path / "out",
            log_file=None
        )
        
        exit_code = execute_parallel_pipeline(config)
        
        assert exit_code == 0
        # Should have processed all 3 txt files
        assert mock_process.call_count == 3
    
    @patch('cvextract.cli_parallel.process_single_file_wrapper')
    def test_parallel_default_file_type(self, mock_process, test_directory: Path, tmp_path: Path):
        """Test parallel processing uses default *.docx file type."""
        mock_process.return_value = (True, "", 0, False)
        
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=test_directory, n=2),  # No file_type specified
            target_dir=tmp_path / "out",
            log_file=None
        )
        
        exit_code = execute_parallel_pipeline(config)
        
        assert exit_code == 0
        # Should have processed 5 docx files (default)
        assert mock_process.call_count == 5
    
    def test_parallel_no_matching_files(self, tmp_path: Path):
        """Test parallel processing when no files match the pattern."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        
        # Create only .docx files
        for i in range(2):
            (input_dir / f"cv{i}.docx").write_bytes(b"docx")
        
        # Try to process .txt files
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=input_dir, n=2, file_type="*.txt"),
            target_dir=tmp_path / "out",
            log_file=None
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
        
        Progress logs have format: "%s %s %s" with args like ('%s %s %s', '✅', '[1/5 | 20%]', 'filename.docx')
        The progress indicator is in args[2].
        """
        return [
            call.args[2] for call in mock_log_info.call_args_list
            if len(call.args) >= 4 
            and isinstance(call.args[2], str) 
            and '[' in call.args[2] 
            and '/' in call.args[2]
        ]
    
    @patch('cvextract.cli_parallel.process_single_file_wrapper')
    @patch('cvextract.cli_parallel.LOG.info')
    def test_progress_indicator_shown(self, mock_log_info, mock_process, test_directory: Path, tmp_path: Path):
        """Test that progress indicator is included in log output."""
        mock_process.return_value = (True, "", 0, False)
        
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=test_directory, n=2),
            target_dir=tmp_path / "out",
            log_file=None
        )
        
        exit_code = execute_parallel_pipeline(config)
        
        assert exit_code == 0
        
        # Extract progress indicators
        progress_indicators = self._extract_progress_indicators(mock_log_info)
        
        # Should have 5 progress log entries (one per file)
        assert len(progress_indicators) == 5
    
    @patch('cvextract.cli_parallel.process_single_file_wrapper')
    @patch('cvextract.cli_parallel.LOG.info')
    def test_progress_percentage_calculated(self, mock_log_info, mock_process, tmp_path: Path):
        """Test that progress percentage is calculated correctly."""
        mock_process.return_value = (True, "", 0, False)
        
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        
        # Create exactly 4 files for easy percentage calculation
        for i in range(4):
            (input_dir / f"cv{i}.docx").write_bytes(b"docx")
        
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=None,
            render=None,
            parallel=ParallelStage(source=input_dir, n=1),
            target_dir=tmp_path / "out",
            log_file=None
        )
        
        exit_code = execute_parallel_pipeline(config)
        assert exit_code == 0
        
        # Extract progress indicators using helper
        progress_indicators = self._extract_progress_indicators(mock_log_info)
        
        # Verify that we see expected progress indicators
        # With 4 files: [1/4 | 25%], [2/4 | 50%], [3/4 | 75%], [4/4 | 100%]
        assert "[1/4 | 25%]" in progress_indicators
        assert "[4/4 | 100%]" in progress_indicators
