"""Comprehensive tests to increase pipeline.py coverage above 91%."""

import pytest
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from cvextract.pipeline import (
    safe_relpath,
    infer_source_root,
    _extract_single,
    _render_and_verify,
    _get_status_icons,
    _categorize_result,
    run_extract_mode,
    run_extract_apply_mode,
    run_apply_mode,
)
from cvextract.shared import VerificationResult


class TestSafeRelpath:
    """Tests for safe_relpath exception handling."""

    def test_safe_relpath_exception_handling(self):
        """Test safe_relpath falls back to p.name when relative_to() raises ValueError."""
        # Create paths that cannot be relative to each other
        p = Path("/some/absolute/path/to/file.txt")
        root = Path("/different/root/path")
        
        # This should trigger the exception path and return just the name
        result = safe_relpath(p, root)
        assert result == "file.txt"


class TestGetStatusIconsComplete:
    """Complete test coverage for _get_status_icons combinations."""

    def test_extract_ok_with_warnings_no_apply_compare(self):
        """Extract OK + warnings → ⚠️ ➖➖"""
        x_icon, a_icon, c_icon = _get_status_icons(
            extract_ok=True, has_warns=True, apply_ok=None, compare_ok=None
        )
        assert "⚠️" in x_icon
        assert a_icon == "➖"
        assert c_icon == "➖"

    def test_extract_ok_no_warnings_no_apply_compare(self):
        """Extract OK no warnings → 🟢➖➖"""
        x_icon, a_icon, c_icon = _get_status_icons(
            extract_ok=True, has_warns=False, apply_ok=None, compare_ok=None
        )
        assert x_icon == "🟢"
        assert a_icon == "➖"
        assert c_icon == "➖"

    def test_extract_failed(self):
        """Extract failed → ❌➖➖"""
        x_icon, a_icon, c_icon = _get_status_icons(
            extract_ok=False, has_warns=False, apply_ok=None, compare_ok=None
        )
        assert x_icon == "❌"
        assert a_icon == "➖"
        assert c_icon == "➖"

    def test_with_apply_ok_true(self):
        """With apply_ok=True → second icon ✅"""
        x_icon, a_icon, c_icon = _get_status_icons(
            extract_ok=True, has_warns=False, apply_ok=True, compare_ok=None
        )
        assert a_icon == "✅"

    def test_with_apply_ok_false(self):
        """With apply_ok=False → second icon ❌"""
        x_icon, a_icon, c_icon = _get_status_icons(
            extract_ok=True, has_warns=False, apply_ok=False, compare_ok=None
        )
        assert a_icon == "❌"

    def test_with_compare_ok_true(self):
        """With compare_ok=True → third icon ✅"""
        x_icon, a_icon, c_icon = _get_status_icons(
            extract_ok=True, has_warns=False, apply_ok=True, compare_ok=True
        )
        assert c_icon == "✅"

    def test_with_compare_ok_false(self):
        """With compare_ok=False → third icon ⚠️"""
        x_icon, a_icon, c_icon = _get_status_icons(
            extract_ok=True, has_warns=False, apply_ok=True, compare_ok=False
        )
        assert "⚠️" in c_icon


class TestCategorizeResultComplete:
    """Complete test coverage for _categorize_result all paths."""

    def test_extract_ok_false(self):
        """extract_ok=False → (0, 0, 1)"""
        full, part, fail = _categorize_result(
            extract_ok=False, has_warns=False, apply_ok=None
        )
        assert (full, part, fail) == (0, 0, 1)

    def test_extract_ok_apply_ok_false(self):
        """extract_ok=True, apply_ok=False → (0, 1, 0)"""
        full, part, fail = _categorize_result(
            extract_ok=True, has_warns=False, apply_ok=False
        )
        assert (full, part, fail) == (0, 1, 0)

    def test_extract_ok_apply_none_has_warns(self):
        """extract_ok=True, apply_ok=None, has_warns=True → (0, 1, 0)"""
        full, part, fail = _categorize_result(
            extract_ok=True, has_warns=True, apply_ok=None
        )
        assert (full, part, fail) == (0, 1, 0)

    def test_extract_ok_has_warns_apply_ok_true(self):
        """extract_ok=True, has_warns=True, apply_ok=True → (0, 1, 0)"""
        full, part, fail = _categorize_result(
            extract_ok=True, has_warns=True, apply_ok=True
        )
        assert (full, part, fail) == (0, 1, 0)

    def test_extract_ok_no_warns_apply_ok_true(self):
        """extract_ok=True, has_warns=False, apply_ok=True → (1, 0, 0)"""
        full, part, fail = _categorize_result(
            extract_ok=True, has_warns=False, apply_ok=True
        )
        assert (full, part, fail) == (1, 0, 0)


