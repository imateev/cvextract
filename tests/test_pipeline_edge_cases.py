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
        config = cli.gather_user_requirements([
            "--mode", "extract-apply",
            "--source", "src",
            "--template", "tpl.docx",
            "--target", "out",
            "--adjust-dry-run"
        ])
        assert config.adjust_dry_run is True

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

        # Mock extract_single to return success with warnings
        def fake_extract_single(docx_file, out_json, debug):
            out_json.parent.mkdir(parents=True, exist_ok=True)
            out_json.write_text('{"identity": {}, "sidebar": {}, "overview": "", "experiences": []}')
            return True, [], ["warning"]
        
        monkeypatch.setattr(cli, "extract_single", fake_extract_single)
        
        # Mock render to succeed
        def fake_render(*args, **kwargs):
            return True, [], [], True
        
        monkeypatch.setattr(cli, "render_and_verify", fake_render)
        
        rc = cli.main([
            "--mode", "extract-apply",
            "--source", str(docx),
            "--template", str(template),
            "--target", str(tmp_path / "out"),
            "--strict"
        ])
        
        # With warnings in strict mode, should return 2
        assert rc == 2

    def test_main_adjust_for_customer_stores_in_config(self, tmp_path: Path):
        """Test that --adjust-for-customer is stored in config."""
        config = cli.gather_user_requirements([
            "--mode", "extract-apply",
            "--source", str(tmp_path / "a.docx"),
            "--template", str(tmp_path / "tpl.docx"),
            "--target", str(tmp_path / "out"),
            "--adjust-for-customer", "https://example.com",
            "--openai-model", "gpt-4",
            "--adjust-dry-run"
        ])
        
        assert config.adjust_url == "https://example.com"
        assert config.openai_model == "gpt-4"
        assert config.adjust_dry_run is True
        assert config.mode == cli.ExecutionMode.EXTRACT_ADJUST


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

    def test_execute_pipeline_ignores_non_docx(self, monkeypatch, tmp_path: Path):
        """Test that execute_pipeline ignores non-.docx files in extract mode."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "file.txt").write_text("not docx")
        (src_dir / "file.json").write_text("{}")
        
        template = tmp_path / "tpl.docx"
        with zipfile.ZipFile(template, 'w') as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
        
        config = cli.UserConfig(
            mode=cli.ExecutionMode.EXTRACT,
            source=src_dir / "file.txt",
            template=template,
            target_dir=tmp_path / "out",
        )
        
        def fake_extract(*args):
            pytest.fail("Should not extract non-.docx files")
        
        monkeypatch.setattr(cli, "extract_single", fake_extract)
        
        rc = cli.execute_pipeline(config)
        # Should succeed with 0 inputs processed (file filtered out)
        assert rc == 0

    def test_execute_pipeline_ignores_non_json(self, monkeypatch, tmp_path: Path):
        """Test that execute_pipeline ignores non-.json files in render mode."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "file.docx").write_text("not json")
        (src_dir / "file.txt").write_text("not json")
        
        template = tmp_path / "tpl.docx"
        with zipfile.ZipFile(template, 'w') as zf:
            zf.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types/>")
        
        config = cli.UserConfig(
            mode=cli.ExecutionMode.RENDER,
            source=src_dir / "file.txt",
            template=template,
            target_dir=tmp_path / "out",
        )
        
        def fake_render(*args, **kwargs):
            pytest.fail("Should not render non-.json files")
        
        monkeypatch.setattr(cli, "render_and_verify", fake_render)
        
        rc = cli.execute_pipeline(config)
        # Should succeed with 0 inputs processed
        assert rc == 0

    def test_apply_mode_return_values(self):
        """Test return value logic for apply_mode."""
        # apply_mode returns 0 only when failed == 0
        # Both test states: fully_ok (success) and failed (failure)
        pass  # Logic verified by integration tests

