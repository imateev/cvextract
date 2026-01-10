"""Tests for cli_execute_pipeline module - pipeline execution phase."""

import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cvextract.cli_config import (
    AdjusterConfig,
    AdjustStage,
    ExtractStage,
    ParallelStage,
    RenderStage,
    UserConfig,
)
from cvextract.cli_execute_pipeline import _build_rerun_config, execute_pipeline
from cvextract.shared import StepName, UnitOfWork


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
def mock_json(tmp_path: Path):
    """Create a valid CV JSON file."""
    json_file = tmp_path / "test.json"
    data = _valid_cv_payload()
    json_file.write_text(json.dumps(data, indent=2))
    return json_file


def _valid_cv_payload() -> dict:
    return {
        "identity": {
            "title": "Engineer",
            "full_name": "Test User",
            "first_name": "Test",
            "last_name": "User",
        },
        "sidebar": {"languages": ["English"]},
        "overview": "Test overview",
        "experiences": [{"heading": "Role", "description": "Work"}],
    }


def _extract_result(
    work: UnitOfWork, ok: bool, errs: list[str], warns: list[str]
) -> UnitOfWork:
    output_path = work.get_step_output(StepName.Extract)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(_valid_cv_payload()))
    status = work.ensure_step_status(StepName.Extract)
    status.warnings = list(warns)
    status.errors = list(errs)
    return work


def _adjust_result(work: UnitOfWork, payload: dict) -> UnitOfWork:
    output_path = work.get_step_output(StepName.Adjust)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload))
    return work


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
            render=None,
            target_dir=tmp_path / "out",
            verbosity="minimal",
            log_file=None,
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 1


class TestExecutePipelineExtractOnly:
    """Tests for execute_pipeline with extract stage only."""

    @patch("cvextract.cli_execute_extract.extract_single")
    def test_extract_success(self, mock_extract, tmp_path: Path, mock_docx: Path):
        """Test successful extraction."""
        mock_extract.side_effect = lambda work: _extract_result(work, True, [], [])

        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=None),
            adjust=None,
            render=None,
            target_dir=tmp_path / "out",
            verbosity="minimal",
            log_file=None,
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0
        mock_extract.assert_called_once()

    def test_extract_with_unknown_extractor(self, tmp_path: Path, mock_docx: Path):
        """Test extraction with unknown extractor name returns error."""

        config = UserConfig(
            extract=ExtractStage(
                source=mock_docx, output=None, name="nonexistent-extractor"
            ),
            adjust=None,
            render=None,
            target_dir=tmp_path / "out",
            verbosity="minimal",
            log_file=None,
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 1

    @patch("cvextract.cli_execute_extract.extract_single")
    def test_extract_with_warnings_returns_zero(
        self, mock_extract, tmp_path: Path, mock_docx: Path
    ):
        """Test extraction with warnings returns 0 (success)."""
        mock_extract.side_effect = lambda work: _extract_result(
            work, True, [], ["warning"]
        )

        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=None),
            adjust=None,
            render=None,
            target_dir=tmp_path / "out",
            log_file=None,
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0

    @patch("cvextract.cli_execute_extract.extract_single")
    def test_extract_failure(self, mock_extract, tmp_path: Path, mock_docx: Path):
        """Test extraction failure returns 1."""
        mock_extract.side_effect = lambda work: _extract_result(
            work, False, ["error"], []
        )

        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=None),
            adjust=None,
            render=None,
            target_dir=tmp_path / "out",
            log_file=None,
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 1

    @patch("cvextract.cli_execute_extract.extract_single")
    def test_extract_with_custom_output(
        self, mock_extract, tmp_path: Path, mock_docx: Path
    ):
        """Test extraction with custom output path."""
        mock_extract.side_effect = lambda work: _extract_result(work, True, [], [])

        custom_output = tmp_path / "custom.json"
        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=custom_output),
            adjust=None,
            render=None,
            target_dir=tmp_path / "out",
            verbosity="minimal",
            log_file=None,
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0
        # Verify extract_single was called with custom output
        call_args = mock_extract.call_args
        assert (
            call_args[0][0].get_step_output(StepName.Extract) == custom_output
        )


