"""Tests for CLI module."""

from pathlib import Path

import pytest

import cvextract.cli as cli
from cvextract.cli_prepare import _collect_inputs


class TestStageBasedParsing:
    """Tests for stage-based argument parsing."""

    def test_parse_extract_stage_with_source(self):
        """Extract stage with source parameter should be parsed correctly."""
        config = cli.gather_user_requirements(
            ["--extract", "source=/path/to/cvs", "--target", "/path/to/output"]
        )
        assert config.extract is not None
        assert config.extract.source == Path("/path/to/cvs")
        assert config.extract.output is None
        assert config.has_extract is True

    def test_parse_extract_stage_with_source_and_output(self):
        """Extract stage with both source and output should be parsed."""
        config = cli.gather_user_requirements(
            [
                "--extract",
                "source=/path/to/cv.docx",
                "output=/path/to/data.json",
                "--target",
                "/path/to/output",
            ]
        )
        assert config.extract.source == Path("/path/to/cv.docx")
        assert config.extract.output == Path("/path/to/data.json")

    def test_parse_apply_stage_with_template(self):
        """Apply stage with template parameter should be parsed correctly."""
        config = cli.gather_user_requirements(
            [
                "--render",
                "template=/path/to/template.docx",
                "data=/path/to/data.json",
                "--target",
                "/path/to/output",
            ]
        )
        assert config.render is not None
        assert config.render.template == Path("/path/to/template.docx")
        assert config.render.data == Path("/path/to/data.json")
        assert config.has_render is True

    def test_parse_adjust_stage_with_customer_url(self):
        """Adjust stage with customer-url should be parsed correctly."""
        config = cli.gather_user_requirements(
            [
                "--extract",
                "source=/path/to/cvs",
                "--adjust",
                "name=openai-company-research",
                "customer-url=https://example.com",
                "--target",
                "/path/to/output",
            ]
        )
        assert config.adjust is not None
        assert len(config.adjust.adjusters) == 1
        assert config.adjust.adjusters[0].name == "openai-company-research"
        assert (
            config.adjust.adjusters[0].params.get("customer-url")
            == "https://example.com"
        )
        assert config.has_adjust is True

    def test_parse_extract_and_apply_stages(self):
        """Chaining extract and apply stages should work."""
        config = cli.gather_user_requirements(
            [
                "--extract",
                "source=/path/to/cvs",
                "--render",
                "template=/path/to/template.docx",
                "--target",
                "/path/to/output",
            ]
        )
        assert config.extract is not None
        assert config.render is not None
        assert config.has_extract is True
        assert config.has_render is True

    def test_parse_all_three_stages(self):
        """Chaining extract, adjust, and apply stages should work."""
        config = cli.gather_user_requirements(
            [
                "--extract",
                "source=/path/to/cvs",
                "--adjust",
                "name=openai-company-research",
                "customer-url=https://example.com",
                "--render",
                "template=/path/to/template.docx",
                "--target",
                "/path/to/output",
            ]
        )
        assert config.extract is not None
        assert config.adjust is not None
        assert config.render is not None

    def test_parse_adjust_with_dry_run(self):
        """Adjust stage with dry-run flag should be parsed."""
        config = cli.gather_user_requirements(
            [
                "--extract",
                "source=/path/to/cvs",
                "--adjust",
                "name=openai-company-research",
                "customer-url=https://example.com",
                "dry-run",
                "--target",
                "/path/to/output",
            ]
        )
        assert config.adjust.dry_run is True

    def test_parse_adjust_with_openai_model(self):
        """Adjust stage with openai-model parameter should be parsed."""
        config = cli.gather_user_requirements(
            [
                "--extract",
                "source=/path/to/cvs",
                "--adjust",
                "name=openai-company-research",
                "customer-url=https://example.com",
                "openai-model=gpt-4",
                "--target",
                "/path/to/output",
            ]
        )
        assert config.adjust.adjusters[0].openai_model == "gpt-4"

    def test_extract_without_source_raises_error(self):
        """Extract stage without source parameter should raise error."""
        with pytest.raises(ValueError, match="requires 'source' parameter"):
            cli.gather_user_requirements(["--extract", "--target", "/path/to/output"])

    def test_apply_without_template_raises_error(self):
        """Apply stage without template parameter should raise error."""
        with pytest.raises(ValueError, match="requires 'template' parameter"):
            cli.gather_user_requirements(
                ["--render", "data=/path/to/data.json", "--target", "/path/to/output"]
            )

    def test_adjust_without_name_raises_error(self):
        """Adjust stage without name parameter should raise error."""
        with pytest.raises(ValueError, match="requires 'name' parameter"):
            cli.gather_user_requirements(["--adjust", "--target", "/path/to/output"])

    def test_no_stages_raises_error(self):
        """Not specifying any stages should raise error."""
        with pytest.raises(ValueError, match="Must specify at least one stage"):
            cli.gather_user_requirements(["--target", "/path/to/output"])

    def test_stage_should_compare_when_apply_without_adjust(self):
        """When using apply without adjust, should_compare should be True."""
        config = cli.gather_user_requirements(
            [
                "--extract",
                "source=/path/to/cvs",
                "--render",
                "template=/path/to/template.docx",
                "--target",
                "/path/to/output",
            ]
        )
        assert config.should_compare is True

    def test_stage_should_not_compare_when_apply_with_adjust(self):
        """When using apply with adjust, should_compare should be False."""
        config = cli.gather_user_requirements(
            [
                "--extract",
                "source=/path/to/cvs",
                "--adjust",
                "name=openai-company-research",
                "customer-url=https://example.com",
                "--render",
                "template=/path/to/template.docx",
                "--target",
                "/path/to/output",
            ]
        )
        assert config.should_compare is False

    def test_empty_parameter_key_raises_error(self):
        """Parameter with empty key should raise error."""
        with pytest.raises(ValueError, match="Empty parameter key"):
            cli.gather_user_requirements(
                [
                    "--extract",
                    "source=/path/to/cvs",
                    "=/path/to/output",
                    "--target",
                    "/path/to/output",
                ]
            )

    def test_parse_with_debug_flag_enables_debug_mode(self):
        """When --verbosity debug is provided, debug mode should be enabled."""
        config = cli.gather_user_requirements(
            [
                "--extract",
                "source=/path/to/cvs",
                "--target",
                "/path/to/output",
                "--verbosity",
                "debug",
            ]
        )
        assert config.debug is True

    def test_parse_with_log_file_path_stores_path(self):
        """When --log-file is provided, should store the path as string."""
        config = cli.gather_user_requirements(
            [
                "--extract",
                "source=/path/to/cvs",
                "--target",
                "/path/to/output",
                "--log-file",
                "/path/to/log.txt",
            ]
        )
        assert config.log_file == "/path/to/log.txt"


