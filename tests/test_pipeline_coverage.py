"""Tests for improved coverage of pipeline module critical paths."""

import json
from unittest.mock import patch, MagicMock
from cvextract.pipeline_helpers import (
    extract_single,
    categorize_result,
    get_status_icons,
    render_and_verify,
    infer_source_root,
)
from cvextract.run_input import RunInput
from cvextract.verifiers import get_verifier
from cvextract.shared import VerificationResult


class TestExtractSingle:
    """Tests for extract_single function."""

    def testextract_single_success(self, tmp_path):
        """Test successful extraction."""
        docx_path = tmp_path / "test.docx"
        out_json = tmp_path / "out.json"
        docx_path.touch()
        
        # Mock the extraction pipeline
        mock_data = {
            "identity": {"title": "Engineer", "full_name": "John Doe", "first_name": "John", "last_name": "Doe"},
            "sidebar": {"languages": ["EN"]},
            "overview": "Text",
            "experiences": [{"heading": "Job", "description": "Work", "bullets": ["Item"]}],
        }
        
        mock_verifier = MagicMock()
        mock_verifier.verify.return_value = VerificationResult(ok=True, errors=[], warnings=[])
        
        with patch("cvextract.pipeline_helpers.process_single_docx") as mock_extract, \
             patch("cvextract.pipeline_helpers.get_verifier") as mock_get_verifier:
            
            mock_extract.return_value = mock_data
            mock_get_verifier.return_value = mock_verifier
            
            ok, errors, warnings, run_input = extract_single(docx_path, out_json, debug=False)
            
            assert ok is True
            assert errors == []
            assert warnings == []
            assert isinstance(run_input, RunInput)
            assert run_input.extracted_json_path == out_json

    def testextract_single_invalid_data(self, tmp_path):
        """Test verification failure with invalid data."""
        docx_path = tmp_path / "test.docx"
        out_json = tmp_path / "out.json"
        docx_path.touch()
        
        mock_data = {"identity": {}}  # Missing required fields
        
        with patch("cvextract.pipeline_helpers.process_single_docx") as mock_extract:
            
            mock_extract.return_value = mock_data
            
            ok, errors, warnings, run_input = extract_single(docx_path, out_json, debug=False)
            
            # The actual verifier will catch these errors
            assert ok is False
            # Check that there are errors for missing fields
            assert len(errors) > 0

    def testextract_single_exception_no_debug(self, tmp_path):
        """Test exception handling without debug mode."""
        docx_path = tmp_path / "test.docx"
        out_json = tmp_path / "out.json"
        docx_path.touch()
        
        with patch("cvextract.pipeline_helpers.process_single_docx") as mock_extract:
            mock_extract.side_effect = ValueError("Bad file")
            
            ok, errors, warnings, run_input = extract_single(docx_path, out_json, debug=False)
            
            assert ok is False
            assert any("exception" in e.lower() or "ValueError" in e for e in errors)

    def testextract_single_exception_with_debug(self, tmp_path):
        """Test exception logging with debug mode enabled."""
        docx_path = tmp_path / "test.docx"
        out_json = tmp_path / "out.json"
        docx_path.touch()
        
        with patch("cvextract.pipeline_helpers.process_single_docx") as mock_extract, \
             patch("cvextract.pipeline_helpers.dump_body_sample"):
            
            mock_extract.side_effect = ValueError("Bad file")
            
            ok, errors, warnings, run_input = extract_single(docx_path, out_json, debug=True)
            
            assert ok is False

    def testextract_single_with_warnings(self, tmp_path):
        """Test that warnings are preserved."""
        docx_path = tmp_path / "test.docx"
        out_json = tmp_path / "out.json"
        docx_path.touch()
        
        mock_data = {
            "identity": {"title": "T", "full_name": "A B", "first_name": "A", "last_name": "B"},
            "sidebar": {"languages": ["EN"]},
            "overview": "Text",
            "experiences": [],
        }
        
        mock_verifier = MagicMock()
        mock_verifier.verify.return_value = VerificationResult(
            ok=True,
            errors=[],
            warnings=["Warning message"]
        )
        
        with patch("cvextract.pipeline_helpers.process_single_docx") as mock_extract, \
             patch("cvextract.pipeline_helpers.get_verifier") as mock_get_verifier:
            
            mock_extract.return_value = mock_data
            mock_get_verifier.return_value = mock_verifier
            
            ok, errors, warnings, run_input = extract_single(docx_path, out_json, debug=False)
            
            assert ok is True
            assert "Warning message" in warnings


