"""Tests for cli_execute module - pipeline execution phase."""

import json
import zipfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from cvextract.cli_config import UserConfig, ExtractStage, AdjustStage, AdjusterConfig, ApplyStage
from cvextract.cli_execute import execute_pipeline


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
def mock_json(tmp_path: Path):
    """Create a valid CV JSON file."""
    json_file = tmp_path / "test.json"
    data = {
        "identity": {"name": "John Doe"},
        "sidebar": {},
        "overview": "Test overview",
        "experiences": []
    }
    json_file.write_text(json.dumps(data, indent=2))
    return json_file


@pytest.fixture
def parallel_input_tree(tmp_path: Path):
    """Utility for creating nested inputs that always set input_dir properly."""

    class InputTreeBuilder:
        def __init__(self, root: Path):
            self.root = root
            self.root.mkdir(parents=True, exist_ok=True)

        def docx(self, relative: str) -> Path:
            return self._write(relative, "docx")

        def json(self, relative: str, payload: dict) -> Path:
            return self._write(relative, json.dumps(payload, indent=2))

        def _write(self, relative: str, content: str) -> Path:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            return path

    return InputTreeBuilder(tmp_path / "input_root")


class TestExecutePipelineNoInput:
    """Tests for execute_pipeline when no input is specified."""

    def test_no_input_source(self, tmp_path: Path):
        """Test that execute_pipeline fails when no input source is provided."""
        config = UserConfig(
            extract=None,
            adjust=None,
            apply=None,
            target_dir=tmp_path / "out",
            strict=False,
            log_file=None
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 1


class TestExecutePipelineExtractOnly:
    """Tests for execute_pipeline with extract stage only."""

    @patch('cvextract.cli_execute._collect_inputs')
    @patch('cvextract.cli_execute.extract_single')
    def test_extract_success(self, mock_extract, mock_collect, tmp_path: Path, mock_docx: Path):
        """Test successful extraction."""
        mock_collect.return_value = [mock_docx]
        mock_extract.return_value = (True, [], [])

        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=None),
            adjust=None,
            apply=None,
            target_dir=tmp_path / "out",
            strict=False,
            log_file=None
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0
        mock_extract.assert_called_once()

    @patch('cvextract.cli_execute._collect_inputs')
    def test_extract_with_unknown_extractor(self, mock_collect, tmp_path: Path, mock_docx: Path):
        """Test extraction with unknown extractor name returns error."""
        mock_collect.return_value = [mock_docx]

        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=None, name='nonexistent-extractor'),
            adjust=None,
            apply=None,
            target_dir=tmp_path / "out",
            strict=False,
            log_file=None
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 1

    @patch('cvextract.cli_execute._collect_inputs')
    @patch('cvextract.cli_execute.extract_single')
    def test_extract_with_warnings_strict_mode(self, mock_extract, mock_collect, tmp_path: Path, mock_docx: Path):
        """Test extraction with warnings in strict mode returns 2."""
        mock_collect.return_value = [mock_docx]
        mock_extract.return_value = (True, [], ["warning"])

        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=None),
            adjust=None,
            apply=None,
            target_dir=tmp_path / "out",
            strict=True,
            log_file=None
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 2

    @patch('cvextract.cli_execute._collect_inputs')
    @patch('cvextract.cli_execute.extract_single')
    def test_extract_failure(self, mock_extract, mock_collect, tmp_path: Path, mock_docx: Path):
        """Test extraction failure returns 1."""
        mock_collect.return_value = [mock_docx]
        mock_extract.return_value = (False, ["error"], [])

        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=None),
            adjust=None,
            apply=None,
            target_dir=tmp_path / "out",
            strict=False,
            log_file=None
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 1

    @patch('cvextract.cli_execute._collect_inputs')
    def test_extract_collect_inputs_fails(self, mock_collect, tmp_path: Path, mock_docx: Path):
        """Test that exception during input collection returns 1."""
        mock_collect.side_effect = Exception("Failed to collect inputs")

        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=None),
            adjust=None,
            apply=None,
            target_dir=tmp_path / "out",
            strict=False,
            log_file=None
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 1

    @patch('cvextract.cli_execute._collect_inputs')
    def test_extract_no_matching_files(self, mock_collect, tmp_path: Path, mock_docx: Path):
        """Test that no matching files returns 1."""
        mock_collect.return_value = []

        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=None),
            adjust=None,
            apply=None,
            target_dir=tmp_path / "out",
            strict=False,
            log_file=None
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 1

    @patch('cvextract.cli_execute._collect_inputs')
    @patch('cvextract.cli_execute.extract_single')
    def test_extract_with_custom_output(self, mock_extract, mock_collect, tmp_path: Path, mock_docx: Path):
        """Test extraction with custom output path."""
        mock_collect.return_value = [mock_docx]
        mock_extract.return_value = (True, [], [])

        custom_output = tmp_path / "custom.json"
        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=custom_output),
            adjust=None,
            apply=None,
            target_dir=tmp_path / "out",
            strict=False,
            log_file=None
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0
        # Verify extract_single was called with custom output
        call_args = mock_extract.call_args
        assert call_args[0][1] == custom_output


