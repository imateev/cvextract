"""
Additional tests for pipeline_helpers module to achieve 91% coverage.

These tests cover error paths and edge cases that were missing.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import cvextract.pipeline_helpers as p
from cvextract.cli_config import (
    AdjusterConfig,
    AdjustStage,
    ExtractStage,
    RenderStage,
    UserConfig,
)
from cvextract.shared import StepName, UnitOfWork


class TestPipelineHelpersCoverage:
    """Tests for pipeline_helpers functions to improve coverage."""

    def test_resolve_source_base_for_render_with_input_dir(self, tmp_path):
        """Test _resolve_source_base_for_render when input_dir is set."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        json_file = tmp_path / "test.json"
        json_file.touch()

        config = UserConfig(target_dir=tmp_path, input_dir=input_dir)
        work = UnitOfWork(config=config, initial_input=json_file)

        result = p._resolve_source_base_for_render(work, json_file)

        assert result == input_dir.resolve()

    def test_resolve_source_base_for_render_with_extract_source(self, tmp_path):
        """Test _resolve_source_base_for_render when extract.source is set."""
        source = tmp_path / "source.docx"
        source.touch()

        json_file = tmp_path / "test.json"
        json_file.touch()

        config = UserConfig(target_dir=tmp_path, extract=ExtractStage(source=source))
        work = UnitOfWork(config=config, initial_input=json_file)

        result = p._resolve_source_base_for_render(work, json_file)

        assert result == source.parent.resolve()

    def test_resolve_source_base_for_render_with_render_data(self, tmp_path):
        """Test _resolve_source_base_for_render when render.data is set."""
        data = tmp_path / "data.json"
        data.touch()
        template = tmp_path / "template.docx"
        template.touch()

        json_file = tmp_path / "test.json"
        json_file.touch()

        config = UserConfig(
            target_dir=tmp_path, render=RenderStage(template=template, data=data)
        )
        work = UnitOfWork(config=config, initial_input=json_file)

        result = p._resolve_source_base_for_render(work, json_file)

        assert result == data.parent.resolve()

    def test_resolve_source_base_for_render_with_adjust_data(self, tmp_path):
        """Test _resolve_source_base_for_render when adjust.data is set."""
        data = tmp_path / "data.json"
        data.touch()

        json_file = tmp_path / "test.json"
        json_file.touch()

        config = UserConfig(
            target_dir=tmp_path,
            adjust=AdjustStage(
                data=data, adjusters=[AdjusterConfig(name="test", params={})]
            ),
        )
        work = UnitOfWork(config=config, initial_input=json_file)

        result = p._resolve_source_base_for_render(work, json_file)

        assert result == data.parent.resolve()

    def test_resolve_source_base_for_render_fallback(self, tmp_path):
        """Test _resolve_source_base_for_render fallback to input_path.parent."""
        json_file = tmp_path / "subdir" / "test.json"
        json_file.parent.mkdir(parents=True, exist_ok=True)
        json_file.touch()

        config = UserConfig(target_dir=tmp_path)
        work = UnitOfWork(config=config, initial_input=json_file)

        result = p._resolve_source_base_for_render(work, json_file)

        assert result == json_file.parent.resolve()

    def test_resolve_parent_with_exception(self, tmp_path):
        """Test _resolve_parent handles exception from relative_to."""
        input_path = tmp_path / "input" / "test.json"
        input_path.parent.mkdir(parents=True, exist_ok=True)
        input_path.touch()

        # Use a completely different path as source_base
        source_base = tmp_path / "different" / "base"
        source_base.mkdir(parents=True, exist_ok=True)

        result = p._resolve_parent(input_path, source_base)

        # Should fall back to "."
        assert result == Path(".")

    def test_render_docx_missing_render_config(self, tmp_path):
        """Test _render_docx returns error when render config is missing."""
        config = UserConfig(target_dir=tmp_path)
        work = UnitOfWork(config=config)

        result = p._render_docx(work)

        render_status = result.step_states.get(StepName.Render)
        assert render_status is not None
        assert len(render_status.errors) > 0
        assert "missing render configuration" in render_status.errors[0]

    def test_render_docx_missing_output(self, tmp_path):
        """Test _render_docx returns error when output is None."""
        template = tmp_path / "template.docx"
        template.touch()

        config = UserConfig(target_dir=tmp_path, render=RenderStage(template=template))
        work = UnitOfWork(config=config)

        result = p._render_docx(work)

        render_status = result.step_states.get(StepName.Render)
        assert render_status is not None
        assert len(render_status.errors) > 0
        assert "input JSON path is not set" in render_status.errors[0]

    def test_render_docx_handles_exception(self, tmp_path):
        """Test _render_docx handles exception from render_cv_data."""
        json_file = tmp_path / "test.json"
        cv_data = {
            "identity": {
                "title": "Dev",
                "full_name": "Test",
                "first_name": "T",
                "last_name": "Test",
            },
            "sidebar": {},
            "overview": "",
            "experiences": [],
        }
        json_file.write_text(json.dumps(cv_data))

        template = tmp_path / "template.docx"
        template.touch()

        config = UserConfig(target_dir=tmp_path, render=RenderStage(template=template))
        work = UnitOfWork(config=config, initial_input=json_file)
        work.set_step_paths(StepName.Render, input_path=json_file)

        with patch("cvextract.pipeline_helpers.render_cv_data") as mock_render:
            mock_render.side_effect = RuntimeError("Test error")

            result = p._render_docx(work)

            render_status = result.step_states.get(StepName.Render)
            assert render_status is not None
            assert len(render_status.warnings) > 0
            assert "RuntimeError" in render_status.warnings[0]

    def test_extract_single_unknown_extractor(self, tmp_path):
        """Test extract_single handles unknown extractor."""
        docx = tmp_path / "test.docx"
        docx.touch()
        output = tmp_path / "test.json"

        config = UserConfig(
            target_dir=tmp_path,
            extract=ExtractStage(source=docx, name="unknown-extractor"),
        )
        work = UnitOfWork(config=config, initial_input=docx)
        work.set_step_paths(StepName.Extract, input_path=docx, output_path=output)

        result = p.extract_single(work)

        extract_status = result.step_states.get(StepName.Extract)
        assert extract_status is not None
        assert len(extract_status.errors) > 0
        assert "unknown extractor" in extract_status.errors[0]
        assert extract_status.ConfiguredExecutorAvailable is False

    def test_extract_single_missing_input_path(self, tmp_path):
        """Test extract_single handles missing input path."""
        docx = tmp_path / "missing.docx"
        output = tmp_path / "test.json"

        config = UserConfig(
            target_dir=tmp_path,
            extract=ExtractStage(source=docx),
        )
        work = UnitOfWork(config=config, initial_input=docx)
        work.set_step_paths(StepName.Extract, input_path=docx, output_path=output)

        result = p.extract_single(work)

        extract_status = result.step_states.get(StepName.Extract)
        assert extract_status is not None
        assert any("input file not found" in e for e in extract_status.errors)

    def test_extract_single_missing_output_path(self, tmp_path):
        """Test extract_single reports missing output path."""
        docx = tmp_path / "test.docx"
        docx.touch()

        config = UserConfig(
            target_dir=tmp_path,
            extract=ExtractStage(source=docx),
        )
        work = UnitOfWork(config=config, initial_input=docx)
        work.set_step_paths(StepName.Extract, input_path=docx)

        result = p.extract_single(work)

        extract_status = result.step_states.get(StepName.Extract)
        assert extract_status is not None
        assert "output JSON path is not set" in extract_status.errors[0]

    def test_extract_single_output_cleared_by_extractor(self, tmp_path, monkeypatch):
        """Test extract_single handles extractors that clear output."""
        docx = tmp_path / "test.docx"
        docx.touch()
        output = tmp_path / "test.json"

        def fake_extract(work, extractor=None):
            status = work.ensure_step_status(StepName.Extract)
            status.output = None
            return work

        monkeypatch.setattr(p, "extract_cv_data", fake_extract)

        config = UserConfig(
            target_dir=tmp_path,
            extract=ExtractStage(source=docx),
        )
        work = UnitOfWork(config=config, initial_input=docx)
        work.set_step_paths(StepName.Extract, input_path=docx, output_path=output)

        result = p.extract_single(work)

        extract_status = result.step_states.get(StepName.Extract)
        assert extract_status is not None
        assert "output JSON path is not set" in extract_status.errors[0]

    def test_extract_single_output_file_missing(self, tmp_path, monkeypatch):
        """Test extract_single handles missing output JSON file."""
        docx = tmp_path / "test.docx"
        docx.touch()
        output = tmp_path / "test.json"

        def fake_extract(work, extractor=None):
            return work

        monkeypatch.setattr(p, "extract_cv_data", fake_extract)

        config = UserConfig(
            target_dir=tmp_path,
            extract=ExtractStage(source=docx),
        )
        work = UnitOfWork(config=config, initial_input=docx)
        work.set_step_paths(StepName.Extract, input_path=docx, output_path=output)

        result = p.extract_single(work)

        extract_status = result.step_states.get(StepName.Extract)
        assert extract_status is not None
        assert "output JSON not found" in extract_status.errors[0]

    def test_extract_single_with_debug_mode(self, tmp_path):
        """Test extract_single in debug mode dumps body sample on error."""
        docx = tmp_path / "test.docx"
        docx.touch()
        output = tmp_path / "test.json"

        config = UserConfig(
            target_dir=tmp_path,
            extract=ExtractStage(source=docx),
            verbosity="debug",  # Set verbosity to "debug" instead of debug=True
        )
        work = UnitOfWork(config=config, initial_input=docx)
        work.set_step_paths(StepName.Extract, input_path=docx, output_path=output)

        with patch("cvextract.pipeline_helpers.extract_cv_data") as mock_process, patch(
            "cvextract.pipeline_helpers.dump_body_sample"
        ) as mock_dump:
            mock_process.side_effect = RuntimeError("Test error")

            result = p.extract_single(work)

            # Should have dumped body sample
            mock_dump.assert_called_once()
            extract_status = result.step_states.get(StepName.Extract)
            assert len(extract_status.errors) > 0