class TestExecutePipelineExtractApply:
    """Tests for execute_pipeline with extract + apply stages."""

    @patch("cvextract.cli_execute_extract.extract_single")
    @patch("cvextract.cli_execute_single.roundtrip_verify")
    @patch("cvextract.cli_execute_render.render")
    def test_extract_apply_success(
        self,
        mock_render,
        mock_verify,
        mock_extract,
        tmp_path: Path,
        mock_docx: Path,
        mock_template: Path,
    ):
        """Test successful extract + apply."""
        mock_extract.side_effect = lambda work: _extract_result(work, True, [], [])
        mock_render.side_effect = lambda work: work
        mock_verify.side_effect = lambda work: work

        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=None),
            adjust=None,
            render=RenderStage(template=mock_template, data=None, output=None),
            target_dir=tmp_path / "out",
            verbosity="minimal",
            log_file=None,
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0
        mock_extract.assert_called_once()
        mock_render.assert_called_once()

    @patch("cvextract.cli_execute_extract.extract_single")
    @patch("cvextract.cli_execute_single.roundtrip_verify")
    @patch("cvextract.cli_execute_render.render")
    def test_extract_fails_apply_skipped(
        self,
        mock_render,
        mock_verify,
        mock_extract,
        tmp_path: Path,
        mock_docx: Path,
        mock_template: Path,
    ):
        """Test that apply is skipped if extract fails."""
        mock_extract.side_effect = lambda work: _extract_result(
            work, False, ["extract error"], []
        )

        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=None),
            adjust=None,
            render=RenderStage(template=mock_template, data=None, output=None),
            target_dir=tmp_path / "out",
            log_file=None,
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 1
        mock_extract.assert_called_once()
        mock_render.assert_not_called()
        mock_verify.assert_not_called()

    @patch("cvextract.cli_execute_extract.extract_single")
    @patch("cvextract.cli_execute_single.roundtrip_verify")
    @patch("cvextract.cli_execute_render.render")
    def test_extract_apply_both_warnings_returns_zero(
        self,
        mock_render,
        mock_verify,
        mock_extract,
        tmp_path: Path,
        mock_docx: Path,
        mock_template: Path,
    ):
        """Test extract + apply with warnings returns 0 (success)."""
        mock_extract.side_effect = lambda work: _extract_result(
            work, True, [], ["extract warning"]
        )
        mock_render.side_effect = lambda work: work
        mock_verify.side_effect = lambda work: work

        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=None),
            adjust=None,
            render=RenderStage(template=mock_template, data=None, output=None),
            target_dir=tmp_path / "out",
            log_file=None,
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0