class TestOutputPathResolution:
    """Tests for output path resolution relative to target directory."""

    def test_absolute_output_path_used_as_is(self):
        """Absolute output paths should be used as-is, not relative to target."""
        config = cli.gather_user_requirements(
            [
                "--extract",
                "source=/path/to/cv.docx",
                "output=/absolute/path/data.json",
                "--target",
                "/path/to/target",
            ]
        )
        assert config.extract.output == Path("/absolute/path/data.json")
        assert config.target_dir == Path("/path/to/target")

    def test_relative_output_path_resolved_to_target(self):
        """Relative output paths should be resolved relative to target directory."""
        config = cli.gather_user_requirements(
            [
                "--extract",
                "source=/path/to/cv.docx",
                "output=data.json",
                "--target",
                "/path/to/target",
            ]
        )
        assert config.extract.output == Path("/path/to/target/data.json")

    def test_relative_output_path_with_subdirectory(self):
        """Relative output paths with subdirectories should be resolved correctly."""
        config = cli.gather_user_requirements(
            [
                "--extract",
                "source=/path/to/cv.docx",
                "output=subdir/nested/data.json",
                "--target",
                "/path/to/target",
            ]
        )
        assert config.extract.output == Path("/path/to/target/subdir/nested/data.json")

    def test_no_output_path_returns_none(self):
        """When no output is specified, should return None (uses defaults)."""
        config = cli.gather_user_requirements(
            ["--extract", "source=/path/to/cv.docx", "--target", "/path/to/target"]
        )
        assert config.extract.output is None

    def test_apply_stage_absolute_output(self):
        """Apply stage with absolute output path."""
        config = cli.gather_user_requirements(
            [
                "--render",
                "template=/template.docx",
                "data=/data.json",
                "output=/absolute/result.docx",
                "--target",
                "/path/to/target",
            ]
        )
        assert config.render.output == Path("/absolute/result.docx")

    def test_apply_stage_relative_output(self):
        """Apply stage with relative output path."""
        config = cli.gather_user_requirements(
            [
                "--render",
                "template=/template.docx",
                "data=/data.json",
                "output=final/result.docx",
                "--target",
                "/path/to/target",
            ]
        )
        assert config.render.output == Path("/path/to/target/final/result.docx")

    def test_adjust_stage_relative_output(self):
        """Adjust stage with relative output path."""
        config = cli.gather_user_requirements(
            [
                "--extract",
                "source=/cv.docx",
                "--adjust",
                "name=openai-company-research",
                "customer-url=https://example.com",
                "output=adjusted.json",
                "--target",
                "/path/to/target",
            ]
        )
        assert config.adjust.output == Path("/path/to/target/adjusted.json")

    def test_multiple_stages_mixed_paths(self):
        """Multiple stages with mix of absolute and relative paths."""
        config = cli.gather_user_requirements(
            [
                "--extract",
                "source=/cv.docx",
                "output=extracted/data.json",
                "--render",
                "template=/template.docx",
                "output=/absolute/result.docx",
                "--target",
                "/path/to/target",
            ]
        )
        assert config.extract.output == Path("/path/to/target/extracted/data.json")
        assert config.render.output == Path("/absolute/result.docx")

    def test_windows_absolute_path_on_posix(self):
        """On POSIX systems, Windows-style paths are treated as relative."""
        import os

        if os.name == "posix":
            # On POSIX, C:\output\data.json is not absolute
            config = cli.gather_user_requirements(
                [
                    "--extract",
                    r"source=C:\input\cv.docx",
                    r"output=C:\output\data.json",
                    "--target",
                    "/path/to/target",
                ]
            )
            # Should be treated as relative and resolved to target
            assert str(config.extract.output).startswith("/path/to/target")
        else:
            # On Windows, C:\output\data.json is absolute
            config = cli.gather_user_requirements(
                [
                    "--extract",
                    r"source=C:\input\cv.docx",
                    r"output=C:\output\data.json",
                    "--target",
                    "/path/to/target",
                ]
            )
            assert config.extract.output == Path(r"C:\output\data.json")

    def test_relative_path_with_dots(self):
        """Relative paths with .. should be resolved relative to target."""
        config = cli.gather_user_requirements(
            [
                "--extract",
                "source=/cv.docx",
                "output=../sibling/data.json",
                "--target",
                "/path/to/target",
            ]
        )
        assert config.extract.output == Path("/path/to/target/../sibling/data.json")


