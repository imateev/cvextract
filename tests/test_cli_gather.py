"""Tests for CLI gather (phase 1) functionality."""

from pathlib import Path

import pytest

from cvextract import cli_gather


class TestHandleListCommand:
    """Tests for _handle_list_command function."""

    def test_list_adjusters(self, capsys):
        """--list adjusters should print available adjusters."""
        cli_gather._handle_list_command("adjusters")
        captured = capsys.readouterr()

        assert "Available Adjusters" in captured.out
        assert "openai-company-research" in captured.out
        assert "openai-job-specific" in captured.out
        assert "openai-translate" in captured.out

    def test_list_renderers(self, capsys):
        """--list renderers should print available renderers."""
        cli_gather._handle_list_command("renderers")
        captured = capsys.readouterr()

        assert "Available Renderers" in captured.out
        assert "docx" in captured.out

    def test_list_extractors(self, capsys):
        """--list extractors should print available extractors."""
        cli_gather._handle_list_command("extractors")
        captured = capsys.readouterr()

        assert "Available Extractors" in captured.out
        assert "docx" in captured.out


class TestResolveOutputPath:
    """Tests for _resolve_output_path function."""

    def test_resolve_absolute_path(self):
        """Absolute paths should be returned as-is."""
        result = cli_gather._resolve_output_path("/abs/path.json", Path("/target"))
        assert result == Path("/abs/path.json")

    def test_resolve_relative_path(self):
        """Relative paths should be resolved relative to target."""
        result = cli_gather._resolve_output_path("data.json", Path("/target"))
        assert result == Path("/target/data.json")

    def test_resolve_nested_relative_path(self):
        """Nested relative paths should be resolved correctly."""
        result = cli_gather._resolve_output_path("subdir/data.json", Path("/target"))
        assert result == Path("/target/subdir/data.json")


class TestParseStageParams:
    """Tests for _parse_stage_params function."""

    def test_parse_simple_params(self):
        """Parse simple key=value parameters."""
        params = cli_gather._parse_stage_params(["source=cv.docx", "output=data.json"])
        assert params == {"source": "cv.docx", "output": "data.json"}

    def test_parse_params_with_spaces_in_value(self):
        """Parameters can have spaces in values."""
        params = cli_gather._parse_stage_params(["source=/path with spaces/file.docx"])
        assert params == {"source": "/path with spaces/file.docx"}

    def test_parse_flags(self):
        """Flags without values are stored with empty string."""
        params = cli_gather._parse_stage_params(["skip-verify"])
        assert params == {"skip-verify": ""}

    def test_parse_mixed_params_and_flags(self):
        """Mix of parameters and flags."""
        params = cli_gather._parse_stage_params(
            ["source=cv.docx", "skip-verify", "output=data.json"]
        )
        assert params == {"source": "cv.docx", "skip-verify": "", "output": "data.json"}

    def test_parse_empty_list(self):
        """Empty parameter list returns empty dict."""
        params = cli_gather._parse_stage_params([])
        assert params == {}

    def test_parse_empty_string_skipped(self):
        """Empty strings are skipped."""
        params = cli_gather._parse_stage_params(["", "source=cv.docx", ""])
        assert params == {"source": "cv.docx"}

    def test_parse_empty_key_raises_error(self):
        """Empty keys raise ValueError."""
        with pytest.raises(ValueError, match="Empty parameter key"):
            cli_gather._parse_stage_params(["=value"])

    def test_parse_params_with_equals_in_value(self):
        """Parameters can contain equals signs in values."""
        params = cli_gather._parse_stage_params(["data=key=value"])
        assert params == {"data": "key=value"}