class TestRenderAndVerify:
    """Tests for render_and_verify function."""

    def testrender_and_verify_success(self, tmp_path):
        """Test successful render and verify."""
        json_path = tmp_path / "test.json"
        template_path = tmp_path / "template.docx"
        out_dir = tmp_path / "out"
        
        json_path.write_text(json.dumps({
            "identity": {"title": "T", "full_name": "A B", "first_name": "A", "last_name": "B"},
            "sidebar": {},
            "overview": "",
            "experiences": [],
        }))
        template_path.touch()
        
        # Create RunInput with extracted_json_path set
        run_input = RunInput(file_path=tmp_path / "source.docx", extracted_json_path=json_path)
        rendered_docx = out_dir / "test_NEW.docx"
        
        mock_verifier = MagicMock()
        mock_verifier.verify.return_value = VerificationResult(ok=True, errors=[], warnings=[])
        
        with patch("cvextract.pipeline_helpers.render_cv_data") as mock_render, \
             patch("cvextract.pipeline_helpers.process_single_docx") as mock_process, \
             patch("cvextract.pipeline_helpers.get_verifier") as mock_get_verifier:
            
            mock_render.return_value = rendered_docx
            mock_process.return_value = json.loads(json_path.read_text())
            mock_get_verifier.return_value = mock_verifier
            
            ok, errors, warns, compare_ok, updated_run_input = render_and_verify(
                run_input, template_path, rendered_docx, debug=False
            )
            
            assert ok is True
            assert errors == []
            assert compare_ok is True
            assert isinstance(updated_run_input, RunInput)
            assert updated_run_input.rendered_docx_path == rendered_docx

    def testrender_and_verify_skip_compare(self, tmp_path):
        """Test skip_compare parameter."""
        json_path = tmp_path / "test.json"
        template_path = tmp_path / "template.docx"
        out_dir = tmp_path / "out"
        
        json_path.write_text(json.dumps({
            "identity": {"title": "T", "full_name": "A B", "first_name": "A", "last_name": "B"},
            "sidebar": {},
            "overview": "",
            "experiences": [],
        }))
        template_path.touch()
        
        # Create RunInput with extracted_json_path set
        run_input = RunInput(file_path=tmp_path / "source.docx", extracted_json_path=json_path)
        rendered_docx = out_dir / "test_NEW.docx"
        
        with patch("cvextract.pipeline_helpers.render_cv_data") as mock_render:
            mock_render.return_value = rendered_docx
            
            ok, errors, warns, compare_ok, updated_run_input = render_and_verify(
                run_input, template_path, rendered_docx, debug=False, skip_compare=True
            )
            
            assert ok is True
            assert compare_ok is None  # Not executed
            assert isinstance(updated_run_input, RunInput)

    def testrender_and_verify_with_roundtrip_dir(self, tmp_path):
        """Test roundtrip_dir parameter."""
        json_path = tmp_path / "test.json"
        template_path = tmp_path / "template.docx"
        out_dir = tmp_path / "out"
        roundtrip_dir = tmp_path / "roundtrip"
        
        test_data = {
            "identity": {"title": "T", "full_name": "A B", "first_name": "A", "last_name": "B"},
            "sidebar": {},
            "overview": "",
            "experiences": [],
        }
        json_path.write_text(json.dumps(test_data))
        template_path.touch()
        
        # Create RunInput with extracted_json_path set
        run_input = RunInput(file_path=tmp_path / "source.docx", extracted_json_path=json_path)
        rendered_docx = out_dir / "test_NEW.docx"
        
        mock_verifier = MagicMock()
        mock_verifier.verify.return_value = VerificationResult(ok=True, errors=[], warnings=[])
        
        with patch("cvextract.pipeline_helpers.render_cv_data") as mock_render, \
             patch("cvextract.pipeline_helpers.process_single_docx") as mock_process, \
             patch("cvextract.pipeline_helpers.get_verifier") as mock_get_verifier:
            
            mock_render.return_value = rendered_docx
            mock_process.return_value = test_data
            mock_get_verifier.return_value = mock_verifier
            
            ok, errors, warns, compare_ok, updated_run_input = render_and_verify(
                run_input, template_path, rendered_docx, debug=False,
                roundtrip_dir=roundtrip_dir
            )
            
            assert ok is True
            # Verify roundtrip_dir was created
            assert roundtrip_dir.exists()

    def testrender_and_verify_compare_failure(self, tmp_path):
        """Test when comparison finds differences."""
        json_path = tmp_path / "test.json"
        template_path = tmp_path / "template.docx"
        out_dir = tmp_path / "out"
        
        json_path.write_text(json.dumps({
            "identity": {"title": "T", "full_name": "A B", "first_name": "A", "last_name": "B"},
            "sidebar": {},
            "overview": "",
            "experiences": [],
        }))
        template_path.touch()
        
        # Create RunInput with extracted_json_path set
        run_input = RunInput(file_path=tmp_path / "source.docx", extracted_json_path=json_path)
        rendered_docx = out_dir / "test_NEW.docx"
        
        mock_verifier = MagicMock()
        mock_verifier.verify.return_value = VerificationResult(
            ok=False,
            errors=["Mismatch detected"],
            warnings=[]
        )
        
        with patch("cvextract.pipeline_helpers.render_cv_data") as mock_render, \
             patch("cvextract.pipeline_helpers.process_single_docx") as mock_process, \
             patch("cvextract.pipeline_helpers.get_verifier") as mock_get_verifier:
            
            mock_render.return_value = rendered_docx
            mock_process.return_value = {"identity": {"title": "Different"}, "sidebar": {}, "overview": "", "experiences": []}
            mock_get_verifier.return_value = mock_verifier
            
            ok, errors, warns, compare_ok, updated_run_input = render_and_verify(
                run_input, template_path, rendered_docx, debug=False
            )
            
            assert ok is False
            assert "Mismatch detected" in errors
            assert compare_ok is False

    def testrender_and_verify_render_exception(self, tmp_path):
        """Test exception during rendering."""
        json_path = tmp_path / "test.json"
        template_path = tmp_path / "template.docx"
        out_dir = tmp_path / "out"
        
        json_path.write_text(json.dumps({}))
        template_path.touch()
        
        # Create RunInput with extracted_json_path set
        run_input = RunInput(file_path=tmp_path / "source.docx", extracted_json_path=json_path)
        rendered_docx = out_dir / "test_NEW.docx"
        
        with patch("cvextract.pipeline_helpers.render_cv_data") as mock_render:
            mock_render.side_effect = RuntimeError("Render failed")
            
            ok, errors, warns, compare_ok, updated_run_input = render_and_verify(
                run_input, template_path, rendered_docx, debug=False
            )
            
            assert ok is False
            assert any("RuntimeError" in e for e in errors)
            assert compare_ok is None