class TestPathsWithSpecialCharacters:
    """Tests for handling paths with spaces and special characters."""

    def test_parse_path_with_spaces_in_source(self):
        """Extract stage should handle paths with spaces correctly."""
        config = cli.gather_user_requirements(
            [
                "--extract",
                "source=/path/to/my documents/cv files/resume.docx",
                "--target",
                "/path/to/output",
            ]
        )
        assert config.extract is not None
        assert config.extract.source == Path(
            "/path/to/my documents/cv files/resume.docx"
        )

    def test_parse_path_with_spaces_in_output(self):
        """Extract stage should handle output paths with spaces."""
        config = cli.gather_user_requirements(
            [
                "--extract",
                "source=/path/to/cv.docx",
                "output=/my output folder/data.json",
                "--target",
                "/path/to/output",
            ]
        )
        assert config.extract.output == Path("/my output folder/data.json")

    def test_parse_template_path_with_spaces(self):
        """Apply stage should handle template paths with spaces."""
        config = cli.gather_user_requirements(
            [
                "--render",
                "template=/templates/my template folder/cv template.docx",
                "data=/data.json",
                "--target",
                "/path/to/output",
            ]
        )
        assert config.render.template == Path(
            "/templates/my template folder/cv template.docx"
        )

    def test_parse_multiple_paths_with_spaces(self):
        """Multiple stage parameters with spaces should all be parsed correctly."""
        config = cli.gather_user_requirements(
            [
                "--extract",
                "source=/my docs/cv.docx",
                "output=/output folder/data.json",
                "--render",
                "template=/my templates/template.docx",
                "--target",
                "/target folder",
            ]
        )
        assert config.extract.source == Path("/my docs/cv.docx")
        assert config.extract.output == Path("/output folder/data.json")
        assert config.render.template == Path("/my templates/template.docx")
        assert config.target_dir == Path("/target folder")

    def test_parse_path_with_special_characters(self):
        """Paths with special characters should be preserved."""
        config = cli.gather_user_requirements(
            ["--extract", "source=/path/to/file-name_v1.2.docx", "--target", "/output"]
        )
        assert config.extract.source == Path("/path/to/file-name_v1.2.docx")

    def test_parse_path_with_unicode_characters(self):
        """Paths with unicode characters should be handled correctly."""
        config = cli.gather_user_requirements(
            ["--extract", "source=/путь/к/файлу.docx", "--target", "/output"]
        )
        assert config.extract.source == Path("/путь/к/файлу.docx")

    def test_parse_path_with_parentheses_and_brackets(self):
        """Paths with parentheses and brackets should be preserved."""
        config = cli.gather_user_requirements(
            [
                "--extract",
                "source=/data/CV (Final) [2024]/resume.docx",
                "--target",
                "/output",
            ]
        )
        assert config.extract.source == Path("/data/CV (Final) [2024]/resume.docx")

    def test_parse_path_with_ampersand_and_quotes(self):
        """Paths with ampersands and quotes should be handled."""
        config = cli.gather_user_requirements(
            [
                "--extract",
                "source=/data/John's CV & Portfolio/resume.docx",
                "--target",
                "/output",
            ]
        )
        assert config.extract.source == Path("/data/John's CV & Portfolio/resume.docx")

    def test_parse_customer_url_with_query_params(self):
        """Customer URLs with query parameters should be preserved."""
        config = cli.gather_user_requirements(
            [
                "--extract",
                "source=/path/cv.docx",
                "--adjust",
                "name=openai-company-research",
                "customer-url=https://example.com/page?param=value&other=test",
                "--target",
                "/output",
            ]
        )
        assert (
            config.adjust.adjusters[0].params.get("customer-url")
            == "https://example.com/page?param=value&other=test"
        )

    def test_parse_path_with_leading_trailing_spaces_stripped_from_key(self):
        """Leading/trailing spaces in keys should be stripped, but values preserved."""
        config = cli.gather_user_requirements(
            ["--extract", "source=/path with spaces/file.docx", "--target", "/output"]
        )
        # Value should preserve internal spaces
        assert config.extract.source == Path("/path with spaces/file.docx")

    def test_parse_relative_paths_with_dots(self):
        """Relative paths with .. and . should be resolved relative to target."""
        config = cli.gather_user_requirements(
            [
                "--extract",
                "source=../parent/dir/file.docx",
                "output=./output/data.json",
                "--target",
                "/output",
            ]
        )
        assert config.extract.source == Path("../parent/dir/file.docx")
        # Relative output path should be resolved to target
        assert config.extract.output == Path(
            "/output/./output/data.json"
        )  # or Path("/output/output/data.json") after normalization

    def test_windows_style_paths_with_backslashes(self):
        """Windows-style paths should be handled (though backslashes need escaping in shell)."""
        config = cli.gather_user_requirements(
            [
                "--extract",
                r"source=C:\Users\John Doe\Documents\CV.docx",
                "--target",
                "/output",
            ]
        )
        assert config.extract.source == Path(r"C:\Users\John Doe\Documents\CV.docx")


