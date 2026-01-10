"""
Tests for cli_execute_render module to achieve 91% coverage.

These tests cover missing error paths and validation logic.
"""

import json
from pathlib import Path

from cvextract.cli_config import RenderStage, UserConfig
from cvextract.cli_execute_render import execute
from cvextract.shared import StepName, UnitOfWork


class TestCliExecuteRenderCoverage:
    """Tests for cli_execute_render.execute function."""

    def test_execute_returns_work_when_render_missing(self, tmp_path):
        """Test execute returns work unchanged when config.render is None."""
        config = UserConfig(target_dir=tmp_path)
        work = UnitOfWork(config=config)
        work.set_step_paths(
            StepName.Render,
            input_path=tmp_path / "input.json",
            output_path=tmp_path / "output.json",
        )

        result = execute(work)

        assert result == work

    def test_execute_returns_work_when_input_missing(self, tmp_path):
        """Test execute returns work when no render input is available."""
        template = tmp_path / "template.docx"
        template.touch()

        config = UserConfig(target_dir=tmp_path, render=RenderStage(template=template))
        work = UnitOfWork(config=config)

        result = execute(work)

        assert result == work

    def test_execute_returns_work_when_input_missing(self, tmp_path):
        """Test execute returns work when input JSON is missing."""
        template = tmp_path / "template.docx"
        template.write_text("docx")
        missing_input = tmp_path / "missing.json"

        config = UserConfig(
            target_dir=tmp_path,
            render=RenderStage(template=template, data=missing_input),
        )
        work = UnitOfWork(config=config)

        result = execute(work)

        render_status = result.step_states.get(StepName.Render)
        assert render_status is not None
        assert any("render input JSON not found" in e for e in render_status.errors)

    def test_execute_returns_work_when_input_path_none(self, tmp_path):
        """Test execute returns work when input_path cannot be resolved."""
        template = tmp_path / "template.docx"
        template.write_text("docx")

        config = UserConfig(target_dir=tmp_path, render=RenderStage(template=template))
        work = UnitOfWork(config=config)

        result = execute(work)

        assert result == work
        assert StepName.Render not in result.step_states

    def test_execute_returns_work_when_template_missing(self, tmp_path):
        """Test execute returns work when template doesn't exist."""
        nonexistent_template = tmp_path / "nonexistent.docx"

        input_json = tmp_path / "input.json"
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
        input_json.write_text(json.dumps(cv_data))

        config = UserConfig(
            target_dir=tmp_path,
            render=RenderStage(template=nonexistent_template, data=input_json),
        )
        work = UnitOfWork(config=config)

        result = execute(work)

        # Should return work without raising error (ensure_path_exists handles it)
        assert result.config.render.template == nonexistent_template
        render_status = result.step_states.get(StepName.Render)
        assert render_status is not None
        assert any("render template not found" in e for e in render_status.errors)

    def test_execute_returns_work_when_template_is_directory(self, tmp_path):
        """Test execute returns work when template path is a directory."""
        input_json = tmp_path / "input.json"
        input_json.write_text("{}")
        template_dir = tmp_path / "template_dir"
        template_dir.mkdir()

        config = UserConfig(
            target_dir=tmp_path,
            render=RenderStage(template=template_dir, data=input_json),
        )
        work = UnitOfWork(config=config)

        result = execute(work)

        render_status = result.step_states.get(StepName.Render)
        assert render_status is not None
        assert any("render template is not a file" in e for e in render_status.errors)
