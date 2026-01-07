"""Additional tests for CLI and pipeline edge cases."""

import zipfile
from pathlib import Path

import cvextract.cli as cli
import cvextract.pipeline as pipeline
import cvextract.pipeline_helpers as helpers
from cvextract.cli_config import UserConfig
from cvextract.shared import StepName, StepStatus, UnitOfWork, get_status_icons


class TestCliEdgeCases:
    """Tests for CLI edge cases not covered."""

    def test_main_no_matching_inputs(self, monkeypatch, tmp_path: Path):
        """Test main when no matching input files found."""
        template = tmp_path / "tpl.docx"
        with zipfile.ZipFile(template, "w") as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        # Create a file that won't match (.txt instead of .docx or .json)
        (src_dir / "file.txt").write_text("content")

        rc = cli.main(
            ["--extract", f"source={src_dir}", "--target", str(tmp_path / "out")]
        )

        assert rc == 1

    def test_main_source_not_found(self, tmp_path: Path):
        """Test main when source path does not exist."""
        template = tmp_path / "tpl.docx"
        with zipfile.ZipFile(template, "w") as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")

        rc = cli.main(
            [
                "--extract",
                f"source={tmp_path / 'nonexistent'}",
                "--target",
                str(tmp_path / "out"),
            ]
        )

        assert rc == 1

    def test_main_template_not_found(self, tmp_path: Path):
        """Test main when template file does not exist."""
        src = tmp_path / "src.docx"
        with zipfile.ZipFile(src, "w") as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")

        rc = cli.main(
            [
                "--extract",
                f"source={src}",
                "--render",
                f"template={tmp_path / 'nonexistent.docx'}",
                "--target",
                str(tmp_path / "out"),
            ]
        )

        assert rc == 1


class TestPipelineEdgeCases:
    """Tests for pipeline edge cases."""

    def test_infer_source_root_empty_list(self):
        """Test infer_source_root with empty list."""
        root = pipeline.infer_source_root([])
        assert root.is_absolute()

    def test_safe_relpath_exception_handling(self):
        """Test safe_relpath when relative_to raises exception."""
        # Create a path that will fail relative_to
        p = Path("/some/absolute/path")
        root = Path("/different/path")

        result = pipeline.safe_relpath(p, root)
        # Should fall back to just the name
        assert result == "path"

    def test_categorize_result_extract_fail(self):
        """Test _categorize_result when extract fails."""
        full, part, fail = helpers.categorize_result(
            extract_ok=False, has_warns=False, apply_ok=None
        )
        assert (full, part, fail) == (0, 0, 1)

    def test_categorize_result_apply_false_no_warns(self):
        """Test _categorize_result when apply fails without warns."""
        full, part, fail = helpers.categorize_result(
            extract_ok=True, has_warns=False, apply_ok=False
        )
        # When apply fails, it's partial (not fully failed)
        assert (full, part, fail) == (0, 1, 0)

    def test_categorize_result_success(self):
        """Test _categorize_result for successful result."""
        full, part, fail = helpers.categorize_result(
            extract_ok=True, has_warns=False, apply_ok=True
        )
        assert (full, part, fail) == (1, 0, 0)

    def test_categorize_result_with_warns(self):
        """Test _categorize_result with warnings."""
        full, part, fail = helpers.categorize_result(
            extract_ok=True, has_warns=True, apply_ok=None
        )
        assert (full, part, fail) == (0, 1, 0)

    def test_get_status_icons_all_success(self, tmp_path):
        """Test status icons for complete success."""
        work = UnitOfWork(
            config=UserConfig(target_dir=tmp_path),
            input=tmp_path / "input.json",
            output=tmp_path / "output.json",
        )
        work.step_statuses[StepName.Extract] = StepStatus(step=StepName.Extract)
        work.step_statuses[StepName.Render] = StepStatus(step=StepName.Render)
        work.step_statuses[StepName.RoundtripComparer] = StepStatus(
            step=StepName.RoundtripComparer
        )
        icons = get_status_icons(work)
        assert icons[StepName.Extract] == "🟢"
        assert icons[StepName.Render] == "✅"
        assert icons[StepName.RoundtripComparer] == "✅"

    def test_get_status_icons_all_failures(self, tmp_path):
        """Test status icons for complete failure."""
        work = UnitOfWork(
            config=UserConfig(target_dir=tmp_path),
            input=tmp_path / "input.json",
            output=tmp_path / "output.json",
        )
        work.step_statuses[StepName.Extract] = StepStatus(
            step=StepName.Extract,
            errors=["extract error"],
        )
        work.step_statuses[StepName.Render] = StepStatus(
            step=StepName.Render,
            errors=["render error"],
        )
        work.step_statuses[StepName.RoundtripComparer] = StepStatus(
            step=StepName.RoundtripComparer,
            errors=["verify error"],
        )
        icons = get_status_icons(work)
        assert icons[StepName.Extract] == "❌"
        assert icons[StepName.Render] == "❌"
        assert icons[StepName.RoundtripComparer] == "❌"

    def test_get_status_icons_extract_warn(self, tmp_path):
        """Test status icons when extract has warning."""
        work = UnitOfWork(
            config=UserConfig(target_dir=tmp_path),
            input=tmp_path / "input.json",
            output=tmp_path / "output.json",
        )
        work.step_statuses[StepName.Extract] = StepStatus(
            step=StepName.Extract,
            warnings=["warn"],
        )
        icons = get_status_icons(work)
        assert icons[StepName.Extract] == "❎"
        assert icons[StepName.Render] == "➖"
        assert icons[StepName.RoundtripComparer] == "➖"

    def test_get_status_icons_none_values(self, tmp_path):
        """Test status icons with None values for apply/compare."""
        work = UnitOfWork(
            config=UserConfig(target_dir=tmp_path),
            input=tmp_path / "input.json",
            output=tmp_path / "output.json",
        )
        work.step_statuses[StepName.Extract] = StepStatus(step=StepName.Extract)
        icons = get_status_icons(work)
        assert icons[StepName.Extract] == "🟢"
        assert icons[StepName.Render] == "➖"
        assert icons[StepName.RoundtripComparer] == "➖"