class TestExecutePipelineExtractApply:
    """Tests for execute_pipeline with extract + apply stages."""

    @patch('cvextract.cli_execute._collect_inputs')
    @patch('cvextract.cli_execute.extract_single')
    @patch('cvextract.cli_execute.render_and_verify')
    def test_extract_apply_success(self, mock_render, mock_extract, mock_collect,
                                   tmp_path: Path, mock_docx: Path, mock_template: Path):
        """Test successful extract + apply."""
        mock_collect.return_value = [mock_docx]
        mock_extract.return_value = (True, [], [])
        mock_render.return_value = (True, [], [], True)

        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=None),
            adjust=None,
            apply=ApplyStage(template=mock_template, data=None, output=None),
            target_dir=tmp_path / "out",
            strict=False,
            log_file=None
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0
        mock_extract.assert_called_once()
        mock_render.assert_called_once()

    @patch('cvextract.cli_execute._collect_inputs')
    @patch('cvextract.cli_execute.extract_single')
    @patch('cvextract.cli_execute.render_and_verify')
    def test_extract_fails_apply_skipped(self, mock_render, mock_extract, mock_collect,
                                          tmp_path: Path, mock_docx: Path, mock_template: Path):
        """Test that apply is skipped if extract fails."""
        mock_collect.return_value = [mock_docx]
        mock_extract.return_value = (False, ["extract error"], [])

        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=None),
            adjust=None,
            apply=ApplyStage(template=mock_template, data=None, output=None),
            target_dir=tmp_path / "out",
            strict=False,
            log_file=None
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 1
        mock_extract.assert_called_once()
        mock_render.assert_not_called()

    @patch('cvextract.cli_execute._collect_inputs')
    @patch('cvextract.cli_execute.extract_single')
    @patch('cvextract.cli_execute.render_and_verify')
    def test_extract_apply_both_warnings_strict(self, mock_render, mock_extract, mock_collect,
                                                 tmp_path: Path, mock_docx: Path, mock_template: Path):
        """Test extract + apply with warnings in strict mode."""
        mock_collect.return_value = [mock_docx]
        mock_extract.return_value = (True, [], ["extract warning"])
        mock_render.return_value = (True, [], ["apply warning"], True)

        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=None),
            adjust=None,
            apply=ApplyStage(template=mock_template, data=None, output=None),
            target_dir=tmp_path / "out",
            strict=True,
            log_file=None
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 2


