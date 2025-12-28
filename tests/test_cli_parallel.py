"""Tests for cli_parallel module - parallel directory processing."""

import json
import zipfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from cvextract.cli_config import UserConfig, ExtractStage, AdjustStage, ApplyStage, ParallelStage
from cvextract.cli_parallel import (
    scan_directory_for_docx,
    execute_parallel_pipeline,
    process_single_file_wrapper,
    _perform_upfront_research
)


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


class TestScanDirectoryForDocx:
    """Tests for scan_directory_for_docx function."""
    
    def test_scan_directory_success(self, test_directory: Path):
        """Test scanning directory returns all DOCX files."""
        files = scan_directory_for_docx(test_directory)
        
        # Should find 5 files (3 in root, 2 in subdir, ignore temp)
        assert len(files) == 5
        
        # Verify all are Path objects
        assert all(isinstance(f, Path) for f in files)
        
        # Verify all end with .docx
        assert all(f.suffix == ".docx" for f in files)
        
        # Verify temp file is not included
        assert all(not f.name.startswith("~$") for f in files)
    
    def test_scan_directory_not_found(self, tmp_path: Path):
        """Test scanning non-existent directory raises FileNotFoundError."""
        non_existent = tmp_path / "does_not_exist"
        with pytest.raises(FileNotFoundError):
            scan_directory_for_docx(non_existent)
    
    def test_scan_directory_is_file(self, mock_docx: Path):
        """Test scanning a file instead of directory raises ValueError."""
        with pytest.raises(ValueError, match="not a directory"):
            scan_directory_for_docx(mock_docx)
    
    def test_scan_empty_directory(self, tmp_path: Path):
        """Test scanning empty directory returns empty list."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        files = scan_directory_for_docx(empty_dir)
        assert files == []


class TestProcessSingleFileWrapper:
    """Tests for process_single_file_wrapper function."""
    
    @patch('cvextract.cli_parallel.execute_pipeline')
    def test_process_single_file_success(self, mock_execute, tmp_path: Path, mock_docx: Path):
        """Test processing single file successfully."""
        mock_execute.return_value = 0
        
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=None,
            apply=None,
            parallel=ParallelStage(input=tmp_path, n=1),
            target_dir=tmp_path / "out",
            strict=False,
            debug=False,
            log_file=None
        )
        
        success, message = process_single_file_wrapper(mock_docx, config)
        
        assert success is True
        assert message == "Success"
        mock_execute.assert_called_once()
    
    @patch('cvextract.cli_parallel.execute_pipeline')
    def test_process_single_file_with_warnings(self, mock_execute, tmp_path: Path, mock_docx: Path):
        """Test processing file with warnings (exit code 2)."""
        mock_execute.return_value = 2
        
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=None,
            apply=None,
            parallel=ParallelStage(input=tmp_path, n=1),
            target_dir=tmp_path / "out",
            strict=False,
            debug=False,
            log_file=None
        )
        
        success, message = process_single_file_wrapper(mock_docx, config)
        
        assert success is True
        assert "warnings" in message.lower()
    
    @patch('cvextract.cli_parallel.execute_pipeline')
    def test_process_single_file_failure(self, mock_execute, tmp_path: Path, mock_docx: Path):
        """Test processing file that fails."""
        mock_execute.return_value = 1
        
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=None,
            apply=None,
            parallel=ParallelStage(input=tmp_path, n=1),
            target_dir=tmp_path / "out",
            strict=False,
            debug=False,
            log_file=None
        )
        
        success, message = process_single_file_wrapper(mock_docx, config)
        
        assert success is False
        assert "failed" in message.lower()
    
    @patch('cvextract.cli_parallel.execute_pipeline')
    def test_process_single_file_exception(self, mock_execute, tmp_path: Path, mock_docx: Path):
        """Test processing file that raises exception."""
        mock_execute.side_effect = Exception("Test error")
        
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=None,
            apply=None,
            parallel=ParallelStage(input=tmp_path, n=1),
            target_dir=tmp_path / "out",
            strict=False,
            debug=False,
            log_file=None
        )
        
        success, message = process_single_file_wrapper(mock_docx, config)
        
        assert success is False
        assert "Test error" in message


class TestExecuteParallelPipeline:
    """Tests for execute_parallel_pipeline function."""
    
    @patch('cvextract.cli_parallel.process_single_file_wrapper')
    def test_parallel_pipeline_all_success(self, mock_process, tmp_path: Path, test_directory: Path):
        """Test parallel pipeline with all files succeeding."""
        mock_process.return_value = (True, "Success")
        
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=None,
            apply=None,
            parallel=ParallelStage(input=test_directory, n=2),
            target_dir=tmp_path / "out",
            strict=False,
            debug=False,
            log_file=None
        )
        
        exit_code = execute_parallel_pipeline(config)
        
        assert exit_code == 0
        # Should have been called for each file (5 times)
        assert mock_process.call_count == 5
    
    @patch('cvextract.cli_parallel.process_single_file_wrapper')
    def test_parallel_pipeline_some_failures(self, mock_process, tmp_path: Path, test_directory: Path):
        """Test parallel pipeline with some files failing."""
        # Alternate between success and failure
        mock_process.side_effect = [
            (True, "Success"),
            (False, "Error"),
            (True, "Success"),
            (False, "Error"),
            (True, "Success"),
        ]
        
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=None,
            apply=None,
            parallel=ParallelStage(input=test_directory, n=2),
            target_dir=tmp_path / "out",
            strict=False,
            debug=False,
            log_file=None
        )
        
        exit_code = execute_parallel_pipeline(config)
        
        assert exit_code == 1  # Should fail if any file fails
        assert mock_process.call_count == 5
    
    def test_parallel_pipeline_no_config(self, tmp_path: Path):
        """Test that calling without parallel config raises error."""
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=None,
            apply=None,
            parallel=None,  # No parallel config
            target_dir=tmp_path / "out",
            strict=False,
            debug=False,
            log_file=None
        )
        
        with pytest.raises(ValueError, match="without parallel configuration"):
            execute_parallel_pipeline(config)
    
    def test_parallel_pipeline_directory_not_found(self, tmp_path: Path):
        """Test parallel pipeline with non-existent directory."""
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=None,
            apply=None,
            parallel=ParallelStage(input=tmp_path / "does_not_exist", n=1),
            target_dir=tmp_path / "out",
            strict=False,
            debug=False,
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
            apply=None,
            parallel=ParallelStage(input=empty_dir, n=1),
            target_dir=tmp_path / "out",
            strict=False,
            debug=False,
            log_file=None
        )
        
        exit_code = execute_parallel_pipeline(config)
        assert exit_code == 1
    
    @patch('cvextract.cli_parallel.process_single_file_wrapper')
    @patch('cvextract.cli_parallel._perform_upfront_research')
    def test_parallel_pipeline_with_adjust(self, mock_research, mock_process, tmp_path: Path, test_directory: Path):
        """Test parallel pipeline with adjust stage performs upfront research."""
        mock_research.return_value = tmp_path / "research.json"
        mock_process.return_value = (True, "Success")
        
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=AdjustStage(
                data=None,
                output=None,
                customer_url="https://example.com",
                openai_model=None,
                dry_run=False
            ),
            apply=None,
            parallel=ParallelStage(input=test_directory, n=2),
            target_dir=tmp_path / "out",
            strict=False,
            debug=False,
            log_file=None
        )
        
        exit_code = execute_parallel_pipeline(config)
        
        assert exit_code == 0
        # Verify research was called once
        mock_research.assert_called_once_with(config)
    
    @patch('cvextract.cli_parallel.process_single_file_wrapper')
    def test_parallel_pipeline_strict_mode_with_warnings(self, mock_process, tmp_path: Path, test_directory: Path):
        """Test parallel pipeline in strict mode with warnings returns exit code 2."""
        mock_process.return_value = (True, "Success with warnings (strict mode)")
        
        config = UserConfig(
            extract=ExtractStage(source=Path('.'), output=None),
            adjust=None,
            apply=None,
            parallel=ParallelStage(input=test_directory, n=2),
            target_dir=tmp_path / "out",
            strict=True,  # Strict mode enabled
            debug=False,
            log_file=None
        )
        
        exit_code = execute_parallel_pipeline(config)
        
        assert exit_code == 2  # Strict mode with warnings


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
                data=None,
                output=None,
                customer_url="https://example.com",
                openai_model=None,
                dry_run=False
            ),
            apply=None,
            parallel=None,
            target_dir=tmp_path / "out",
            strict=False,
            debug=False,
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
            apply=None,
            parallel=None,
            target_dir=tmp_path / "out",
            strict=False,
            debug=False,
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
                data=None,
                output=None,
                customer_url="https://example.com",
                openai_model=None,
                dry_run=False
            ),
            apply=None,
            parallel=None,
            target_dir=tmp_path / "out",
            strict=False,
            debug=False,
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
                data=None,
                output=None,
                customer_url="https://example.com",
                openai_model=None,
                dry_run=False
            ),
            apply=None,
            parallel=None,
            target_dir=tmp_path / "out",
            strict=False,
            debug=False,
            log_file=None
        )
        
        cache_path = _perform_upfront_research(config)
        assert cache_path is None