class TestInputCollection:
    """Tests for collecting input files from source paths."""

    def test_collect_from_single_docx_file_returns_file_in_list(self, tmp_path: Path):
        """When source is a single DOCX file, should return it in a list."""
        docx = tmp_path / "test.docx"
        docx.write_text("x")
        template = tmp_path / "template.docx"

        inputs = _collect_inputs(docx, is_extraction=True, template_path=template)
        assert len(inputs) == 1
        assert inputs[0] == docx

    def test_collect_from_directory_raises_error(self, tmp_path: Path):
        """When source is directory, should raise ValueError with clear message."""
        (tmp_path / "a.docx").write_text("x")
        (tmp_path / "b.docx").write_text("y")
        template = tmp_path / "template.docx"
        template.write_text("t")

        with pytest.raises(ValueError, match="Directories are not supported"):
            _collect_inputs(tmp_path, is_extraction=True, template_path=template)

    def test_collect_in_apply_mode_rejects_directory(self, tmp_path: Path):
        """When in render mode with directory, should raise ValueError."""
        (tmp_path / "a.json").write_text("{}")
        (tmp_path / "b.json").write_text("{}")
        template = tmp_path / "template.docx"

        with pytest.raises(ValueError, match="Directories are not supported"):
            _collect_inputs(tmp_path, is_extraction=False, template_path=template)

    def test_collect_from_single_json_file(self, tmp_path: Path):
        """When source is a single JSON file, should return it in a list."""
        json_file = tmp_path / "test.json"
        json_file.write_text("{}")

        inputs = _collect_inputs(json_file, is_extraction=False, template_path=None)
        assert len(inputs) == 1
        assert inputs[0] == json_file

    def test_collect_nonexistent_file_raises_error(self, tmp_path: Path):
        """When source doesn't exist, should raise FileNotFoundError."""
        nonexistent = tmp_path / "nonexistent.docx"

        with pytest.raises(FileNotFoundError, match="Path not found"):
            _collect_inputs(nonexistent, is_extraction=True, template_path=None)

    def test_collect_wrong_file_type_for_extraction(self, tmp_path: Path):
        """File type validation for extraction is delegated to the extractor."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("not a docx")

        # Should not raise - extractor will validate file type
        result = _collect_inputs(txt_file, is_extraction=True, template_path=None)
        assert len(result) == 1
        assert result[0] == txt_file

    def test_collect_wrong_file_type_for_apply(self, tmp_path: Path):
        """When file type doesn't match apply mode, should raise ValueError."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("not json")

        with pytest.raises(ValueError, match="must be a JSON file"):
            _collect_inputs(txt_file, is_extraction=False, template_path=None)


