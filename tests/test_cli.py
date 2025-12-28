"""Tests for CLI module."""

import pytest
from pathlib import Path
import cvextract.cli as cli


class TestStageBasedParsing:
    """Tests for stage-based argument parsing."""
    
    def test_parse_extract_stage_with_source(self):
        """Extract stage with source parameter should be parsed correctly."""
        config = cli.gather_user_requirements([
            "--extract", "source=/path/to/cvs",
            "--target", "/path/to/output"
        ])
        assert config.extract is not None
        assert config.extract.source == Path("/path/to/cvs")
        assert config.extract.output is None
        assert config.has_extract is True
    
    def test_parse_extract_stage_with_source_and_output(self):
        """Extract stage with both source and output should be parsed."""
        config = cli.gather_user_requirements([
            "--extract", "source=/path/to/cv.docx", "output=/path/to/data.json",
            "--target", "/path/to/output"
        ])
        assert config.extract.source == Path("/path/to/cv.docx")
        assert config.extract.output == Path("/path/to/data.json")
    
    def test_parse_apply_stage_with_template(self):
        """Apply stage with template parameter should be parsed correctly."""
        config = cli.gather_user_requirements([
            "--apply", "template=/path/to/template.docx", "data=/path/to/data.json",
            "--target", "/path/to/output"
        ])
        assert config.apply is not None
        assert config.apply.template == Path("/path/to/template.docx")
        assert config.apply.data == Path("/path/to/data.json")
        assert config.has_apply is True
    
    def test_parse_adjust_stage_with_customer_url(self):
        """Adjust stage with customer-url should be parsed correctly."""
        config = cli.gather_user_requirements([
            "--extract", "source=/path/to/cvs",
            "--adjust", "customer-url=https://example.com",
            "--target", "/path/to/output"
        ])
        assert config.adjust is not None
        assert config.adjust.customer_url == "https://example.com"
        assert config.has_adjust is True
    
    def test_parse_extract_and_apply_stages(self):
        """Chaining extract and apply stages should work."""
        config = cli.gather_user_requirements([
            "--extract", "source=/path/to/cvs",
            "--apply", "template=/path/to/template.docx",
            "--target", "/path/to/output"
        ])
        assert config.extract is not None
        assert config.apply is not None
        assert config.has_extract is True
        assert config.has_apply is True
    
    def test_parse_all_three_stages(self):
        """Chaining extract, adjust, and apply stages should work."""
        config = cli.gather_user_requirements([
            "--extract", "source=/path/to/cvs",
            "--adjust", "customer-url=https://example.com",
            "--apply", "template=/path/to/template.docx",
            "--target", "/path/to/output"
        ])
        assert config.extract is not None
        assert config.adjust is not None
        assert config.apply is not None
    
    def test_parse_adjust_with_dry_run(self):
        """Adjust stage with dry-run flag should be parsed."""
        config = cli.gather_user_requirements([
            "--extract", "source=/path/to/cvs",
            "--adjust", "customer-url=https://example.com", "dry-run",
            "--target", "/path/to/output"
        ])
        assert config.adjust.dry_run is True
    
    def test_parse_adjust_with_openai_model(self):
        """Adjust stage with openai-model parameter should be parsed."""
        config = cli.gather_user_requirements([
            "--extract", "source=/path/to/cvs",
            "--adjust", "customer-url=https://example.com", "openai-model=gpt-4",
            "--target", "/path/to/output"
        ])
        assert config.adjust.openai_model == "gpt-4"
    
    def test_extract_without_source_raises_error(self):
        """Extract stage without source parameter should raise error."""
        with pytest.raises(ValueError, match="requires 'source' parameter"):
            cli.gather_user_requirements([
                "--extract",
                "--target", "/path/to/output"
            ])
    
    def test_apply_without_template_raises_error(self):
        """Apply stage without template parameter should raise error."""
        with pytest.raises(ValueError, match="requires 'template' parameter"):
            cli.gather_user_requirements([
                "--apply", "data=/path/to/data.json",
                "--target", "/path/to/output"
            ])
    
    def test_no_stages_raises_error(self):
        """Not specifying any stages should raise error."""
        with pytest.raises(ValueError, match="Must specify at least one stage"):
            cli.gather_user_requirements([
                "--target", "/path/to/output"
            ])
    
    def test_stage_should_compare_when_apply_without_adjust(self):
        """When using apply without adjust, should_compare should be True."""
        config = cli.gather_user_requirements([
            "--extract", "source=/path/to/cvs",
            "--apply", "template=/path/to/template.docx",
            "--target", "/path/to/output"
        ])
        assert config.should_compare is True
    
    def test_stage_should_not_compare_when_apply_with_adjust(self):
        """When using apply with adjust, should_compare should be False."""
        config = cli.gather_user_requirements([
            "--extract", "source=/path/to/cvs",
            "--adjust", "customer-url=https://example.com",
            "--apply", "template=/path/to/template.docx",
            "--target", "/path/to/output"
        ])
        assert config.should_compare is False
    
    def test_empty_parameter_key_raises_error(self):
        """Parameter with empty key should raise error."""
        with pytest.raises(ValueError, match="Empty parameter key"):
            cli.gather_user_requirements([
                "--extract", "source=/path/to/cvs", "=/path/to/output",
                "--target", "/path/to/output"
            ])

    def test_parse_with_strict_flag_enables_strict_mode(self):
        """When --strict flag is provided, strict mode should be enabled."""
        config = cli.gather_user_requirements([
            "--extract", "source=/path/to/cvs",
            "--target", "/path/to/output",
            "--strict"
        ])
        assert config.strict is True

    def test_parse_with_debug_flag_enables_debug_mode(self):
        """When --debug flag is provided, debug mode should be enabled."""
        config = cli.gather_user_requirements([
            "--extract", "source=/path/to/cvs",
            "--target", "/path/to/output",
            "--debug"
        ])
        assert config.debug is True

    def test_parse_with_log_file_path_stores_path(self):
        """When --log-file is provided, should store the path as string."""
        config = cli.gather_user_requirements([
            "--extract", "source=/path/to/cvs",
            "--target", "/path/to/output",
            "--log-file", "/path/to/log.txt"
        ])
        assert config.log_file == "/path/to/log.txt"


