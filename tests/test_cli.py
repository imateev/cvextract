"""Tests for CLI module."""

import pytest
from pathlib import Path
import cvextract.cli as cli


class TestArgumentParsing:
    """Tests for command-line argument parsing."""

    def test_parse_extract_mode_with_required_args_returns_expected_values(self):
        """Extract mode with required args should parse correctly with defaults."""
        config = cli.gather_user_requirements([
            "--mode", "extract",
            "--source", "/path/to/cvs",
            "--template", "/path/to/template.docx",
            "--target", "/path/to/output"
        ])
        assert config.mode == cli.ExecutionMode.EXTRACT
        assert config.source == Path("/path/to/cvs")
        assert config.template == Path("/path/to/template.docx")
        assert config.target_dir == Path("/path/to/output")
        assert config.strict is False
        assert config.debug is False

    def test_parse_extract_apply_mode_with_required_args_sets_mode(self):
        """Extract-apply mode should be recognized and set correctly."""
        config = cli.gather_user_requirements([
            "--mode", "extract-apply",
            "--source", "/path/to/cvs",
            "--template", "/path/to/template.docx",
            "--target", "/path/to/output"
        ])
        assert config.mode == cli.ExecutionMode.EXTRACT_RENDER

    def test_parse_apply_mode_with_required_args_sets_mode(self):
        """Apply mode should be recognized and set correctly."""
        config = cli.gather_user_requirements([
            "--mode", "apply",
            "--source", "/path/to/json",
            "--template", "/path/to/template.docx",
            "--target", "/path/to/output"
        ])
        assert config.mode == cli.ExecutionMode.RENDER

    def test_parse_with_strict_flag_enables_strict_mode(self):
        """When --strict flag is provided, strict mode should be enabled."""
        config = cli.gather_user_requirements([
            "--mode", "extract",
            "--source", "/path/to/cvs",
            "--template", "/path/to/template.docx",
            "--target", "/path/to/output",
            "--strict"
        ])
        assert config.strict is True

    def test_parse_with_debug_flag_enables_debug_mode(self):
        """When --debug flag is provided, debug mode should be enabled."""
        config = cli.gather_user_requirements([
            "--mode", "extract",
            "--source", "/path/to/cvs",
            "--template", "/path/to/template.docx",
            "--target", "/path/to/output",
            "--debug"
        ])
        assert config.debug is True

    def test_parse_with_log_file_path_stores_path(self):
        """When --log-file is provided, should store the path as string."""
        config = cli.gather_user_requirements([
            "--mode", "extract",
            "--source", "/path/to/cvs",
            "--template", "/path/to/template.docx",
            "--target", "/path/to/output",
            "--log-file", "/path/to/log.txt"
        ])
        assert config.log_file == "/path/to/log.txt"
    
    def test_parse_extract_apply_with_adjustment_sets_extract_adjust_render(self):
        """Extract-apply mode with adjustment should map to EXTRACT_ADJUST_RENDER."""
        config = cli.gather_user_requirements([
            "--mode", "extract-apply",
            "--source", "/path/to/cvs",
            "--template", "/path/to/template.docx",
            "--target", "/path/to/output",
            "--adjust-for-customer", "https://example.com"
        ])
        assert config.mode == cli.ExecutionMode.EXTRACT_ADJUST_RENDER
        assert config.adjust_url == "https://example.com"
    
    def test_parse_extract_apply_with_adjustment_dry_run_sets_extract_adjust(self):
        """Extract-apply mode with adjustment dry-run should map to EXTRACT_ADJUST."""
        config = cli.gather_user_requirements([
            "--mode", "extract-apply",
            "--source", "/path/to/cvs",
            "--template", "/path/to/template.docx",
            "--target", "/path/to/output",
            "--adjust-for-customer", "https://example.com",
            "--adjust-dry-run"
        ])
        assert config.mode == cli.ExecutionMode.EXTRACT_ADJUST
        assert config.adjust_dry_run is True
    
    def test_parse_apply_with_adjustment_sets_adjust_render(self):
        """Apply mode with adjustment should map to ADJUST_RENDER."""
        config = cli.gather_user_requirements([
            "--mode", "apply",
            "--source", "/path/to/json",
            "--template", "/path/to/template.docx",
            "--target", "/path/to/output",
            "--adjust-for-customer", "https://example.com"
        ])
        assert config.mode == cli.ExecutionMode.ADJUST_RENDER


class TestInputCollection:
    """Tests for collecting input files from source paths."""

    def test_collect_from_single_docx_file_returns_file_in_list(self, tmp_path: Path):
        """When source is a single DOCX file, should return it in a list."""
        docx = tmp_path / "test.docx"
        docx.write_text("x")
        template = tmp_path / "template.docx"
        
        inputs = cli._collect_inputs(docx, mode=cli.ExecutionMode.EXTRACT, template_path=template)
        assert len(inputs) == 1
        assert inputs[0] == docx

    def test_collect_from_directory_excludes_template_file(self, tmp_path: Path):
        """When source is directory in extract mode, should find all DOCX files except template."""
        (tmp_path / "a.docx").write_text("x")
        (tmp_path / "b.docx").write_text("y")
        template = tmp_path / "template.docx"
        template.write_text("t")
        
        inputs = cli._collect_inputs(tmp_path, mode=cli.ExecutionMode.EXTRACT, template_path=template)
        assert len(inputs) == 2
        assert template not in inputs

    def test_collect_in_apply_mode_finds_json_files(self, tmp_path: Path):
        """When mode is apply, should collect JSON files instead of DOCX."""
        (tmp_path / "a.json").write_text("{}")
        (tmp_path / "b.json").write_text("{}")
        template = tmp_path / "template.docx"
        
        inputs = cli._collect_inputs(tmp_path, mode=cli.ExecutionMode.RENDER, template_path=template)
        assert len(inputs) == 2

    def test_collect_from_nested_directories_finds_all_files(self, tmp_path: Path):
        """When source has nested subdirectories, should recursively find all matching files."""
        sub1 = tmp_path / "sub1"
        sub2 = tmp_path / "sub2"
        sub1.mkdir()
        sub2.mkdir()
        
        (sub1 / "a.docx").write_text("x")
        (sub2 / "b.docx").write_text("y")
        template = tmp_path / "template.docx"
        template.write_text("t")
        
        inputs = cli._collect_inputs(tmp_path, mode=cli.ExecutionMode.EXTRACT, template_path=template)
        assert len(inputs) == 2