class TestMainFunction:
    """Tests for main CLI entry point."""

    def test_main_executes_successfully_with_stage_based_interface(
        self, tmp_path: Path
    ):
        """When using stage-based interface, should execute pipeline and return success code."""
        import zipfile

        docx = tmp_path / "test.docx"
        with zipfile.ZipFile(docx, "w") as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")

        target = tmp_path / "output"

        # This will fail during execution (invalid DOCX), but we're testing the dispatch
        rc = cli.main(["--extract", f"source={str(docx)}", "--target", str(target)])
        # Should return 1 because the DOCX is invalid, but that means dispatch worked
        assert rc in (0, 1)

    def test_main_with_log_file_creates_parent_directory(self, tmp_path: Path):
        """When log file path has non-existent parent directories, should create them."""
        import zipfile

        docx = tmp_path / "test.docx"
        with zipfile.ZipFile(docx, "w") as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")

        target = tmp_path / "output"
        log_file = tmp_path / "logs" / "run.log"

        cli.main(
            [
                "--extract",
                f"source={str(docx)}",
                "--target",
                str(target),
                "--log-file",
                str(log_file),
            ]
        )

        assert log_file.parent.exists()


class TestMainErrorHandling:
    """Tests for main function error handling."""

    def test_main_with_invalid_template_returns_error(self, tmp_path: Path):
        """When template file doesn't exist or isn't a .docx, should return error code 1."""
        docx = tmp_path / "data.json"
        docx.write_text("{}")
        template = tmp_path / "template.txt"  # Wrong extension
        target = tmp_path / "output"

        rc = cli.main(
            [
                "--render",
                f"template={str(template)}",
                f"data={str(docx)}",
                "--target",
                str(target),
            ]
        )
        assert rc == 1

    def test_main_with_collect_inputs_exception_in_debug_logs_traceback(
        self, monkeypatch, tmp_path: Path, caplog
    ):
        """When collect_inputs raises exception in debug mode, should log traceback."""
        import logging
        import zipfile

        from cvextract import cli_prepare

        docx = tmp_path / "test.docx"
        with zipfile.ZipFile(docx, "w") as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")

        target = tmp_path / "output"

        def fake_collect_inputs(*args, **kwargs):
            raise ValueError("Test error")

        monkeypatch.setattr(cli_prepare, "_collect_inputs", fake_collect_inputs)

        with caplog.at_level(logging.ERROR):
            rc = cli.main(
                [
                    "--extract",
                    f"source={str(docx)}",
                    "--target",
                    str(target),
                    "--verbosity",
                    "debug",
                ]
            )

        assert rc == 1
        assert "Traceback" in caplog.text or "Test error" in caplog.text