class TestGatherUserRequirements:
    """Tests for gather_user_requirements function."""

    def test_missing_target_raises_error(self):
        """--target is required when not using --list."""
        with pytest.raises(ValueError, match="--target is required"):
            cli_gather.gather_user_requirements(["--extract", "source=cv.docx"])

    def test_no_stages_raises_error(self):
        """Must specify at least one stage."""
        with pytest.raises(ValueError, match="Must specify at least one stage"):
            cli_gather.gather_user_requirements(["--target", "/output"])

    def test_extract_without_source_raises_error(self):
        """--extract requires 'source' parameter when not using --parallel."""
        with pytest.raises(ValueError, match="--extract requires 'source'"):
            cli_gather.gather_user_requirements(["--extract", "--target", "/output"])

    def test_extract_with_source(self):
        """--extract with source parameter creates ExtractStage."""
        config = cli_gather.gather_user_requirements(
            ["--extract", "source=cv.docx", "--target", "/output"]
        )

        assert config.extract is not None
        assert config.extract.source == Path("cv.docx")
        assert config.target_dir == Path("/output")

    def test_extract_with_output_parameter(self):
        """--extract output parameter is resolved relative to target."""
        config = cli_gather.gather_user_requirements(
            ["--extract", "source=cv.docx", "output=data.json", "--target", "/output"]
        )

        assert config.extract.output == Path("/output/data.json")

    def test_extract_with_verifier_and_skip_verify(self):
        """--extract verifier and skip-verify parameters are stored."""
        config = cli_gather.gather_user_requirements(
            [
                "--extract",
                "source=cv.docx",
                "verifier=custom-verifier",
                "skip-verify",
                "--target",
                "/output",
            ]
        )

        assert config.extract.verifier == "custom-verifier"
        assert config.extract.skip_verify is True

    def test_adjust_requires_name(self):
        """--adjust requires 'name' parameter."""
        with pytest.raises(ValueError, match="requires 'name' parameter"):
            cli_gather.gather_user_requirements(
                [
                    "--extract",
                    "source=cv.docx",
                    "--adjust",
                    "customer-url=https://example.com",
                    "--target",
                    "/output",
                ]
            )

    def test_adjust_with_name(self):
        """--adjust with name creates AdjustStage."""
        config = cli_gather.gather_user_requirements(
            [
                "--extract",
                "source=cv.docx",
                "--adjust",
                "name=openai-company-research",
                "customer-url=https://example.com",
                "--target",
                "/output",
            ]
        )

        assert config.adjust is not None
        assert len(config.adjust.adjusters) == 1
        assert config.adjust.adjusters[0].name == "openai-company-research"
        assert config.adjust.adjusters[0].params == {
            "customer-url": "https://example.com"
        }

    def test_adjust_with_openai_model(self):
        """--adjust openai-model parameter is stored."""
        config = cli_gather.gather_user_requirements(
            [
                "--extract",
                "source=cv.docx",
                "--adjust",
                "name=openai-company-research",
                "customer-url=https://example.com",
                "openai-model=gpt-4",
                "--target",
                "/output",
            ]
        )

        assert config.adjust.adjusters[0].openai_model == "gpt-4"

    def test_multiple_adjust_stages(self):
        """Multiple --adjust flags create multiple adjusters."""
        config = cli_gather.gather_user_requirements(
            [
                "--extract",
                "source=cv.docx",
                "--adjust",
                "name=openai-company-research",
                "customer-url=https://example.com",
                "--adjust",
                "name=openai-job-specific",
                "job-url=https://example.com/job/123",
                "--target",
                "/output",
            ]
        )

        assert config.adjust is not None
        assert len(config.adjust.adjusters) == 2
        assert config.adjust.adjusters[0].name == "openai-company-research"
        assert config.adjust.adjusters[1].name == "openai-job-specific"

    def test_adjust_with_data_parameter(self):
        """--adjust data parameter is stored."""
        config = cli_gather.gather_user_requirements(
            [
                "--extract",
                "source=cv.docx",
                "--adjust",
                "name=openai-company-research",
                "customer-url=https://example.com",
                "data=existing.json",
                "--target",
                "/output",
            ]
        )

        assert config.adjust.data == Path("existing.json")

    def test_adjust_with_verifier_and_skip_verify(self):
        """--adjust verifier and skip-verify parameters are stored."""
        config = cli_gather.gather_user_requirements(
            [
                "--extract",
                "source=cv.docx",
                "--adjust",
                "name=openai-company-research",
                "customer-url=https://example.com",
                "verifier=cv-schema-verifier",
                "skip-verify",
                "--target",
                "/output",
            ]
        )

        assert config.adjust.verifier == "cv-schema-verifier"
        assert config.adjust.skip_verify is True

    def test_apply_requires_template(self):
        """--render requires 'template' parameter."""
        with pytest.raises(ValueError, match="--render requires 'template'"):
            cli_gather.gather_user_requirements(["--render", "--target", "/output"])

    def test_apply_with_template(self):
        """--render with template creates RenderStage."""
        config = cli_gather.gather_user_requirements(
            ["--render", "template=template.docx", "--target", "/output"]
        )

        assert config.render is not None
        assert config.render.template == Path("template.docx")

    def test_apply_with_data(self):
        """--render data parameter is stored."""
        config = cli_gather.gather_user_requirements(
            [
                "--render",
                "template=template.docx",
                "data=extracted.json",
                "--target",
                "/output",
            ]
        )

        assert config.render.data == Path("extracted.json")

    def test_render_with_verifier_and_skip_verify(self):
        """--render verifier and skip-verify parameters are stored."""
        config = cli_gather.gather_user_requirements(
            [
                "--render",
                "template=template.docx",
                "verifier=roundtrip-verifier",
                "skip-verify",
                "--target",
                "/output",
            ]
        )

        assert config.render.verifier == "roundtrip-verifier"
        assert config.render.skip_verify is True

    def test_parallel_requires_source(self):
        """--parallel requires 'source' parameter."""
        with pytest.raises(ValueError, match="--parallel requires 'source'"):
            cli_gather.gather_user_requirements(
                ["--parallel", "n=4", "--target", "/output"]
            )

    def test_parallel_without_source_allowed_for_rerun_failed(self):
        """--parallel allows missing source when rerun-failed is set."""
        config = cli_gather.gather_user_requirements(
            [
                "--parallel",
                "n=4",
                "--rerun-failed",
                "/tmp/failed.txt",
                "--target",
                "/output",
                "--extract",
                "source=/path/to/file.docx",
            ]
        )

        assert config.parallel is not None
        assert config.rerun_failed == Path("/tmp/failed.txt")
        assert config.parallel.source == Path(".")

    def test_rerun_failed_allows_extract_without_source(self):
        """--rerun-failed allows --extract without source."""
        config = cli_gather.gather_user_requirements(
            [
                "--rerun-failed",
                "/tmp/failed.txt",
                "--extract",
                "name=default-docx-cv-extractor",
                "--target",
                "/output",
            ]
        )

        assert config.rerun_failed == Path("/tmp/failed.txt")
        assert config.extract is not None
        assert config.extract.source == Path(".")

    def test_parallel_with_source(self):
        """--parallel with source creates ParallelStage."""
        config = cli_gather.gather_user_requirements(
            ["--parallel", "source=/path/to/cvs", "--target", "/output"]
        )

        assert config.parallel is not None
        assert config.parallel.source == Path("/path/to/cvs")
        assert config.parallel.n == 1  # Default

    def test_parallel_with_n_workers(self):
        """--parallel n parameter sets number of workers."""
        config = cli_gather.gather_user_requirements(
            ["--parallel", "source=/path/to/cvs", "n=4", "--target", "/output"]
        )

        assert config.parallel.n == 4

    def test_parallel_n_must_be_positive(self):
        """--parallel n parameter must be >= 1."""
        with pytest.raises(ValueError, match="must be >= 1"):
            cli_gather.gather_user_requirements(
                ["--parallel", "source=/path/to/cvs", "n=0", "--target", "/output"]
            )

    def test_parallel_n_must_be_integer(self):
        """--parallel n parameter must be valid integer."""
        with pytest.raises(ValueError, match="must be a valid integer"):
            cli_gather.gather_user_requirements(
                ["--parallel", "source=/path/to/cvs", "n=abc", "--target", "/output"]
            )

    def test_extract_with_parallel_no_source_required(self):
        """--extract source is optional when using --parallel."""
        config = cli_gather.gather_user_requirements(
            ["--parallel", "source=/path/to/cvs", "--extract", "--target", "/output"]
        )

        assert config.extract is not None
        assert config.parallel is not None

    def test_debug_flag(self):
        """--verbosity debug enables debug mode."""
        config = cli_gather.gather_user_requirements(
            [
                "--extract",
                "source=cv.docx",
                "--target",
                "/output",
                "--verbosity",
                "debug",
            ]
        )
        assert config.debug is True

    def test_log_file_parameter(self):
        """--log-file parameter is stored."""
        config = cli_gather.gather_user_requirements(
            [
                "--extract",
                "source=cv.docx",
                "--target",
                "/output",
                "--log-file",
                "/tmp/app.log",
            ]
        )

        assert config.log_file == "/tmp/app.log"

    def test_global_skip_all_verify(self):
        """--skip-all-verify is stored on the user config."""
        config = cli_gather.gather_user_requirements(
            [
                "--extract",
                "source=cv.docx",
                "--target",
                "/output",
                "--skip-all-verify",
            ]
        )

        assert config.skip_all_verify is True

    def test_full_pipeline(self):
        """Full pipeline with extract, adjust, and apply."""
        config = cli_gather.gather_user_requirements(
            [
                "--extract",
                "source=cv.docx",
                "--adjust",
                "name=openai-company-research",
                "customer-url=https://example.com",
                "--render",
                "template=template.docx",
                "--target",
                "/output",
                "--verbosity",
                "debug",
            ]
        )
        assert config.extract is not None
        assert config.adjust is not None
        assert config.render is not None
        assert config.target_dir == Path("/output")
        assert config.debug is True

    def test_adjust_output_parameter(self):
        """--adjust output parameter is resolved relative to target."""
        config = cli_gather.gather_user_requirements(
            [
                "--extract",
                "source=cv.docx",
                "--adjust",
                "name=openai-company-research",
                "customer-url=https://example.com",
                "output=adjusted.json",
                "--target",
                "/output",
            ]
        )

        assert config.adjust.output == Path("/output/adjusted.json")

    def test_adjust_empty_configs_error(self):
        """--adjust without any configurable adjusters raises error."""
        # This tests the edge case where adjust is specified but no configs are created
        # This is hard to trigger naturally, but we can test related logic
        with pytest.raises(ValueError, match="--adjust requires 'name'"):
            cli_gather.gather_user_requirements(
                [
                    "--extract",
                    "source=cv.docx",
                    "--adjust",  # No parameters
                    "--target",
                    "/output",
                ]
            )

    def test_parallel_with_file_type(self):
        """Test parallel with file-type parameter."""
        config = cli_gather.gather_user_requirements(
            [
                "--parallel",
                "source=/input",
                "n=5",
                "file-type=*.txt",
                "--extract",
                "--target",
                "/output",
            ]
        )

        assert config.parallel is not None
        assert config.parallel.source == Path("/input")
        assert config.parallel.n == 5
        assert config.parallel.file_type == "*.txt"