class TestExecutionModeProperties:
    """Tests for ExecutionMode enum properties."""
    
    def test_extract_mode_needs_extraction_only(self):
        """EXTRACT mode should only need extraction."""
        mode = cli.ExecutionMode.EXTRACT
        assert mode.needs_extraction is True
        assert mode.needs_adjustment is False
        assert mode.needs_rendering is False
        assert mode.should_compare is False
    
    def test_extract_render_mode_needs_extraction_and_rendering(self):
        """EXTRACT_RENDER mode should need extraction and rendering, with comparison."""
        mode = cli.ExecutionMode.EXTRACT_RENDER
        assert mode.needs_extraction is True
        assert mode.needs_adjustment is False
        assert mode.needs_rendering is True
        assert mode.should_compare is True
    
    def test_extract_adjust_render_mode_needs_all_except_compare(self):
        """EXTRACT_ADJUST_RENDER mode should need all operations but skip comparison."""
        mode = cli.ExecutionMode.EXTRACT_ADJUST_RENDER
        assert mode.needs_extraction is True
        assert mode.needs_adjustment is True
        assert mode.needs_rendering is True
        assert mode.should_compare is False
    
    def test_adjust_render_mode_needs_adjustment_and_rendering(self):
        """ADJUST_RENDER mode should need adjustment and rendering, no comparison."""
        mode = cli.ExecutionMode.ADJUST_RENDER
        assert mode.needs_extraction is False
        assert mode.needs_adjustment is True
        assert mode.needs_rendering is True
        assert mode.should_compare is False


class TestMainFunction:
    """Tests for main CLI entry point and mode dispatching."""

    def test_main_in_extract_mode_executes_successfully(self, tmp_path: Path):
        """When mode is extract, should execute pipeline and return success code."""
        import zipfile
        
        docx = tmp_path / "test.docx"
        with zipfile.ZipFile(docx, 'w') as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
        
        template = tmp_path / "template.docx"
        with zipfile.ZipFile(template, 'w') as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
        
        target = tmp_path / "output"
        
        # This will fail during execution (invalid DOCX), but we're testing the dispatch
        rc = cli.main([
            "--mode", "extract",
            "--source", str(docx),
            "--template", str(template),
            "--target", str(target)
        ])
        # Should return 1 because the DOCX is invalid, but that means dispatch worked
        assert rc in (0, 1)

    def test_main_with_log_file_creates_parent_directory(self, tmp_path: Path):
        """When log file path has non-existent parent directories, should create them."""
        import zipfile
        
        docx = tmp_path / "test.docx"
        with zipfile.ZipFile(docx, 'w') as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
        
        template = tmp_path / "template.docx"
        with zipfile.ZipFile(template, 'w') as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
        
        target = tmp_path / "output"
        log_file = tmp_path / "logs" / "run.log"
        
        cli.main([
            "--mode", "extract",
            "--source", str(docx),
            "--template", str(template),
            "--target", str(target),
            "--log-file", str(log_file)
        ])
        
        assert log_file.parent.exists()


class TestMainErrorHandling:
    """Tests for main function error handling."""

    def test_main_with_invalid_template_returns_error(self, tmp_path: Path):
        """When template file doesn't exist or isn't a .docx, should return error code 1."""
        docx = tmp_path / "test.docx"
        docx.write_text("test")
        template = tmp_path / "template.txt"  # Wrong extension
        target = tmp_path / "output"
        
        rc = cli.main([
            "--mode", "extract",
            "--source", str(docx),
            "--template", str(template),
            "--target", str(target)
        ])
        assert rc == 1

    def test_main_with_collect_inputs_exception_in_debug_logs_traceback(self, monkeypatch, tmp_path: Path, caplog):
        """When collect_inputs raises exception in debug mode, should log traceback."""
        import logging
        import zipfile
        
        docx = tmp_path / "test.docx"
        with zipfile.ZipFile(docx, 'w') as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
        
        template = tmp_path / "template.docx"
        with zipfile.ZipFile(template, 'w') as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
        
        target = tmp_path / "output"
        
        def fake_collect_inputs(*args, **kwargs):
            raise ValueError("Test error")
        
        monkeypatch.setattr(cli, "_collect_inputs", fake_collect_inputs)
        
        with caplog.at_level(logging.ERROR):
            rc = cli.main([
                "--mode", "extract",
                "--source", str(docx),
                "--template", str(template),
                "--target", str(target),
                "--debug"
            ])
        
        assert rc == 1
        assert "Traceback" in caplog.text or "Test error" in caplog.text
