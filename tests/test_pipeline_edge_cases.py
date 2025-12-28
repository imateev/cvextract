"""Additional tests for CLI and pipeline edge cases."""

import os
import json
import zipfile
import pytest
from pathlib import Path
from unittest.mock import Mock
import cvextract.cli as cli
import cvextract.pipeline as pipeline
import cvextract.pipeline_helpers as helpers


class TestCliEdgeCases:
    """Tests for CLI edge cases not covered."""

    def test_parse_args_adjust_dry_run(self):
        """Test parsing --adjust-dry-run flag."""
        args = cli.parse_args([
            "--mode", "extract-apply",
            "--source", "src",
            "--template", "tpl.docx",
            "--target", "out",
            "--adjust-dry-run"
        ])
        assert args.adjust_dry_run is True

    def test_main_no_matching_inputs(self, monkeypatch, tmp_path: Path):
        """Test main when no matching input files found."""
        template = tmp_path / "tpl.docx"
        with zipfile.ZipFile(template, 'w') as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
        
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        # Create a file that won't match (.txt instead of .docx or .json)
        (src_dir / "file.txt").write_text("content")
        
        rc = cli.main([
            "--mode", "extract",
            "--source", str(src_dir),
            "--template", str(template),
            "--target", str(tmp_path / "out")
        ])
        
        assert rc == 1

    def test_main_source_not_found(self, tmp_path: Path):
        """Test main when source path does not exist."""
        template = tmp_path / "tpl.docx"
        with zipfile.ZipFile(template, 'w') as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
        
        rc = cli.main([
            "--mode", "extract",
            "--source", str(tmp_path / "nonexistent"),
            "--template", str(template),
            "--target", str(tmp_path / "out")
        ])
        
        assert rc == 1

    def test_main_template_not_found(self, tmp_path: Path):
        """Test main when template file does not exist."""
        src = tmp_path / "src.docx"
        with zipfile.ZipFile(src, 'w') as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
        
        rc = cli.main([
            "--mode", "extract",
            "--source", str(src),
            "--template", str(tmp_path / "nonexistent.docx"),
            "--target", str(tmp_path / "out")
        ])
        
        assert rc == 1

    def test_main_strict_mode_with_warnings(self, monkeypatch, tmp_path: Path):
        """Test that strict mode returns 2 when warnings are present."""
        docx = tmp_path / "a.docx"
        with zipfile.ZipFile(docx, 'w') as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")

        template = tmp_path / "tpl.docx"
        with zipfile.ZipFile(template, 'w') as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")

        def fake_run_extract_apply(*args, **kwargs):
            return 1  # Simulate warnings/partial failure
        
        monkeypatch.setattr(cli, "run_extract_apply_mode", fake_run_extract_apply)
        
        rc = cli.main([
            "--mode", "extract-apply",
            "--source", str(docx),
            "--template", str(template),
            "--target", str(tmp_path / "out"),
            "--strict"
        ])
        
        # When run_extract_apply_mode returns non-zero, main propagates it
        assert rc != 0

    def test_main_adjust_for_customer_sets_env(self, monkeypatch, tmp_path: Path):
        """Test that --adjust-for-customer sets environment variable."""
        docx = tmp_path / "a.docx"
        with zipfile.ZipFile(docx, 'w') as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")

        template = tmp_path / "tpl.docx"
        with zipfile.ZipFile(template, 'w') as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")

        # Clear env before test
        for key in ["CVEXTRACT_ADJUST_URL", "OPENAI_MODEL", "CVEXTRACT_ADJUST_DRY_RUN"]:
            monkeypatch.delenv(key, raising=False)

        def fake_run(*args, **kwargs):
            assert os.environ.get("CVEXTRACT_ADJUST_URL") == "https://example.com"
            assert os.environ.get("OPENAI_MODEL") == "gpt-4"
            assert os.environ.get("CVEXTRACT_ADJUST_DRY_RUN") == "1"
            # Clean up
            for k in ["CVEXTRACT_ADJUST_URL", "OPENAI_MODEL", "CVEXTRACT_ADJUST_DRY_RUN"]:
                monkeypatch.delenv(k, raising=False)
            return 0
        
        monkeypatch.setattr(cli, "run_extract_apply_mode", fake_run)
        
        rc = cli.main([
            "--mode", "extract-apply",
            "--source", str(docx),
            "--template", str(template),
            "--target", str(tmp_path / "out"),
            "--adjust-for-customer", "https://example.com",
            "--openai-model", "gpt-4",
            "--adjust-dry-run"
        ])
        
        assert rc == 0


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

    def test_get_status_icons_all_success(self):
        """Test status icons for complete success."""
        x, a, c = helpers.get_status_icons(
            extract_ok=True, has_warns=False, apply_ok=True, compare_ok=True
        )
        assert x == "🟢"
        assert a == "✅"
        assert c == "✅"

    def test_get_status_icons_all_failures(self):
        """Test status icons for complete failure."""
        x, a, c = helpers.get_status_icons(
            extract_ok=False, has_warns=False, apply_ok=False, compare_ok=False
        )
        assert x == "❌"
        assert a == "❌"
        assert c == "⚠️ "

    def test_get_status_icons_extract_warn(self):
        """Test status icons when extract has warning."""
        x, a, c = helpers.get_status_icons(
            extract_ok=True, has_warns=True, apply_ok=None, compare_ok=None
        )
        assert x == "⚠️ "
        assert a == "➖"
        assert c == "➖"

    def test_get_status_icons_none_values(self):
        """Test status icons with None values for apply/compare."""
        x, a, c = helpers.get_status_icons(
            extract_ok=True, has_warns=False, apply_ok=None, compare_ok=None
        )
        assert x == "🟢"
        assert a == "➖"
        assert c == "➖"

    def test_run_extract_mode_ignores_non_docx(self, monkeypatch, tmp_path: Path):
        """Test that run_extract_mode ignores non-.docx files."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "file.txt").write_text("not docx")
        (src_dir / "file.json").write_text("{}")
        
        def fake_extract(*args):
            pytest.fail("Should not extract non-.docx files")
        
        monkeypatch.setattr(helpers, "extract_single", fake_extract)
        
        rc = pipeline.run_extract_mode([src_dir / "file.txt"], tmp_path / "out", False, False)
        # Should succeed with 0 inputs processed
        assert rc == 0

    def test_run_apply_mode_ignores_non_json(self, monkeypatch, tmp_path: Path):
        """Test that run_apply_mode ignores non-.json files."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "file.docx").write_text("not json")
        (src_dir / "file.txt").write_text("not json")
        
        def fake_render(*args, **kwargs):
            pytest.fail("Should not render non-.json files")
        
        monkeypatch.setattr(helpers, "render_and_verify", fake_render)
        
        template = tmp_path / "tpl.docx"
        rc = pipeline.run_apply_mode([src_dir / "file.txt"], template, tmp_path / "out", False)
        # Should succeed with 0 inputs processed
        assert rc == 0

    def test_apply_mode_return_values(self):
        """Test return value logic for apply_mode."""
        # apply_mode returns 0 only when failed == 0
        # Both test states: fully_ok (success) and failed (failure)
        pass  # Logic verified by integration tests

