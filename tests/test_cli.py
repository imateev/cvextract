"""Tests for CLI module."""

import pytest
from pathlib import Path
import cvextract.cli as cli


class TestArgumentParsing:
    """Tests for command-line argument parsing."""

    def test_parse_extract_mode_with_required_args_returns_expected_values(self):
        """Extract mode with required args should parse correctly with defaults."""
        args = cli.parse_args([
            "--mode", "extract",
            "--source", "/path/to/cvs",
            "--template", "/path/to/template.docx",
            "--target", "/path/to/output"
        ])
        assert args.mode == "extract"
        assert args.source == "/path/to/cvs"
        assert args.template == "/path/to/template.docx"
        assert args.target == "/path/to/output"
        assert args.strict is False
        assert args.debug is False

    def test_parse_extract_apply_mode_with_required_args_sets_mode(self):
        """Extract-apply mode should be recognized and set correctly."""
        args = cli.parse_args([
            "--mode", "extract-apply",
            "--source", "/path/to/cvs",
            "--template", "/path/to/template.docx",
            "--target", "/path/to/output"
        ])
        assert args.mode == "extract-apply"

    def test_parse_apply_mode_with_required_args_sets_mode(self):
        """Apply mode should be recognized and set correctly."""
        args = cli.parse_args([
            "--mode", "apply",
            "--source", "/path/to/json",
            "--template", "/path/to/template.docx",
            "--target", "/path/to/output"
        ])
        assert args.mode == "apply"

    def test_parse_with_strict_flag_enables_strict_mode(self):
        """When --strict flag is provided, strict mode should be enabled."""
        args = cli.parse_args([
            "--mode", "extract",
            "--source", "/path/to/cvs",
            "--template", "/path/to/template.docx",
            "--target", "/path/to/output",
            "--strict"
        ])
        assert args.strict is True

    def test_parse_with_debug_flag_enables_debug_mode(self):
        """When --debug flag is provided, debug mode should be enabled."""
        args = cli.parse_args([
            "--mode", "extract",
            "--source", "/path/to/cvs",
            "--template", "/path/to/template.docx",
            "--target", "/path/to/output",
            "--debug"
        ])
        assert args.debug is True

    def test_parse_with_log_file_path_stores_path(self):
        """When --log-file is provided, should store the path as string."""
        args = cli.parse_args([
            "--mode", "extract",
            "--source", "/path/to/cvs",
            "--template", "/path/to/template.docx",
            "--target", "/path/to/output",
            "--log-file", "/path/to/log.txt"
        ])
        assert args.log_file == "/path/to/log.txt"


class TestInputCollection:
    """Tests for collecting input files from source paths."""

    def test_collect_from_single_docx_file_returns_file_in_list(self, tmp_path: Path):
        """When source is a single DOCX file, should return it in a list."""
        docx = tmp_path / "test.docx"
        docx.write_text("x")
        template = tmp_path / "template.docx"
        
        inputs = cli.collect_inputs(docx, mode="extract", template_path=template)
        assert len(inputs) == 1
        assert inputs[0] == docx

    def test_collect_from_directory_excludes_template_file(self, tmp_path: Path):
        """When source is directory in extract mode, should find all DOCX files except template."""
        (tmp_path / "a.docx").write_text("x")
        (tmp_path / "b.docx").write_text("y")
        template = tmp_path / "template.docx"
        template.write_text("t")
        
        inputs = cli.collect_inputs(tmp_path, mode="extract", template_path=template)
        assert len(inputs) == 2
        assert template not in inputs

    def test_collect_in_apply_mode_finds_json_files(self, tmp_path: Path):
        """When mode is apply, should collect JSON files instead of DOCX."""
        (tmp_path / "a.json").write_text("{}")
        (tmp_path / "b.json").write_text("{}")
        template = tmp_path / "template.docx"
        
        inputs = cli.collect_inputs(tmp_path, mode="apply", template_path=template)
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
        
        inputs = cli.collect_inputs(tmp_path, mode="extract", template_path=template)
        assert len(inputs) == 2


class TestMainFunction:
    """Tests for main CLI entry point and mode dispatching."""

    def test_main_in_extract_mode_dispatches_to_extract_pipeline(self, monkeypatch, tmp_path: Path):
        """When mode is extract, should call run_extract_mode and return its exit code."""
        import zipfile
        
        docx = tmp_path / "test.docx"
        with zipfile.ZipFile(docx, 'w') as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
        
        template = tmp_path / "template.docx"
        with zipfile.ZipFile(template, 'w') as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
        
        target = tmp_path / "output"
        
        call_count = {"count": 0}
        
        def fake_run_extract(inputs, target_dir, strict, debug):
            call_count["count"] += 1
            return 0
        
        monkeypatch.setattr(cli, "run_extract_mode", fake_run_extract)
        
        rc = cli.main([
            "--mode", "extract",
            "--source", str(docx),
            "--template", str(template),
            "--target", str(target)
        ])
        assert rc == 0
        assert call_count["count"] == 1

    def test_main_in_extract_apply_mode_dispatches_to_extract_apply_pipeline(self, monkeypatch, tmp_path: Path):
        """When mode is extract-apply, should call run_extract_apply_mode and return its exit code."""
        import zipfile
        
        docx = tmp_path / "test.docx"
        with zipfile.ZipFile(docx, 'w') as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
        
        template = tmp_path / "template.docx"
        with zipfile.ZipFile(template, 'w') as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
        
        target = tmp_path / "output"
        
        call_count = {"count": 0}
        
        def fake_run_extract_apply(inputs, template_path, target_dir, strict, debug):
            call_count["count"] += 1
            return 0
        
        monkeypatch.setattr(cli, "run_extract_apply_mode", fake_run_extract_apply)
        
        rc = cli.main([
            "--mode", "extract-apply",
            "--source", str(docx),
            "--template", str(template),
            "--target", str(target)
        ])
        assert rc == 0
        assert call_count["count"] == 1

    def test_main_in_apply_mode_dispatches_to_apply_pipeline(self, monkeypatch, tmp_path: Path, caplog):
        """When mode is apply, should call run_apply_mode and return its exit code."""
        import zipfile
        import logging
        
        json_file = tmp_path / "test.json"
        json_file.write_text("{}")
        
        template = tmp_path / "template.docx"
        with zipfile.ZipFile(template, 'w') as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
        
        target = tmp_path / "output"
        
        call_count = {"count": 0}
        
        def fake_run_apply(inputs, template_path, target_dir, debug):
            call_count["count"] += 1
            return 0
        
        monkeypatch.setattr(cli, "run_apply_mode", fake_run_apply)
        
        with caplog.at_level(logging.DEBUG):
            rc = cli.main([
                "--mode", "apply",
                "--source", str(json_file),
                "--template", str(template),
                "--target", str(target)
            ])
        
        if rc != 0:
            print(f"Return code: {rc}")
            print(f"Logs: {caplog.text}")
        
        assert rc == 0
        assert call_count["count"] == 1

    def test_main_with_log_file_creates_parent_directory(self, monkeypatch, tmp_path: Path):
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
        
        def fake_run_extract(inputs, target_dir, strict, debug):
            return 0
        
        monkeypatch.setattr(cli, "run_extract_mode", fake_run_extract)
        
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
        
        monkeypatch.setattr(cli, "collect_inputs", fake_collect_inputs)
        
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