class TestCategorizeResult:
    """Tests for categorize_result function."""

    def test_categorize_extract_failed(self):
        """Test when extraction failed."""
        fully_ok, partial_ok, failed = categorize_result(extract_ok=False, has_warns=False, apply_ok=None)
        assert (fully_ok, partial_ok, failed) == (0, 0, 1)

    def test_categorize_apply_failed(self):
        """Test when apply failed."""
        fully_ok, partial_ok, failed = categorize_result(extract_ok=True, has_warns=False, apply_ok=False)
        assert (fully_ok, partial_ok, failed) == (0, 1, 0)

    def test_categorize_with_warnings(self):
        """Test when result has warnings."""
        fully_ok, partial_ok, failed = categorize_result(extract_ok=True, has_warns=True, apply_ok=True)
        assert (fully_ok, partial_ok, failed) == (0, 1, 0)

    def test_categorize_fully_ok(self):
        """Test fully successful result."""
        fully_ok, partial_ok, failed = categorize_result(extract_ok=True, has_warns=False, apply_ok=True)
        assert (fully_ok, partial_ok, failed) == (1, 0, 0)

    def test_categorize_apply_none_with_warns(self):
        """Test when apply is None but has warnings."""
        fully_ok, partial_ok, failed = categorize_result(extract_ok=True, has_warns=True, apply_ok=None)
        assert (fully_ok, partial_ok, failed) == (0, 1, 0)