class TestRenderAndVerifyComplete:
    """Complete test coverage for _render_and_verify scenarios."""

    def test_cleanup_when_debug_false_no_roundtrip_dir(self, tmp_path):
        """Test cleanup logic when debug=False and roundtrip_dir is None."""
        json_path = tmp_path / "test.json"
        template_path = tmp_path / "template.docx"
        out_dir = tmp_path / "out"
        
        test_data = {"identity": {"title": "T"}, "sidebar": {}, "overview": "", "experiences": []}
        json_path.write_text(json.dumps(test_data))
        template_path.touch()
        out_dir.mkdir()
        
        rendered_docx = out_dir / "test.docx"
        roundtrip_json = rendered_docx.with_suffix(".json")
        
        with patch("cvextract.pipeline.render_from_json") as mock_render, \
             patch("cvextract.pipeline.process_single_docx") as mock_process, \
             patch("cvextract.pipeline.compare_data_structures") as mock_compare:
            
            mock_render.return_value = rendered_docx
            mock_process.return_value = test_data
            mock_compare.return_value = VerificationResult(ok=True, errors=[], warnings=[])
            
            ok, errors, warns, compare_ok = _render_and_verify(
                json_path, template_path, out_dir, debug=False, roundtrip_dir=None
            )
            
            assert ok is True
            # Verify cleanup was attempted (roundtrip_json should not persist)
            # Since we're mocking, we can't verify the actual file deletion
            # but we can verify the function completed successfully

    def test_exception_with_debug_true(self, tmp_path):
        """Test exception handling when debug=True logs traceback."""
        json_path = tmp_path / "test.json"
        template_path = tmp_path / "template.docx"
        out_dir = tmp_path / "out"
        
        json_path.write_text(json.dumps({}))
        template_path.touch()
        
        with patch("cvextract.pipeline.render_from_json") as mock_render, \
             patch("cvextract.pipeline.LOG.error") as mock_log_error:
            
            mock_render.side_effect = RuntimeError("Test error")
            
            ok, errors, warns, compare_ok = _render_and_verify(
                json_path, template_path, out_dir, debug=True
            )
            
            assert ok is False
            assert any("RuntimeError" in e for e in errors)
            assert compare_ok is None
            # Verify that LOG.error was called (traceback logging)
            assert mock_log_error.called


class TestRunExtractModeComplete:
    """Complete test coverage for run_extract_mode edge cases."""

    def test_extract_with_warnings(self, tmp_path):
        """Test extract with warnings increases partial_ok count."""
        docx_file = tmp_path / "test.docx"
        target_dir = tmp_path / "output"
        docx_file.touch()
        
        with patch("cvextract.pipeline._extract_single") as mock_extract:
            # Return success with warnings
            mock_extract.return_value = (True, [], ["warning message"])
            
            rc = run_extract_mode([docx_file], target_dir, strict=False, debug=False)
            
            # Should return 0 because there are no failures
            assert rc == 0

    def test_mixed_success_warning_failure(self, tmp_path):
        """Test mixed success/warning/failure files."""
        docx1 = tmp_path / "success.docx"
        docx2 = tmp_path / "warning.docx"
        docx3 = tmp_path / "failure.docx"
        docx1.touch()
        docx2.touch()
        docx3.touch()
        target_dir = tmp_path / "output"
        
        call_log = []
        
        with patch("cvextract.pipeline._extract_single") as mock_extract:
            # Different results for different files
            def side_effect(docx_path, out_json, *args, **kwargs):
                # Create the JSON file so the function can proceed
                out_json.parent.mkdir(parents=True, exist_ok=True)
                out_json.write_text("{}")
                path_str = str(docx_path.name)  # Use .name to get just the filename
                if "success" in path_str:
                    call_log.append(("success", True, [], []))
                    return (True, [], [])
                elif "warning" in path_str:
                    call_log.append(("warning", True, [], ["warning"]))
                    return (True, [], ["warning"])
                else:
                    call_log.append(("failure", False, ["error"], []))
                    return (False, ["error"], [])
            
            mock_extract.side_effect = side_effect
            
            rc = run_extract_mode([docx1, docx2, docx3], target_dir, strict=False, debug=False)
            
            # Should return 1 because there's at least one failure
            assert rc == 1