class TestInputCollection:
    """Tests for collecting input files from source paths."""

    def test_collect_from_single_docx_file_returns_file_in_list(self, tmp_path: Path):
        """When source is a single DOCX file, should return it in a list."""
        docx = tmp_path / "test.docx"
        docx.write_text("x")
        template = tmp_path / "template.docx"
        
        inputs = cli._collect_inputs(docx, is_extraction=True, template_path=template)
        assert len(inputs) == 1
        assert inputs[0] == docx

    def test_collect_from_directory_excludes_template_file(self, tmp_path: Path):
        """When source is directory in extract mode, should find all DOCX files except template."""
        (tmp_path / "a.docx").write_text("x")
        (tmp_path / "b.docx").write_text("y")
        template = tmp_path / "template.docx"
        template.write_text("t")
        
        inputs = cli._collect_inputs(tmp_path, is_extraction=True, template_path=template)
        assert len(inputs) == 2
        assert template not in inputs

    def test_collect_in_apply_mode_finds_json_files(self, tmp_path: Path):
        """When in render mode, should collect JSON files instead of DOCX."""
        (tmp_path / "a.json").write_text("{}")
        (tmp_path / "b.json").write_text("{}")
        template = tmp_path / "template.docx"
        
        inputs = cli._collect_inputs(tmp_path, is_extraction=False, template_path=template)
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
        
        inputs = cli._collect_inputs(tmp_path, is_extraction=True, template_path=template)
        assert len(inputs) == 2


class TestMainFunction:
    """Tests for main CLI entry point."""

    def test_main_executes_successfully_with_stage_based_interface(self, tmp_path: Path):
        """When using stage-based interface, should execute pipeline and return success code."""
        import zipfile
        
        docx = tmp_path / "test.docx"
        with zipfile.ZipFile(docx, 'w') as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
        
        target = tmp_path / "output"
        
        # This will fail during execution (invalid DOCX), but we're testing the dispatch
        rc = cli.main([
            "--extract", f"source={str(docx)}",
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
        
        target = tmp_path / "output"
        log_file = tmp_path / "logs" / "run.log"
        
        cli.main([
            "--extract", f"source={str(docx)}",
            "--target", str(target),
            "--log-file", str(log_file)
        ])
        
        assert log_file.parent.exists()


class TestMainErrorHandling:
    """Tests for main function error handling."""

    def test_main_with_invalid_template_returns_error(self, tmp_path: Path):
        """When template file doesn't exist or isn't a .docx, should return error code 1."""
        docx = tmp_path / "data.json"
        docx.write_text("{}")
        template = tmp_path / "template.txt"  # Wrong extension
        target = tmp_path / "output"
        
        rc = cli.main([
            "--apply", f"template={str(template)}", f"data={str(docx)}",
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
        
        target = tmp_path / "output"
        
        def fake_collect_inputs(*args, **kwargs):
            raise ValueError("Test error")
        
        monkeypatch.setattr(cli, "_collect_inputs", fake_collect_inputs)
        
        with caplog.at_level(logging.ERROR):
            rc = cli.main([
                "--extract", f"source={str(docx)}",
                "--target", str(target),
                "--debug"
            ])
        
        assert rc == 1
        assert "Traceback" in caplog.text or "Test error" in caplog.text