class TestGetStatusIcons:
    """Tests for get_status_icons function."""

    def test_extract_ok_with_warnings(self):
        """Test extract ok but with warnings."""
        x_icon, a_icon, c_icon = get_status_icons(extract_ok=True, has_warns=True, apply_ok=True, compare_ok=True)
        assert "⚠️" in x_icon  # Warning icon for extract

    def test_extract_ok_no_warnings(self):
        """Test extract ok without warnings."""
        x_icon, a_icon, c_icon = get_status_icons(extract_ok=True, has_warns=False, apply_ok=True, compare_ok=True)
        assert "🟢" in x_icon  # Green icon

    def test_extract_failed(self):
        """Test extract failed."""
        x_icon, a_icon, c_icon = get_status_icons(extract_ok=False, has_warns=False, apply_ok=False, compare_ok=False)
        assert "❌" in x_icon  # Fail icon

    def test_apply_none(self):
        """Test apply not executed."""
        x_icon, a_icon, c_icon = get_status_icons(extract_ok=True, has_warns=False, apply_ok=None, compare_ok=None)
        assert "➖" in a_icon  # Neutral icon for apply

    def test_compare_ok(self):
        """Test compare successful."""
        x_icon, a_icon, c_icon = get_status_icons(extract_ok=True, has_warns=False, apply_ok=True, compare_ok=True)
        assert "✅" in c_icon or "✓" in c_icon

    def test_compare_failed(self):
        """Test compare found differences."""
        x_icon, a_icon, c_icon = get_status_icons(extract_ok=True, has_warns=False, apply_ok=True, compare_ok=False)
        assert "⚠️" in c_icon  # Warning for compare mismatch

    def test_compare_none(self):
        """Test compare not executed."""
        x_icon, a_icon, c_icon = get_status_icons(extract_ok=True, has_warns=False, apply_ok=True, compare_ok=None)
        assert "➖" in c_icon


class TestInferSourceRoot:
    """Tests for infer_source_root function."""

    def test_infer_from_single_file(self, tmp_path):
        """Test inferring root from single JSON file."""
        json_file = tmp_path / "data.json"
        json_file.touch()
        
        root = infer_source_root([json_file])
        assert root == tmp_path

    def test_infer_from_nested_files(self, tmp_path):
        """Test inferring root from nested JSON files."""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()
        
        file1 = dir1 / "data1.json"
        file2 = dir2 / "data2.json"
        file1.touch()
        file2.touch()
        
        root = infer_source_root([file1, file2])
        assert root == tmp_path

    def test_infer_with_deeply_nested_files(self, tmp_path):
        """Test inferring root with deeply nested files."""
        deep_dir = tmp_path / "a" / "b" / "c"
        deep_dir.mkdir(parents=True)
        
        file1 = tmp_path / "file1.json"
        file2 = deep_dir / "file2.json"
        file1.touch()
        file2.touch()
        
        root = infer_source_root([file1, file2])
        assert root == tmp_path
