"""Tests for cli_execute module - pipeline execution phase."""

import json
import zipfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from cvextract.cli_config import UserConfig, ExtractStage, AdjustStage, ApplyStage
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
            debug=False,
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
            debug=False,
            log_file=None
        )
        
        exit_code = execute_pipeline(config)
        assert exit_code == 0
        mock_extract.assert_called_once()

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
            debug=False,
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
            debug=False,
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
            debug=False,
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
            debug=False,
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
            debug=False,
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
            debug=False,
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
            debug=False,
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
            debug=False,
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
            debug=False,
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
            debug=False,
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
    @patch('cvextract.cli_execute.adjust_for_customer')
    @patch('cvextract.cli_execute.render_and_verify')
    def test_extract_adjust_apply_success(self, mock_render, mock_adjust, mock_extract, mock_collect,
                                          tmp_path: Path, mock_docx: Path, mock_template: Path):
        """Test successful extract + adjust + apply."""
        mock_collect.return_value = [mock_docx]
        
        # Mock extract_single to create a JSON file
        def fake_extract(docx_file, out_json, debug):
            out_json.parent.mkdir(parents=True, exist_ok=True)
            out_json.write_text(json.dumps({"identity": {}, "sidebar": {}, "overview": "", "experiences": []}))
            return True, [], []
        
        mock_extract.side_effect = fake_extract
        mock_adjust.return_value = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        mock_render.return_value = (True, [], [], True)
        
        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=None),
            adjust=AdjustStage(
                customer_url="https://example.com",
                openai_model="gpt-4",
                dry_run=False,
                data=None,
                output=None
            ),
            apply=ApplyStage(template=mock_template, data=None, output=None),
            target_dir=tmp_path / "out",
            strict=False,
            debug=False,
            log_file=None
        )
        
        exit_code = execute_pipeline(config)
        assert exit_code == 0
        mock_extract.assert_called_once()
        mock_adjust.assert_called_once()
        mock_render.assert_called_once()

    @patch('cvextract.cli_execute._collect_inputs')
    @patch('cvextract.cli_execute.extract_single')
    @patch('cvextract.cli_execute.adjust_for_customer')
    def test_adjust_dry_run_skips_apply(self, mock_adjust, mock_extract, mock_collect,
                                        tmp_path: Path, mock_docx: Path, mock_template: Path):
        """Test that dry-run mode skips apply stage."""
        mock_collect.return_value = [mock_docx]
        
        # Mock extract_single to create a JSON file
        def fake_extract(docx_file, out_json, debug):
            out_json.parent.mkdir(parents=True, exist_ok=True)
            out_json.write_text(json.dumps({"identity": {}, "sidebar": {}, "overview": "", "experiences": []}))
            return True, [], []
        
        mock_extract.side_effect = fake_extract
        mock_adjust.return_value = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=None),
            adjust=AdjustStage(
                customer_url="https://example.com",
                openai_model="gpt-4",
                dry_run=True,
                data=None,
                output=None
            ),
            apply=ApplyStage(template=mock_template, data=None, output=None),
            target_dir=tmp_path / "out",
            strict=False,
            debug=False,
            log_file=None
        )
        
        exit_code = execute_pipeline(config)
        assert exit_code == 0
        mock_extract.assert_called_once()
        mock_adjust.assert_called_once()

    @patch('cvextract.cli_execute._collect_inputs')
    @patch('cvextract.cli_execute.adjust_for_customer')
    @patch('cvextract.cli_execute.render_and_verify')
    def test_adjust_from_json(self, mock_render, mock_adjust, mock_collect,
                             tmp_path: Path, mock_json: Path, mock_template: Path):
        """Test adjust from existing JSON without extraction."""
        mock_collect.return_value = [mock_json]
        mock_adjust.return_value = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        mock_render.return_value = (True, [], [], True)        
        config = UserConfig(
            extract=None,
            adjust=AdjustStage(
                customer_url="https://example.com",
                openai_model="gpt-4",
                dry_run=False,
                data=mock_json,
                output=None
            ),
            apply=ApplyStage(template=mock_template, data=None, output=None),
            target_dir=tmp_path / "out",
            strict=False,
            debug=False,
            log_file=None
        )
        
        exit_code = execute_pipeline(config)
        assert exit_code == 0
        mock_adjust.assert_called_once()
        mock_render.assert_called_once()

    @patch('cvextract.cli_execute._collect_inputs')
    @patch('cvextract.cli_execute.extract_single')
    @patch('cvextract.cli_execute.adjust_for_customer')
    @patch('cvextract.cli_execute.render_and_verify')
    def test_adjust_exception_fallback(self, mock_render, mock_adjust, mock_extract, mock_collect,
                                       tmp_path: Path, mock_docx: Path, mock_template: Path):
        """Test that adjustment exceptions are handled and apply proceeds with original JSON."""
        mock_collect.return_value = [mock_docx]
        
        # Mock extract_single to create a JSON file
        def fake_extract(docx_file, out_json, debug):
            out_json.parent.mkdir(parents=True, exist_ok=True)
            out_json.write_text(json.dumps({"identity": {}, "sidebar": {}, "overview": "", "experiences": []}))
            return True, [], []
        
        mock_extract.side_effect = fake_extract
        mock_adjust.side_effect = Exception("Adjustment failed")
        mock_render.return_value = (True, [], [], True)
        
        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=None),
            adjust=AdjustStage(
                customer_url="https://example.com",
                openai_model="gpt-4",
                dry_run=False,
                data=None,
                output=None
            ),
            apply=ApplyStage(template=mock_template, data=None, output=None),
            target_dir=tmp_path / "out",
            strict=False,
            debug=False,
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
            debug=False,
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
            debug=False,
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
            debug=True,
            log_file=None
        )
        
        exit_code = execute_pipeline(config)
        assert exit_code == 1

    @patch('cvextract.cli_execute._collect_inputs')
    @patch('cvextract.cli_execute.extract_single')
    @patch('cvextract.cli_execute.adjust_for_customer')
    def test_adjust_exception_debug_mode(self, mock_adjust, mock_extract, mock_collect,
                                         tmp_path: Path, mock_docx: Path):
        """Test that adjust exceptions in debug mode are logged."""
        mock_collect.return_value = [mock_docx]
        mock_extract.return_value = (True, [], [])
        mock_adjust.side_effect = Exception("Adjustment error")
        
        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=None),
            adjust=AdjustStage(
                customer_url="https://example.com",
                openai_model="gpt-4",
                dry_run=True,
                data=None,
                output=None
            ),
            apply=None,
            target_dir=tmp_path / "out",
            strict=False,
            debug=True,
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
            debug=False,
            log_file=None
        )
        
        exit_code = execute_pipeline(config)
        # Should return error code 1 for wrong file type
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
            debug=False,
            log_file=None
        )
        
        exit_code = execute_pipeline(config)
        # Should return error code 1 for wrong file type
        assert exit_code == 1
        mock_render.assert_not_called()