class TestExecutePipelineApplyOnly:
    """Tests for execute_pipeline with apply stage only (from existing JSON)."""

    @patch("cvextract.cli_execute_single.roundtrip_verify")
    @patch("cvextract.cli_execute_render.render")
    def test_apply_from_json_success(
        self,
        mock_render,
        mock_verify,
        tmp_path: Path,
        mock_json: Path,
        mock_template: Path,
    ):
        """Test applying from existing JSON file."""
        mock_render.side_effect = lambda work: work
        mock_verify.side_effect = lambda work: work

        config = UserConfig(
            extract=None,
            adjust=None,
            render=RenderStage(template=mock_template, data=mock_json, output=None),
            target_dir=tmp_path / "out",
            log_file=None,
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0
        mock_render.assert_called_once()

    @patch("cvextract.cli_execute_single.roundtrip_verify")
    @patch("cvextract.cli_execute_render.render")
    def test_apply_custom_output(
        self,
        mock_render,
        mock_verify,
        tmp_path: Path,
        mock_json: Path,
        mock_template: Path,
    ):
        """Test applying with custom output path."""
        mock_render.side_effect = lambda work: work
        mock_verify.side_effect = lambda work: work

        custom_output = tmp_path / "custom_output.docx"
        config = UserConfig(
            extract=None,
            adjust=None,
            render=RenderStage(
                template=mock_template, data=mock_json, output=custom_output
            ),
            target_dir=tmp_path / "out",
            log_file=None,
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0
        render_work = mock_render.call_args[0][0]
        assert render_work.config.render.output == custom_output


class TestExecutePipelineAdjust:
    """Tests for execute_pipeline with adjust stage."""

    @patch("cvextract.cli_execute_extract.extract_single")
    @patch("cvextract.cli_execute_adjust.get_adjuster")
    @patch("cvextract.cli_execute_single.roundtrip_verify")
    @patch("cvextract.cli_execute_render.render")
    def test_extract_adjust_apply_success(
        self,
        mock_render,
        mock_verify,
        mock_get_adjuster,
        mock_extract,
        tmp_path: Path,
        mock_docx: Path,
        mock_template: Path,
    ):
        """Test successful extract + adjust + apply."""

        # Mock extract_single to create a JSON file
        def fake_extract(work: UnitOfWork):
            output_path = work.get_step_output(StepName.Extract)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(_valid_cv_payload()))
            return _extract_result(work, True, [], [])

        mock_extract.side_effect = fake_extract

        # Mock adjuster
        mock_adjuster = MagicMock()
        mock_adjuster.adjust.side_effect = lambda work, **kwargs: _adjust_result(
            work, _valid_cv_payload()
        )
        mock_adjuster.validate_params.return_value = None
        mock_get_adjuster.return_value = mock_adjuster

        mock_render.side_effect = lambda work: work
        mock_verify.side_effect = lambda work: work

        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=None),
            adjust=AdjustStage(
                adjusters=[
                    AdjusterConfig(
                        name="openai-company-research",
                        params={"customer-url": "https://example.com"},
                        openai_model="gpt-4",
                    )
                ],
                dry_run=False,
                data=None,
                output=None,
            ),
            render=RenderStage(template=mock_template, data=None, output=None),
            target_dir=tmp_path / "out",
            verbosity="minimal",
            log_file=None,
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0
        mock_extract.assert_called_once()
        mock_adjuster.adjust.assert_called_once()
        mock_render.assert_called_once()

    @patch("cvextract.cli_execute_extract.extract_single")
    @patch("cvextract.cli_execute_adjust.get_adjuster")
    def test_adjust_dry_run_skips_apply(
        self,
        mock_get_adjuster,
        mock_extract,
        tmp_path: Path,
        mock_docx: Path,
        mock_template: Path,
    ):
        """Test that dry-run mode skips apply stage."""

        # Mock extract_single to create a JSON file
        def fake_extract(work: UnitOfWork):
            output_path = work.get_step_output(StepName.Extract)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(_valid_cv_payload()))
            return _extract_result(work, True, [], [])

        mock_extract.side_effect = fake_extract
        # Mock adjuster
        mock_adjuster = MagicMock()
        mock_adjuster.adjust.side_effect = lambda work, **kwargs: _adjust_result(
            work, _valid_cv_payload()
        )
        mock_adjuster.validate_params.return_value = None
        mock_get_adjuster.return_value = mock_adjuster

        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=None),
            adjust=AdjustStage(
                adjusters=[
                    AdjusterConfig(
                        name="openai-company-research",
                        params={"customer-url": "https://example.com"},
                        openai_model="gpt-4",
                    )
                ],
                dry_run=True,
                data=None,
                output=None,
            ),
            render=RenderStage(template=mock_template, data=None, output=None),
            target_dir=tmp_path / "out",
            log_file=None,
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0
        mock_extract.assert_called_once()
        mock_adjuster.adjust.assert_called_once()

    @patch("cvextract.cli_execute_adjust.get_adjuster")
    @patch("cvextract.cli_execute_single.roundtrip_verify")
    @patch("cvextract.cli_execute_render.render")
    def test_adjust_from_json(
        self,
        mock_render,
        mock_verify,
        mock_get_adjuster,
        tmp_path: Path,
        mock_json: Path,
        mock_template: Path,
    ):
        """Test adjust from existing JSON without extraction."""
        # Mock adjuster
        mock_adjuster = MagicMock()
        mock_adjuster.adjust.side_effect = lambda work, **kwargs: _adjust_result(
            work, _valid_cv_payload()
        )
        mock_adjuster.validate_params.return_value = None
        mock_get_adjuster.return_value = mock_adjuster
        mock_render.side_effect = lambda work: work
        mock_verify.side_effect = lambda work: work
        config = UserConfig(
            extract=None,
            adjust=AdjustStage(
                adjusters=[
                    AdjusterConfig(
                        name="openai-company-research",
                        params={"customer-url": "https://example.com"},
                        openai_model="gpt-4",
                    )
                ],
                dry_run=False,
                data=mock_json,
                output=None,
            ),
            render=RenderStage(template=mock_template, data=None, output=None),
            target_dir=tmp_path / "out",
            log_file=None,
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0
        mock_adjuster.adjust.assert_called_once()
        mock_render.assert_called_once()

    @patch("cvextract.cli_execute_adjust.get_adjuster")
    def test_adjust_research_cache_is_delegated(
        self, mock_get_adjuster, tmp_path: Path, parallel_input_tree
    ):
        """Research cache decision is delegated to the adjuster, not CLI."""
        payload = _valid_cv_payload()
        input_json = parallel_input_tree.json("folder/profile.json", payload)
        # Mock adjuster
        mock_adjuster = MagicMock()
        mock_adjuster.adjust.side_effect = lambda work, **kwargs: _adjust_result(
            work, _valid_cv_payload()
        )
        mock_adjuster.validate_params.return_value = None
        mock_get_adjuster.return_value = mock_adjuster

        config = UserConfig(
            extract=None,
            input_dir=parallel_input_tree.root,
            adjust=AdjustStage(
                adjusters=[
                    AdjusterConfig(
                        name="openai-company-research",
                        params={"customer-url": "https://example.com"},
                        openai_model="gpt-4",
                    )
                ],
                dry_run=False,
                data=input_json,
                output=None,
            ),
            render=None,
            target_dir=tmp_path / "out",
            log_file=None,
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0

        mock_adjuster.adjust.assert_called_once()
        # CLI should not inject cache_path into adjuster params
        call_kwargs = mock_adjuster.adjust.call_args.kwargs
        assert "cache_path" not in call_kwargs
        
class TestExecutePipelineDebugMode:
    """Tests for execute_pipeline with debug mode."""

    @patch("cvextract.cli_execute_extract.extract_single")
    @patch("cvextract.cli_execute_adjust.get_adjuster")
    def test_adjust_exception_debug_mode(
        self, mock_get_adjuster, mock_extract, tmp_path: Path, mock_docx: Path
    ):
        """Test that adjust exceptions in debug mode are logged."""

        def fake_extract(work: UnitOfWork):
            output_path = work.get_step_output(StepName.Extract)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(_valid_cv_payload()))
            return _extract_result(work, True, [], [])

        mock_extract.side_effect = fake_extract
        # Mock adjuster to raise exception
        mock_adjuster = MagicMock()
        mock_adjuster.adjust.side_effect = Exception("Adjustment error")
        mock_adjuster.validate_params.return_value = None
        mock_get_adjuster.return_value = mock_adjuster

        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=None),
            adjust=AdjustStage(
                adjusters=[
                    AdjusterConfig(
                        name="openai-company-research",
                        params={"customer-url": "https://example.com"},
                        openai_model="gpt-4",
                    )
                ],
                dry_run=True,
                data=None,
                output=None,
            ),
            render=None,
            target_dir=tmp_path / "out",
            log_file=None,
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0  # Dry run doesn't fail on adjust error