class TestRunExtractApplyModeComplete:
    """Complete test coverage for run_extract_apply_mode."""

    def test_customer_adjustment_from_env(self, monkeypatch, tmp_path):
        """Test customer adjustment using environment variable."""
        docx_file = tmp_path / "test.docx"
        template_path = tmp_path / "template.docx"
        target_dir = tmp_path / "output"
        docx_file.touch()
        template_path.touch()
        
        # Set environment variables
        monkeypatch.setenv("CVEXTRACT_ADJUST_URL", "https://example.com")
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4")
        
        test_data = {"identity": {"title": "T"}, "sidebar": {}, "overview": "", "experiences": []}
        adjusted_data = {"identity": {"title": "T Adjusted"}, "sidebar": {}, "overview": "", "experiences": []}
        
        with patch("cvextract.pipeline._extract_single") as mock_extract, \
             patch("cvextract.pipeline._render_and_verify") as mock_render, \
             patch("cvextract.pipeline.adjust_for_customer") as mock_adjust:
            
            # Mock extract to create the JSON file
            def extract_side_effect(docx_path, out_json, *args):
                out_json.parent.mkdir(parents=True, exist_ok=True)
                out_json.write_text(json.dumps(test_data))
                return (True, [], [])
            
            mock_extract.side_effect = extract_side_effect
            mock_render.return_value = (True, [], [], True)
            mock_adjust.return_value = adjusted_data
            
            rc = run_extract_apply_mode(
                [docx_file], template_path, target_dir, strict=False, debug=False
            )
            
            # Verify adjust_for_customer was called
            assert mock_adjust.called
            assert rc == 0

    def test_adjustment_exception_handling(self, tmp_path):
        """Test adjustment exception handling - falls back to original JSON."""
        docx_file = tmp_path / "test.docx"
        template_path = tmp_path / "template.docx"
        target_dir = tmp_path / "output"
        docx_file.touch()
        template_path.touch()
        
        test_data = {"identity": {"title": "T"}, "sidebar": {}, "overview": "", "experiences": []}
        
        with patch("cvextract.pipeline._extract_single") as mock_extract, \
             patch("cvextract.pipeline._render_and_verify") as mock_render, \
             patch("cvextract.pipeline.adjust_for_customer") as mock_adjust:
            
            mock_extract.return_value = (True, [], [])
            mock_render.return_value = (True, [], [], True)
            # Simulate adjustment failure
            mock_adjust.side_effect = Exception("Adjustment failed")
            
            rc = run_extract_apply_mode(
                [docx_file], template_path, target_dir, 
                strict=False, debug=False, adjust_url="https://example.com"
            )
            
            # Should still complete successfully using original JSON
            assert mock_render.called
            # Check that skip_compare was set to False (fallback behavior)
            call_kwargs = mock_render.call_args[1]
            assert call_kwargs.get("skip_compare") == False

    def test_skip_compare_when_adjusted_json_differs(self, tmp_path):
        """Test skip_compare logic when adjusted JSON differs from original."""
        docx_file = tmp_path / "test.docx"
        template_path = tmp_path / "template.docx"
        target_dir = tmp_path / "output"
        docx_file.touch()
        template_path.touch()
        
        test_data = {"identity": {"title": "T"}, "sidebar": {}, "overview": "", "experiences": []}
        adjusted_data = {"identity": {"title": "T Adjusted"}, "sidebar": {}, "overview": "", "experiences": []}
        
        with patch("cvextract.pipeline._extract_single") as mock_extract, \
             patch("cvextract.pipeline._render_and_verify") as mock_render, \
             patch("cvextract.pipeline.adjust_for_customer") as mock_adjust:
            
            # Mock extract to create the JSON file
            def extract_side_effect(docx_path, out_json, *args):
                out_json.parent.mkdir(parents=True, exist_ok=True)
                out_json.write_text(json.dumps(test_data))
                return (True, [], [])
            
            mock_extract.side_effect = extract_side_effect
            mock_render.return_value = (True, [], [], None)
            mock_adjust.return_value = adjusted_data
            
            rc = run_extract_apply_mode(
                [docx_file], template_path, target_dir,
                strict=False, debug=False, adjust_url="https://example.com"
            )
            
            # Verify skip_compare was set to True because data differs
            call_kwargs = mock_render.call_args[1]
            assert call_kwargs.get("skip_compare") == True

    def test_dry_run_mode_with_adjustment(self, monkeypatch, tmp_path):
        """Test dry-run mode with adjustment skips rendering."""
        docx_file = tmp_path / "test.docx"
        template_path = tmp_path / "template.docx"
        target_dir = tmp_path / "output"
        docx_file.touch()
        template_path.touch()
        
        # Set dry-run environment variable
        monkeypatch.setenv("CVEXTRACT_ADJUST_DRY_RUN", "1")
        
        test_data = {"identity": {"title": "T"}, "sidebar": {}, "overview": "", "experiences": []}
        adjusted_data = {"identity": {"title": "T Adjusted"}, "sidebar": {}, "overview": "", "experiences": []}
        
        with patch("cvextract.pipeline._extract_single") as mock_extract, \
             patch("cvextract.pipeline._render_and_verify") as mock_render, \
             patch("cvextract.pipeline.adjust_for_customer") as mock_adjust:
            
            mock_extract.return_value = (True, [], [])
            mock_adjust.return_value = adjusted_data
            
            rc = run_extract_apply_mode(
                [docx_file], template_path, target_dir,
                strict=False, debug=False, adjust_url="https://example.com"
            )
            
            # Verify render was NOT called in dry-run mode
            assert not mock_render.called

    def test_strict_mode_with_warnings_returns_2(self, tmp_path):
        """Test strict mode with warnings returns exit code 2."""
        docx_file = tmp_path / "test.docx"
        template_path = tmp_path / "template.docx"
        target_dir = tmp_path / "output"
        docx_file.touch()
        template_path.touch()
        
        with patch("cvextract.pipeline._extract_single") as mock_extract, \
             patch("cvextract.pipeline._render_and_verify") as mock_render:
            
            # Return success with warnings
            mock_extract.return_value = (True, [], ["warning"])
            mock_render.return_value = (True, [], [], True)
            
            rc = run_extract_apply_mode(
                [docx_file], template_path, target_dir, strict=True, debug=False
            )
            
            # Strict mode should return 2 when there are warnings
            assert rc == 2

    def test_extract_failure_skips_rendering(self, tmp_path):
        """Test extract failure path where rendering is skipped."""
        docx_file = tmp_path / "test.docx"
        template_path = tmp_path / "template.docx"
        target_dir = tmp_path / "output"
        docx_file.touch()
        template_path.touch()
        
        with patch("cvextract.pipeline._extract_single") as mock_extract, \
             patch("cvextract.pipeline._render_and_verify") as mock_render:
            
            # Simulate extraction failure
            mock_extract.return_value = (False, ["extraction error"], [])
            
            rc = run_extract_apply_mode(
                [docx_file], template_path, target_dir, strict=False, debug=False
            )
            
            # Verify rendering was NOT called when extraction failed
            assert not mock_render.called

    def test_combined_warnings_from_extract_and_apply(self, tmp_path):
        """Test combined warnings from extract and apply."""
        docx_file = tmp_path / "test.docx"
        template_path = tmp_path / "template.docx"
        target_dir = tmp_path / "output"
        docx_file.touch()
        template_path.touch()
        
        with patch("cvextract.pipeline._extract_single") as mock_extract, \
             patch("cvextract.pipeline._render_and_verify") as mock_render:
            
            # Both extract and apply return warnings
            mock_extract.return_value = (True, [], ["extract warning"])
            mock_render.return_value = (True, [], ["apply warning"], True)
            
            rc = run_extract_apply_mode(
                [docx_file], template_path, target_dir, strict=False, debug=False
            )
            
            # Should succeed but have warnings
            assert rc == 1  # partial_ok > 0, so returns 1