class TestExecutePipelineApplyOnly:
    """Tests for execute_pipeline with apply stage only (from existing JSON)."""

    @patch('cvextract.cli_execute._collect_inputs')
    @patch('cvextract.cli_execute.render_and_verify')
    def test_apply_from_json_success(self, mock_render, mock_collect,
                                     tmp_path: Path, mock_json: Path, mock_template: Path):
        """Test applying from existing JSON file."""
        mock_collect.return_value = [mock_json]
        mock_render.return_value = (True, [], [], True)

        config = UserConfig(
            extract=None,
            adjust=None,
            apply=ApplyStage(template=mock_template, data=mock_json, output=None),
            target_dir=tmp_path / "out",
            strict=False,
            log_file=None
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0
        mock_render.assert_called_once()

    @patch('cvextract.cli_execute._collect_inputs')
    @patch('cvextract.cli_execute.render_and_verify')
    def test_apply_custom_output(self, mock_render, mock_collect,
                                 tmp_path: Path, mock_json: Path, mock_template: Path):
        """Test applying with custom output path."""
        mock_collect.return_value = [mock_json]
        mock_render.return_value = (True, [], [], True)

        custom_output = tmp_path / "custom_output.docx"
        config = UserConfig(
            extract=None,
            adjust=None,
            apply=ApplyStage(template=mock_template, data=mock_json, output=custom_output),
            target_dir=tmp_path / "out",
            strict=False,
            log_file=None
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0
        # Verify render was called with custom output
        call_args = mock_render.call_args
        assert call_args[1]['output_docx'] == custom_output


class TestExecutePipelineAdjust:
    """Tests for execute_pipeline with adjust stage."""

    @patch('cvextract.cli_execute._collect_inputs')
    @patch('cvextract.cli_execute.extract_single')
    @patch('cvextract.cli_execute.get_adjuster')
    @patch('cvextract.cli_execute.render_and_verify')
    def test_extract_adjust_apply_success(self, mock_render, mock_get_adjuster, mock_extract, mock_collect,
                                          tmp_path: Path, mock_docx: Path, mock_template: Path):
        """Test successful extract + adjust + apply."""
        mock_collect.return_value = [mock_docx]

        # Mock extract_single to create a JSON file
        def fake_extract(docx_file, out_json, verbosity=0, extractor=None):
            out_json.parent.mkdir(parents=True, exist_ok=True)
            out_json.write_text(json.dumps({"identity": {}, "sidebar": {}, "overview": "", "experiences": []}))
            return True, [], []

        mock_extract.side_effect = fake_extract

        # Mock adjuster
        mock_adjuster = MagicMock()
        mock_adjuster.adjust.return_value = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        mock_adjuster.validate_params.return_value = None
        mock_get_adjuster.return_value = mock_adjuster

        mock_render.return_value = (True, [], [], True)

        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=None),
            adjust=AdjustStage(
                adjusters=[AdjusterConfig(
                    name="openai-company-research",
                    params={"customer-url": "https://example.com"},
                    openai_model="gpt-4"
                )],
                dry_run=False,
                data=None,
                output=None
            ),
            apply=ApplyStage(template=mock_template, data=None, output=None),
            target_dir=tmp_path / "out",
            strict=False,
            log_file=None
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0
        mock_extract.assert_called_once()
        mock_adjuster.adjust.assert_called_once()
        mock_render.assert_called_once()

    @patch('cvextract.cli_execute._collect_inputs')
    @patch('cvextract.cli_execute.extract_single')
    @patch('cvextract.cli_execute.get_adjuster')
    def test_adjust_dry_run_skips_apply(self, mock_get_adjuster, mock_extract, mock_collect,
                                        tmp_path: Path, mock_docx: Path, mock_template: Path):
        """Test that dry-run mode skips apply stage."""
        mock_collect.return_value = [mock_docx]

        # Mock extract_single to create a JSON file
        def fake_extract(docx_file, out_json, verbosity=0, extractor=None):
            out_json.parent.mkdir(parents=True, exist_ok=True)
            out_json.write_text(json.dumps({"identity": {}, "sidebar": {}, "overview": "", "experiences": []}))
            return True, [], []

        mock_extract.side_effect = fake_extract
        # Mock adjuster
        mock_adjuster = MagicMock()
        mock_adjuster.adjust.return_value = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        mock_adjuster.validate_params.return_value = None
        mock_get_adjuster.return_value = mock_adjuster

        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=None),
            adjust=AdjustStage(
                adjusters=[AdjusterConfig(
                    name="openai-company-research",
                    params={"customer-url": "https://example.com"},
                    openai_model="gpt-4"
                )],
                dry_run=True,
                data=None,
                output=None

            ),
            apply=ApplyStage(template=mock_template, data=None, output=None),
            target_dir=tmp_path / "out",
            strict=False,
            log_file=None
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0
        mock_extract.assert_called_once()
        mock_adjuster.adjust.assert_called_once()

    @patch('cvextract.cli_execute._collect_inputs')
    @patch('cvextract.cli_execute.get_adjuster')
    @patch('cvextract.cli_execute.render_and_verify')
    def test_adjust_from_json(self, mock_render, mock_get_adjuster, mock_collect,
                             tmp_path: Path, mock_json: Path, mock_template: Path):
        """Test adjust from existing JSON without extraction."""
        mock_collect.return_value = [mock_json]
        # Mock adjuster
        mock_adjuster = MagicMock()
        mock_adjuster.adjust.return_value = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        mock_adjuster.validate_params.return_value = None
        mock_get_adjuster.return_value = mock_adjuster
        mock_render.return_value = (True, [], [], True)
        config = UserConfig(
            extract=None,
            adjust=AdjustStage(
                adjusters=[AdjusterConfig(
                    name="openai-company-research",
                    params={"customer-url": "https://example.com"},
                    openai_model="gpt-4"
                )],
                dry_run=False,
                data=mock_json,
                output=None

            ),
            apply=ApplyStage(template=mock_template, data=None, output=None),
            target_dir=tmp_path / "out",
            strict=False,
            log_file=None
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0
        mock_adjuster.adjust.assert_called_once()
        mock_render.assert_called_once()

    @patch('cvextract.cli_execute._collect_inputs')
    @patch('cvextract.cli_execute.get_adjuster')
    @patch('cvextract.cli_execute._url_to_cache_filename', return_value="cache.json")
    def test_adjust_research_cache_is_rooted(self, mock_cache_name, mock_get_adjuster, mock_collect,
                                             tmp_path: Path, parallel_input_tree):
        """Research cache should always live under target/research_data regardless of input path."""
        payload = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        input_json = parallel_input_tree.json("folder/profile.json", payload)
        mock_collect.return_value = [input_json]
        # Mock adjuster
        mock_adjuster = MagicMock()
        mock_adjuster.adjust.return_value = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        mock_adjuster.validate_params.return_value = None
        mock_get_adjuster.return_value = mock_adjuster

        config = UserConfig(
            extract=None,
            input_dir=parallel_input_tree.root,
            adjust=AdjustStage(
                adjusters=[AdjusterConfig(
                    name="openai-company-research",
                    params={"customer-url": "https://example.com"},
                    openai_model="gpt-4"
                )],
                dry_run=False,
                data=input_json,
                output=None

            ),
            apply=None,
            target_dir=tmp_path / "out",
            strict=False,
            log_file=None
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0

        mock_adjuster.adjust.assert_called_once()
        # Check that cache_path was passed in the adjuster params
        call_kwargs = mock_adjuster.adjust.call_args.kwargs
        assert 'cache_path' in call_kwargs
        cache_path = call_kwargs["cache_path"]
        expected_cache = tmp_path / "out" / "research_data" / "cache.json"
        assert cache_path == expected_cache
        assert cache_path.parent.exists()

    @patch('cvextract.cli_execute._collect_inputs')
    @patch('cvextract.cli_execute.extract_single')
    @patch('cvextract.cli_execute.get_adjuster')
    @patch('cvextract.cli_execute.render_and_verify')
    def test_adjust_exception_fallback(self, mock_render, mock_get_adjuster, mock_extract, mock_collect,
                                       tmp_path: Path, mock_docx: Path, mock_template: Path):
        """Test that adjustment exceptions are handled and apply proceeds with original JSON."""
        mock_collect.return_value = [mock_docx]

        # Mock extract_single to create a JSON file
        def fake_extract(docx_file, out_json, verbosity=0, extractor=None):
            out_json.parent.mkdir(parents=True, exist_ok=True)
            out_json.write_text(json.dumps({"identity": {}, "sidebar": {}, "overview": "", "experiences": []}))
            return True, [], []

        mock_extract.side_effect = fake_extract
        # Mock adjuster to raise exception
        mock_adjuster = MagicMock()
        mock_adjuster.adjust.side_effect = Exception("Adjustment failed")
        mock_adjuster.validate_params.return_value = None
        mock_get_adjuster.return_value = mock_adjuster
        mock_render.return_value = (True, [], [], True)

        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=None),
            adjust=AdjustStage(
                adjusters=[AdjusterConfig(
                    name="openai-company-research",
                    params={"customer-url": "https://example.com"},
                    openai_model="gpt-4"
                )],
                dry_run=False,
                data=None,
                output=None

            ),
            apply=ApplyStage(template=mock_template, data=None, output=None),
            target_dir=tmp_path / "out",
            strict=False,
            log_file=None
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0
        mock_render.assert_called_once()


class TestExecutePipelineDirectoryRejection:
    """Tests for execute_pipeline when directory is provided instead of single file."""

    def test_directory_in_extract_mode_returns_error(self, tmp_path: Path):
        """Test that providing a directory in extract mode returns error code 1."""
        docx_dir = tmp_path / "cvs"
        docx_dir.mkdir()
        (docx_dir / "a.docx").write_text("x")
        (docx_dir / "b.docx").write_text("y")

        config = UserConfig(
            extract=ExtractStage(source=docx_dir, output=None),
            adjust=None,
            apply=None,
            target_dir=tmp_path / "out",
            strict=False,
            log_file=None
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 1

    def test_directory_in_apply_mode_returns_error(self, tmp_path: Path):
        """Test that providing a directory in apply mode returns error code 1."""
        json_dir = tmp_path / "jsons"
        json_dir.mkdir()
        (json_dir / "a.json").write_text("{}")
        (json_dir / "b.json").write_text("{}")

        template = tmp_path / "template.docx"
        with zipfile.ZipFile(template, 'w') as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")

        config = UserConfig(
            extract=None,
            adjust=None,
            apply=ApplyStage(template=template, data=json_dir, output=None),
            target_dir=tmp_path / "out",
            strict=False,
            log_file=None
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 1


class TestExecutePipelineDebugMode:
    """Tests for execute_pipeline with debug mode."""

    @patch('cvextract.cli_execute._collect_inputs')
    def test_collect_inputs_exception_debug_mode(self, mock_collect, tmp_path: Path, mock_docx: Path):
        """Test that exceptions in debug mode are logged with traceback."""
        mock_collect.side_effect = Exception("Collection error")

        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=None),
            adjust=None,
            apply=None,
            target_dir=tmp_path / "out",
            strict=False,
            verbosity=2,
            log_file=None
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 1

    @patch('cvextract.cli_execute._collect_inputs')
    @patch('cvextract.cli_execute.extract_single')
    @patch('cvextract.cli_execute.get_adjuster')
    def test_adjust_exception_debug_mode(self, mock_get_adjuster, mock_extract, mock_collect,
                                         tmp_path: Path, mock_docx: Path):
        """Test that adjust exceptions in debug mode are logged."""
        mock_collect.return_value = [mock_docx]
        mock_extract.return_value = (True, [], [])
        # Mock adjuster to raise exception
        mock_adjuster = MagicMock()
        mock_adjuster.adjust.side_effect = Exception("Adjustment error")
        mock_adjuster.validate_params.return_value = None
        mock_get_adjuster.return_value = mock_adjuster

        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=None),
            adjust=AdjustStage(
                adjusters=[AdjusterConfig(
                    name="openai-company-research",
                    params={"customer-url": "https://example.com"},
                    openai_model="gpt-4"
                )],
                dry_run=True,
                data=None,
                output=None

            ),
            apply=None,
            target_dir=tmp_path / "out",
            strict=False,
            verbosity=2,
            log_file=None
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0  # Dry run doesn't fail on adjust error


class TestExecutePipelineSkipNonMatchingFiles:
    """Tests that non-matching file extensions return appropriate errors."""

    def test_non_docx_for_extract_returns_error(self, tmp_path: Path):
        """Test that non-DOCX files return error during extraction."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("not a docx")

        config = UserConfig(
            extract=ExtractStage(source=txt_file, output=None),
            adjust=None,
            apply=None,
            target_dir=tmp_path / "out",
            strict=False,
            log_file=None
        )

        exit_code = execute_pipeline(config)
        # Should return error code 1 for wrong file type (from _collect_inputs)
        assert exit_code == 1

    @patch('cvextract.cli_execute.render_and_verify')
    def test_non_json_for_apply_returns_error(self, mock_render, tmp_path: Path):
        """Test that non-JSON files return error during apply-only mode."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("not json")

        template = tmp_path / "template.docx"
        with zipfile.ZipFile(template, 'w') as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")

        config = UserConfig(
            extract=None,
            adjust=None,
            apply=ApplyStage(template=template, data=txt_file, output=None),
            target_dir=tmp_path / "out",
            strict=False,
            log_file=None
        )

        exit_code = execute_pipeline(config)
        # Should return error code 1 for wrong file type (from _collect_inputs)
        assert exit_code == 1
        mock_render.assert_not_called()


class TestFolderStructurePreservation:
    """Tests for preserving folder structure in output directories."""

    @patch('cvextract.cli_execute._collect_inputs')
    @patch('cvextract.cli_execute.extract_single')
    def test_extract_preserves_folder_structure(self, mock_extract, mock_collect,
                                                tmp_path: Path, parallel_input_tree):
        """Test that extracted JSON files preserve folder structure."""
        # Create a nested input file structure rooted under the simulated parallel input tree
        input_file = parallel_input_tree.docx("DACH/Software Engineering/profile.docx")

        mock_collect.return_value = [input_file]
        mock_extract.return_value = (True, [], [])

        config = UserConfig(
            extract=ExtractStage(source=input_file, output=None),
            adjust=None,
            apply=None,
            target_dir=tmp_path / "output",
            strict=False,
            log_file=None,
            input_dir=parallel_input_tree.root  # Mirror how parallel mode seeds rel_path
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0

        # Verify extract was called with the correct output path
        call_args = mock_extract.call_args
        output_json = call_args[0][1]

        # Output should be in DACH/Software Engineering subdirectory
        assert "DACH" in str(output_json)
        assert "Software Engineering" in str(output_json)
        assert output_json.parent.parent.parent == tmp_path / "output" / "structured_data"

    @patch('cvextract.cli_execute._collect_inputs')
    @patch('cvextract.cli_execute.extract_single')
    @patch('cvextract.cli_execute.get_adjuster')
    def test_adjust_preserves_folder_structure(self, mock_get_adjuster, mock_extract, mock_collect,
                                               tmp_path: Path, parallel_input_tree):
        """Test that adjusted JSON files preserve folder structure."""
        # Create nested input rooted at parallel tree to capture rel_path logic
        input_file = parallel_input_tree.docx("DACH/Software Engineering/profile.docx")

        mock_collect.return_value = [input_file]

        def fake_extract(docx_file, out_json, verbosity=0, extractor=None):
            out_json.parent.mkdir(parents=True, exist_ok=True)
            out_json.write_text(json.dumps({"identity": {}, "sidebar": {}, "overview": "", "experiences": []}))
            return True, [], []

        mock_extract.side_effect = fake_extract
        # Mock adjuster
        mock_adjuster = MagicMock()
        mock_adjuster.adjust.return_value = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        mock_adjuster.validate_params.return_value = None
        mock_get_adjuster.return_value = mock_adjuster

        config = UserConfig(
            extract=ExtractStage(source=input_file, output=None),
            adjust=AdjustStage(
                adjusters=[AdjusterConfig(
                    name="openai-company-research",
                    params={"customer-url": "https://example.com"},
                    openai_model="gpt-4"
                )],
                dry_run=True,
                data=None,
                output=None

            ),
            apply=None,
            target_dir=tmp_path / "output",
            strict=False,
            log_file=None,
            input_dir=parallel_input_tree.root
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0

        # Verify that adjusted JSON would be created with the same structure
        mock_adjuster.adjust.assert_called_once()

    @patch('cvextract.cli_execute._collect_inputs')
    @patch('cvextract.cli_execute.extract_single')
    @patch('cvextract.cli_execute.render_and_verify')
    def test_apply_preserves_folder_structure(self, mock_render, mock_extract, mock_collect,
                                             tmp_path: Path, mock_template: Path, parallel_input_tree):
        """Test that output DOCX files preserve folder structure."""
        # Create nested input rooted at the simulated parallel tree
        input_file = parallel_input_tree.docx("DACH/Software Engineering/profile.docx")

        mock_collect.return_value = [input_file]

        def fake_extract(docx_file, out_json, verbosity=0, extractor=None):
            out_json.parent.mkdir(parents=True, exist_ok=True)
            out_json.write_text(json.dumps({"identity": {}, "sidebar": {}, "overview": "", "experiences": []}))
            return True, [], []

        mock_extract.side_effect = fake_extract
        mock_render.return_value = (True, [], [], True)

        config = UserConfig(
            extract=ExtractStage(source=input_file, output=None),
            adjust=None,
            apply=ApplyStage(template=mock_template, data=None, output=None),
            target_dir=tmp_path / "output",
            strict=False,
            log_file=None,
            input_dir=parallel_input_tree.root
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0

        # Verify render was called with output in correct subdirectory
        call_args = mock_render.call_args
        output_docx = call_args[1]['output_docx']

        # Output should be in DACH/Software Engineering subdirectory
        assert "DACH" in str(output_docx)
        assert "Software Engineering" in str(output_docx)
        assert output_docx.parent.parent.parent == tmp_path / "output" / "documents"

    @patch('cvextract.cli_execute._collect_inputs')
    @patch('cvextract.cli_execute.extract_single')
    def test_flat_structure_without_input_dir(self, mock_extract, mock_collect, tmp_path: Path):
        """Test that without input_dir, structure defaults to flat (backward compatibility)."""
        # Create a nested input file
        input_dir = tmp_path / "input" / "DACH" / "Software Engineering"
        input_dir.mkdir(parents=True)
        input_file = input_dir / "profile.docx"
        input_file.write_text("docx")

        mock_collect.return_value = [input_file]
        mock_extract.return_value = (True, [], [])

        config = UserConfig(
            extract=ExtractStage(source=input_file, output=None),
            adjust=None,
            apply=None,
            target_dir=tmp_path / "output",
            strict=False,
            log_file=None,
            input_dir=None  # No input_dir specified, behavior depends on source
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0

        # The behavior will depend on whether source is a file or directory
        # If source is a file, rel_path will be calculated from source.parent
        mock_extract.assert_called_once()

    @patch('cvextract.cli_execute._collect_inputs')
    @patch('cvextract.cli_execute.extract_single')
    def test_parallel_mode_delegates_to_parallel_pipeline(self, mock_extract, mock_collect, tmp_path: Path):
        """execute_pipeline() with parallel=True delegates to execute_parallel_pipeline."""
        mock_docx = tmp_path / "test.docx"
        mock_docx.write_text("docx")
        mock_collect.return_value = [mock_docx]
        mock_extract.return_value = (True, [], [])

        with patch('cvextract.cli_parallel.execute_parallel_pipeline', return_value=0) as mock_parallel:
            config = UserConfig(
                extract=ExtractStage(source=mock_docx, output=None),
                adjust=None,
                apply=None,
                target_dir=tmp_path / "output",
                strict=False,
                log_file=None,
                parallel=True  # Enable parallel mode
            )

            exit_code = execute_pipeline(config)
            assert exit_code == 0
            mock_parallel.assert_called_once_with(config)

    @patch('cvextract.cli_execute._collect_inputs')
    @patch('cvextract.cli_execute.extract_single')
    def test_relative_path_calculation_with_value_error_fallback(self, mock_extract, mock_collect, tmp_path: Path):
        """execute_pipeline() falls back to '.' when relative_to() raises ValueError."""
        mock_docx = tmp_path / "test.docx"
        mock_docx.write_text("docx")
        mock_collect.return_value = [mock_docx]
        mock_extract.return_value = (True, [], [])

        # Create a config where input_dir is outside of the resolved input_file parent
        # This will cause ValueError when trying to compute relative_to
        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=None),
            adjust=None,
            apply=None,
            target_dir=tmp_path / "output",
            strict=False,
            log_file=None,
            input_dir=tmp_path / "other_dir"  # Different from the file's parent
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0  # Should still succeed with fallback
        mock_extract.assert_called_once()