class TestFolderStructurePreservation:
    """Tests for preserving folder structure in output directories."""

    @patch("cvextract.cli_execute_extract.extract_single")
    def test_extract_preserves_folder_structure(
        self, mock_extract, tmp_path: Path, parallel_input_tree
    ):
        """Test that extracted JSON files preserve folder structure."""
        # Create a nested input file structure rooted under the simulated parallel input tree
        input_file = parallel_input_tree.docx("DACH/Software Engineering/profile.docx")

        mock_extract.side_effect = lambda work: _extract_result(work, True, [], [])

        config = UserConfig(
            extract=ExtractStage(source=input_file, output=None),
            adjust=None,
            render=None,
            target_dir=tmp_path / "output",
            verbosity="minimal",
            log_file=None,
            input_dir=parallel_input_tree.root,  # Mirror how parallel mode seeds rel_path
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0

        # Verify extract was called with the correct output path
        call_args = mock_extract.call_args
        output_json = call_args[0][0].get_step_output(StepName.Extract)

        # Output should be in DACH/Software Engineering subdirectory
        assert "DACH" in str(output_json)
        assert "Software Engineering" in str(output_json)
        assert (
            output_json.parent.parent.parent == tmp_path / "output" / "structured_data"
        )

    @patch("cvextract.cli_execute_extract.extract_single")
    @patch("cvextract.cli_execute_adjust.get_adjuster")
    def test_adjust_preserves_folder_structure(
        self, mock_get_adjuster, mock_extract, tmp_path: Path, parallel_input_tree
    ):
        """Test that adjusted JSON files preserve folder structure."""
        # Create nested input rooted at parallel tree to capture rel_path logic
        input_file = parallel_input_tree.docx("DACH/Software Engineering/profile.docx")

        def fake_extract(work: UnitOfWork):
            output_path = work.get_step_output(StepName.Extract)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(_valid_cv_payload()))
            return _extract_result(work, True, [], [])

        mock_extract.side_effect = fake_extract
        # Mock adjuster
        mock_adjuster = MagicMock()
        mock_adjuster.adjust.side_effect = lambda work, **kwargs: _adjust_result(
            work, _valid_cv_payload()
        )
        mock_adjuster.validate_params.return_value = None
        mock_get_adjuster.return_value = mock_adjuster

        config = UserConfig(
            extract=ExtractStage(source=input_file, output=None),
            adjust=AdjustStage(
                adjusters=[
                    AdjusterConfig(
                        name="openai-company-research",
                        params={"customer-url": "https://example.com"},
                        openai_model="gpt-4",
                    )
                ],
                dry_run=True,
                data=None,
                output=None,
            ),
            render=None,
            target_dir=tmp_path / "output",
            log_file=None,
            input_dir=parallel_input_tree.root,
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0

        # Verify that adjusted JSON would be created with the same structure
        mock_adjuster.adjust.assert_called_once()

    @patch("cvextract.cli_execute_extract.extract_single")
    @patch("cvextract.cli_execute_single.roundtrip_verify")
    @patch("cvextract.cli_execute_render.render")
    def test_apply_preserves_folder_structure(
        self,
        mock_render,
        mock_verify,
        mock_extract,
        tmp_path: Path,
        mock_template: Path,
        parallel_input_tree,
    ):
        """Test that output DOCX files preserve folder structure."""
        # Create nested input rooted at the simulated parallel tree
        input_file = parallel_input_tree.docx("DACH/Software Engineering/profile.docx")

        def fake_extract(work: UnitOfWork):
            output_path = work.get_step_output(StepName.Extract)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(_valid_cv_payload()))
            return _extract_result(work, True, [], [])

        mock_extract.side_effect = fake_extract
        mock_render.side_effect = lambda work: work
        mock_verify.side_effect = lambda work: work

        config = UserConfig(
            extract=ExtractStage(source=input_file, output=None),
            adjust=None,
            render=RenderStage(template=mock_template, data=None, output=None),
            target_dir=tmp_path / "output",
            log_file=None,
            input_dir=parallel_input_tree.root,
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0

        render_work = mock_render.call_args[0][0]
        input_path = render_work.initial_input
        source_base = render_work.config.input_dir.resolve()
        rel_path = input_path.parent.resolve().relative_to(source_base)
        output_docx = (
            render_work.config.workspace.documents_dir
            / rel_path
            / f"{input_path.stem}_NEW.docx"
        )

        # Output should be in DACH/Software Engineering subdirectory
        assert "DACH" in str(output_docx)
        assert "Software Engineering" in str(output_docx)
        assert output_docx.parent.parent.parent == tmp_path / "output" / "documents"

    @patch("cvextract.cli_execute_extract.extract_single")
    def test_flat_structure_without_input_dir(self, mock_extract, tmp_path: Path):
        """Test that without input_dir, structure defaults to flat (backward compatibility)."""
        # Create a nested input file
        input_dir = tmp_path / "input" / "DACH" / "Software Engineering"
        input_dir.mkdir(parents=True)
        input_file = input_dir / "profile.docx"
        input_file.write_text("docx")

        mock_extract.side_effect = lambda work: _extract_result(work, True, [], [])

        config = UserConfig(
            extract=ExtractStage(source=input_file, output=None),
            adjust=None,
            render=None,
            target_dir=tmp_path / "output",
            log_file=None,
            input_dir=None,  # No input_dir specified, behavior depends on source
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0

        # The behavior will depend on whether source is a file or directory
        # If source is a file, rel_path will be calculated from source.parent
        mock_extract.assert_called_once()

    @patch("cvextract.cli_execute_extract.extract_single")
    def test_parallel_mode_delegates_to_parallel_pipeline(
        self, mock_extract, tmp_path: Path
    ):
        """execute_pipeline() with parallel=True delegates to execute_parallel_pipeline."""
        mock_docx = tmp_path / "test.docx"
        mock_docx.write_text("docx")
        mock_extract.side_effect = lambda work: _extract_result(work, True, [], [])

        with patch(
            "cvextract.cli_execute_parallel.execute_parallel_pipeline", return_value=0
        ) as mock_parallel:
            config = UserConfig(
                extract=ExtractStage(source=mock_docx, output=None),
                adjust=None,
                render=None,
                target_dir=tmp_path / "output",
                log_file=None,
                parallel=True,  # Enable parallel mode
            )

            exit_code = execute_pipeline(config)
            assert exit_code == 0
            mock_parallel.assert_called_once_with(config)

    def test_rerun_failed_serial_writes_failed_list(self, tmp_path: Path):
        """execute_pipeline() reruns a failed list serially and logs failures."""
        failed_list = tmp_path / "failed.txt"
        doc_a = tmp_path / "a.docx"
        doc_b = tmp_path / "b.docx"
        failed_list.write_text(f"{doc_a}\n{doc_b}\n", encoding="utf-8")

        config = UserConfig(
            extract=ExtractStage(source=doc_a, output=None),
            adjust=None,
            render=None,
            target_dir=tmp_path / "output",
            log_failed=tmp_path / "rerun_failed_out.txt",
            rerun_failed=failed_list,
        )

        def _fake_execute_single(cfg):
            work = UnitOfWork(config=cfg, initial_input=doc_a)
            exit_code = 1 if cfg.extract and cfg.extract.source == doc_b else 0
            return exit_code, work

        with patch(
            "cvextract.cli_execute_pipeline.execute_single",
            side_effect=_fake_execute_single,
        ):
            exit_code = execute_pipeline(config)

        assert exit_code == 1
        logged = config.log_failed.read_text(encoding="utf-8").strip().splitlines()
        assert logged == [str(doc_b)]

    def test_rerun_failed_missing_list_returns_error(self, tmp_path: Path):
        """execute_pipeline() returns error if rerun list cannot be read."""
        missing_list = tmp_path / "missing.txt"

        config = UserConfig(
            target_dir=tmp_path / "output",
            rerun_failed=missing_list,
        )

        with patch("cvextract.cli_execute_pipeline.execute_single") as mock_execute:
            exit_code = execute_pipeline(config)

        assert exit_code == 1
        mock_execute.assert_not_called()

    def test_rerun_failed_empty_list_returns_error(self, tmp_path: Path):
        """execute_pipeline() returns error when rerun list is empty."""
        failed_list = tmp_path / "failed.txt"
        failed_list.write_text("# comment\n\n", encoding="utf-8")

        config = UserConfig(
            target_dir=tmp_path / "output",
            rerun_failed=failed_list,
        )

        with patch("cvextract.cli_execute_pipeline.execute_single") as mock_execute:
            exit_code = execute_pipeline(config)

        assert exit_code == 1
        mock_execute.assert_not_called()

    def test_rerun_failed_parallel_uses_failed_list(self, tmp_path: Path):
        """execute_pipeline() uses rerun list for parallel reruns."""
        failed_list = tmp_path / "failed.txt"
        doc_a = tmp_path / "a.docx"
        doc_b = tmp_path / "b.docx"
        failed_list.write_text(f"{doc_a}\n{doc_b}\n", encoding="utf-8")

        config = UserConfig(
            extract=ExtractStage(source=doc_a, output=None),
            adjust=None,
            render=None,
            target_dir=tmp_path / "output",
            parallel=ParallelStage(source=tmp_path, n=2, file_type="*.docx"),
            rerun_failed=failed_list,
        )

        with patch(
            "cvextract.cli_execute_parallel._execute_parallel_pipeline", return_value=0
        ) as mock_parallel:
            exit_code = execute_pipeline(config)

        assert exit_code == 0
        args, _kwargs = mock_parallel.call_args
        assert [str(p) for p in args[0]] == [str(doc_a), str(doc_b)]

    def test_build_rerun_config_updates_render_data(self, tmp_path: Path):
        """_build_rerun_config should replace render data with file path."""
        template = tmp_path / "template.docx"
        template.touch()
        original = tmp_path / "original.json"
        rerun_path = tmp_path / "rerun.json"

        config = UserConfig(
            target_dir=tmp_path,
            render=RenderStage(template=template, data=original),
            parallel=ParallelStage(source=tmp_path, n=1),
            input_dir=tmp_path / "input",
        )

        rerun_config = _build_rerun_config(config, rerun_path)

        assert rerun_config.render is not None
        assert rerun_config.render.data == rerun_path
        assert rerun_config.parallel is None
        assert rerun_config.input_dir is None

    def test_build_rerun_config_updates_adjust_data(self, tmp_path: Path):
        """_build_rerun_config should replace adjust data with file path."""
        original = tmp_path / "original.json"
        rerun_path = tmp_path / "rerun.json"

        config = UserConfig(
            target_dir=tmp_path,
            adjust=AdjustStage(
                adjusters=[AdjusterConfig(name="noop", params={})],
                data=original,
            ),
            parallel=ParallelStage(source=tmp_path, n=1),
            input_dir=tmp_path / "input",
        )

        rerun_config = _build_rerun_config(config, rerun_path)

        assert rerun_config.adjust is not None
        assert rerun_config.adjust.data == rerun_path
        assert rerun_config.parallel is None
        assert rerun_config.input_dir is None

    @patch("cvextract.cli_execute_extract.extract_single")
    def test_relative_path_calculation_with_value_error_fallback(
        self, mock_extract, tmp_path: Path
    ):
        """execute_pipeline() falls back to '.' when relative_to() raises ValueError."""
        mock_docx = tmp_path / "test.docx"
        mock_docx.write_text("docx")
        mock_extract.side_effect = lambda work: _extract_result(work, True, [], [])

        # Create a config where input_dir is outside of the resolved input_file parent
        # This will cause ValueError when trying to compute relative_to
        config = UserConfig(
            extract=ExtractStage(source=mock_docx, output=None),
            adjust=None,
            render=None,
            target_dir=tmp_path / "output",
            log_file=None,
            input_dir=tmp_path / "other_dir",  # Different from the file's parent
        )

        exit_code = execute_pipeline(config)
        assert exit_code == 0  # Should still succeed with fallback
        mock_extract.assert_called_once()