class TestRunApplyModeComplete:
    """Complete test coverage for run_apply_mode."""

    def test_customer_adjustment_from_env(self, monkeypatch, tmp_path):
        """Test customer adjustment from environment variable."""
        json_file = tmp_path / "test.json"
        template_path = tmp_path / "template.docx"
        target_dir = tmp_path / "output"
        
        test_data = {"identity": {"title": "T"}, "sidebar": {}, "overview": "", "experiences": []}
        json_file.write_text(json.dumps(test_data))
        template_path.touch()
        
        # Set environment variables
        monkeypatch.setenv("CVEXTRACT_ADJUST_URL", "https://example.com")
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4")
        
        adjusted_data = {"identity": {"title": "T Adjusted"}, "sidebar": {}, "overview": "", "experiences": []}
        
        with patch("cvextract.pipeline._render_and_verify") as mock_render, \
             patch("cvextract.pipeline.adjust_for_customer") as mock_adjust:
            
            mock_render.return_value = (True, [], [], True)
            mock_adjust.return_value = adjusted_data
            
            rc = run_apply_mode([json_file], template_path, target_dir, debug=False)
            
            # Verify adjust_for_customer was called
            assert mock_adjust.called
            assert rc == 0

    def test_adjustment_exception_handling(self, tmp_path):
        """Test adjustment exception handling - falls back to original JSON."""
        json_file = tmp_path / "test.json"
        template_path = tmp_path / "template.docx"
        target_dir = tmp_path / "output"
        
        test_data = {"identity": {"title": "T"}, "sidebar": {}, "overview": "", "experiences": []}
        json_file.write_text(json.dumps(test_data))
        template_path.touch()
        
        with patch("cvextract.pipeline._render_and_verify") as mock_render, \
             patch("cvextract.pipeline.adjust_for_customer") as mock_adjust:
            
            mock_render.return_value = (True, [], [], True)
            # Simulate adjustment failure
            mock_adjust.side_effect = Exception("Adjustment failed")
            
            rc = run_apply_mode(
                [json_file], template_path, target_dir,
                debug=False, adjust_url="https://example.com"
            )
            
            # Should still complete successfully using original JSON
            assert mock_render.called
            # Verify skip_compare was set to False (fallback)
            call_kwargs = mock_render.call_args[1]
            assert call_kwargs.get("skip_compare") == False

    def test_dry_run_mode(self, monkeypatch, tmp_path):
        """Test dry-run mode skips rendering."""
        json_file = tmp_path / "test.json"
        template_path = tmp_path / "template.docx"
        target_dir = tmp_path / "output"
        
        test_data = {"identity": {"title": "T"}, "sidebar": {}, "overview": "", "experiences": []}
        json_file.write_text(json.dumps(test_data))
        template_path.touch()
        
        # Set dry-run environment variable
        monkeypatch.setenv("CVEXTRACT_ADJUST_DRY_RUN", "1")
        
        adjusted_data = {"identity": {"title": "T Adjusted"}, "sidebar": {}, "overview": "", "experiences": []}
        
        with patch("cvextract.pipeline._render_and_verify") as mock_render, \
             patch("cvextract.pipeline.adjust_for_customer") as mock_adjust:
            
            mock_adjust.return_value = adjusted_data
            
            rc = run_apply_mode(
                [json_file], template_path, target_dir,
                debug=False, adjust_url="https://example.com"
            )
            
            # Verify render was NOT called in dry-run mode
            assert not mock_render.called

    def test_apply_warnings_handling(self, tmp_path):
        """Test apply warnings handling."""
        json_file = tmp_path / "test.json"
        template_path = tmp_path / "template.docx"
        target_dir = tmp_path / "output"
        
        test_data = {"identity": {"title": "T"}, "sidebar": {}, "overview": "", "experiences": []}
        json_file.write_text(json.dumps(test_data))
        template_path.touch()
        
        with patch("cvextract.pipeline._render_and_verify") as mock_render:
            # Return success with warnings
            mock_render.return_value = (True, [], ["apply warning"], True)
            
            rc = run_apply_mode([json_file], template_path, target_dir, debug=False)
            
            # Should succeed
            assert rc == 0

    def test_success_vs_failure_categorization(self, tmp_path):
        """Test mixed success/failure scenarios."""
        json1 = tmp_path / "success.json"
        json2 = tmp_path / "failure.json"
        template_path = tmp_path / "template.docx"
        target_dir = tmp_path / "output"
        
        test_data = {"identity": {"title": "T"}, "sidebar": {}, "overview": "", "experiences": []}
        json1.write_text(json.dumps(test_data))
        json2.write_text(json.dumps(test_data))
        template_path.touch()
        
        with patch("cvextract.pipeline._render_and_verify") as mock_render:
            # Different results for different files
            def side_effect(render_json, *args, **kwargs):
                # Use .name to get just the filename
                if "success" in str(render_json.name):
                    return (True, [], [], True)
                else:
                    return (False, ["render error"], [], None)
            
            mock_render.side_effect = side_effect
            
            rc = run_apply_mode([json1, json2], template_path, target_dir, debug=False)
            
            # Should return 1 because there's at least one failure
            assert rc == 1
