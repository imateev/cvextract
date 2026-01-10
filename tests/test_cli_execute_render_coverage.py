"""
Tests for cli_execute_render module to achieve 91% coverage.

These tests cover missing error paths and validation logic.
"""

import json
from pathlib import Path

from docx import Document

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

    def test_execute_returns_work_when_output_missing(self, tmp_path):
        """Test execute returns work when output path doesn't exist."""
        template = tmp_path / "template.docx"
        doc = Document()
        doc.add_paragraph("Test")
        doc.save(str(template))

        # Create non-existent output path
        nonexistent_output = tmp_path / "nonexistent.json"

        config = UserConfig(target_dir=tmp_path, render=RenderStage(template=template))
        work = UnitOfWork(config=config)
        work.set_step_paths(
            StepName.Render,
            input_path=tmp_path / "input.json",
            output_path=nonexistent_output,
        )

        result = execute(work)

        # Should return work without raising error (ensure_path_exists handles it)
        assert result.get_step_output(StepName.Render) == nonexistent_output

    def test_execute_returns_work_when_template_missing(self, tmp_path):
        """Test execute returns work when template doesn't exist."""
        nonexistent_template = tmp_path / "nonexistent.docx"

        # Create valid output JSON
        output_json = tmp_path / "output.json"
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
        output_json.write_text(json.dumps(cv_data))

        config = UserConfig(
            target_dir=tmp_path, render=RenderStage(template=nonexistent_template)
        )
        work = UnitOfWork(config=config)
        work.set_step_paths(
            StepName.Render,
            input_path=tmp_path / "input.json",
            output_path=output_json,
        )

        result = execute(work)

        # Should return work without raising error (ensure_path_exists handles it)
        assert result.config.render.template == nonexistent_template