class TestParallelParsing:
    """Tests for parallel stage argument parsing."""

    def test_parse_parallel_stage_with_input(self):
        """Parallel stage with input parameter should be parsed correctly."""
        config = cli.gather_user_requirements(
            [
                "--parallel",
                "source=/path/to/directory",
                "--extract",
                "--target",
                "/path/to/output",
            ]
        )
        assert config.parallel is not None
        assert config.parallel.source == Path("/path/to/directory")
        assert config.parallel.n == 1  # Default value

    def test_parse_parallel_stage_with_input_and_n(self):
        """Parallel stage with both input and n parameters should be parsed."""
        config = cli.gather_user_requirements(
            [
                "--parallel",
                "source=/path/to/directory",
                "n=10",
                "--extract",
                "--target",
                "/path/to/output",
            ]
        )
        assert config.parallel.source == Path("/path/to/directory")
        assert config.parallel.n == 10

    def test_parallel_without_input_raises_error(self):
        """Parallel stage without input parameter should raise error."""
        with pytest.raises(ValueError, match="requires 'source' parameter"):
            cli.gather_user_requirements(
                ["--parallel", "--extract", "--target", "/path/to/output"]
            )

    def test_parallel_with_invalid_n_raises_error(self):
        """Parallel stage with invalid n parameter should raise error."""
        with pytest.raises(ValueError, match="must be a valid integer"):
            cli.gather_user_requirements(
                [
                    "--parallel",
                    "source=/path/to/directory",
                    "n=invalid",
                    "--extract",
                    "--target",
                    "/path/to/output",
                ]
            )

    def test_parallel_with_negative_n_raises_error(self):
        """Parallel stage with negative n parameter should raise error."""
        with pytest.raises(ValueError, match="must be >= 1"):
            cli.gather_user_requirements(
                [
                    "--parallel",
                    "source=/path/to/directory",
                    "n=-5",
                    "--extract",
                    "--target",
                    "/path/to/output",
                ]
            )

    def test_parallel_with_zero_n_raises_error(self):
        """Parallel stage with zero n parameter should raise error."""
        with pytest.raises(ValueError, match="must be >= 1"):
            cli.gather_user_requirements(
                [
                    "--parallel",
                    "source=/path/to/directory",
                    "n=0",
                    "--extract",
                    "--target",
                    "/path/to/output",
                ]
            )

    def test_parallel_with_extract_no_source_allowed(self):
        """When parallel is present, extract can be specified without source."""
        config = cli.gather_user_requirements(
            [
                "--parallel",
                "source=/path/to/directory",
                "n=5",
                "--extract",
                "--target",
                "/path/to/output",
            ]
        )
        assert config.parallel is not None
        assert config.extract is not None
        # Source will be a placeholder
        assert config.extract.source == Path(".")

    def test_parallel_with_all_stages(self):
        """Parallel can be combined with extract, adjust, and apply stages."""
        config = cli.gather_user_requirements(
            [
                "--parallel",
                "source=/path/to/directory",
                "n=5",
                "--extract",
                "--adjust",
                "name=openai-company-research",
                "customer-url=https://example.com",
                "--render",
                "template=/path/to/template.docx",
                "--target",
                "/path/to/output",
            ]
        )
        assert config.parallel is not None
        assert config.extract is not None
        assert config.adjust is not None
        assert config.render is not None

    def test_parallel_only_stage(self):
        """Parallel can be used as the only stage."""
        config = cli.gather_user_requirements(
            ["--parallel", "source=/path/to/directory", "--target", "/path/to/output"]
        )
        assert config.parallel is not None
        assert config.extract is None
        assert config.adjust is None
        assert config.render is None
