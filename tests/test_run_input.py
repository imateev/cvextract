"""Tests for RunInput object."""

from pathlib import Path
import pytest
from cvextract.run_input import RunInput


@pytest.fixture
def mock_cv_data():
    """Shared fixture for mock CV data structure."""
    return {
        "identity": {"title": "T", "full_name": "F N", "first_name": "F", "last_name": "N"},
        "sidebar": {"languages": ["Python"], "tools": ["x"], "industries": ["x"], 
                   "spoken_languages": ["EN"], "academic_background": ["x"]},
        "experiences": [{"heading": "h", "description": "d", "bullets": ["b"]}],
    }


@pytest.fixture
def mock_cv_data_minimal():
    """Shared fixture for minimal mock CV data structure."""
    return {
        "identity": {"title": "T", "full_name": "F N", "first_name": "F", "last_name": "N"},
        "sidebar": {"languages": ["Python"], "tools": [], "industries": [], 
                   "spoken_languages": [], "academic_background": []},
        "experiences": [{"heading": "h", "description": "d", "bullets": ["b"]}],
    }


class TestRunInput:
    """Test RunInput construction and usage."""
    
    def test_run_input_from_path(self, tmp_path: Path):
        """Test constructing RunInput from a Path."""
        file_path = tmp_path / "test.docx"
        run_input = RunInput.from_path(file_path)
        
        assert run_input.file_path == file_path
        assert isinstance(run_input, RunInput)
        # Verify all optional fields are None by default
        assert run_input.extracted_json_path is None
        assert run_input.adjusted_json_path is None
        assert run_input.rendered_output_path is None
        assert run_input.errors == []
        assert run_input.warnings == []
    
    def test_run_input_direct_construction(self, tmp_path: Path):
        """Test direct construction of RunInput."""
        file_path = tmp_path / "test.docx"
        run_input = RunInput(file_path=file_path)
        
        assert run_input.file_path == file_path
        assert run_input.extracted_json_path is None
    
    def test_run_input_preserves_path_type(self, tmp_path: Path):
        """Test that RunInput preserves Path type."""
        file_path = tmp_path / "test.docx"
        run_input = RunInput.from_path(file_path)
        
        assert isinstance(run_input.file_path, Path)
        assert run_input.file_path == file_path
    
    def test_run_input_set_extracted_json_path(self, tmp_path: Path):
        """Test setting extracted JSON path."""
        file_path = tmp_path / "test.docx"
        json_path = tmp_path / "test.json"
        run_input = RunInput.from_path(file_path)
        
        run_input.extracted_json_path = json_path
        assert run_input.extracted_json_path == json_path
    
    def test_run_input_set_adjusted_json_path(self, tmp_path: Path):
        """Test setting adjusted JSON path."""
        file_path = tmp_path / "test.docx"
        adjusted_path = tmp_path / "test_adjusted.json"
        run_input = RunInput.from_path(file_path)
        
        run_input.adjusted_json_path = adjusted_path
        assert run_input.adjusted_json_path == adjusted_path
    
    def test_run_input_set_rendered_output_path(self, tmp_path: Path):
        """Test setting rendered output path."""
        file_path = tmp_path / "test.docx"
        output_path = tmp_path / "test_NEW.docx"
        run_input = RunInput.from_path(file_path)
        
        run_input.rendered_output_path = output_path
        assert run_input.rendered_output_path == output_path
    
    def test_run_input_add_error(self, tmp_path: Path):
        """Test adding error messages."""
        file_path = tmp_path / "test.docx"
        run_input = RunInput.from_path(file_path)
        
        run_input.add_error("Test error 1")
        run_input.add_error("Test error 2")
        
        assert len(run_input.errors) == 2
        assert "Test error 1" in run_input.errors
        assert "Test error 2" in run_input.errors
    
    def test_run_input_add_warning(self, tmp_path: Path):
        """Test adding warning messages."""
        file_path = tmp_path / "test.docx"
        run_input = RunInput.from_path(file_path)
        
        run_input.add_warning("Test warning 1")
        run_input.add_warning("Test warning 2")
        
        assert len(run_input.warnings) == 2
        assert "Test warning 1" in run_input.warnings
        assert "Test warning 2" in run_input.warnings
    
    def test_run_input_has_errors(self, tmp_path: Path):
        """Test has_errors method."""
        file_path = tmp_path / "test.docx"
        run_input = RunInput.from_path(file_path)
        
        assert not run_input.has_errors()
        
        run_input.add_error("Test error")
        assert run_input.has_errors()
    
    def test_run_input_has_warnings(self, tmp_path: Path):
        """Test has_warnings method."""
        file_path = tmp_path / "test.docx"
        run_input = RunInput.from_path(file_path)
        
        assert not run_input.has_warnings()
        
        run_input.add_warning("Test warning")
        assert run_input.has_warnings()
    
    def test_run_input_complete_workflow_paths(self, tmp_path: Path):
        """Test setting all workflow paths in sequence."""
        file_path = tmp_path / "test.docx"
        json_path = tmp_path / "test.json"
        adjusted_path = tmp_path / "test_adjusted.json"
        output_path = tmp_path / "test_NEW.docx"
        
        run_input = RunInput.from_path(file_path)
        
        # Simulate extract stage
        run_input.extracted_json_path = json_path
        assert run_input.extracted_json_path == json_path
        
        # Simulate adjust stage
        run_input.adjusted_json_path = adjusted_path
        assert run_input.adjusted_json_path == adjusted_path
        
        # Simulate render stage
        run_input.rendered_output_path = output_path
        assert run_input.rendered_output_path == output_path
        
        # Verify all paths are set
        assert run_input.file_path == file_path
        assert run_input.extracted_json_path == json_path
        assert run_input.adjusted_json_path == adjusted_path
        assert run_input.rendered_output_path == output_path


class TestRunInputWithPipeline:
    """Test RunInput integration with pipeline functions."""
    
    def test_extract_single_accepts_run_input(self, monkeypatch, tmp_path: Path, mock_cv_data):
        """Test extract_single accepts RunInput."""
        from cvextract import pipeline_helpers as p
        
        docx = tmp_path / "test.docx"
        out_json = tmp_path / "test.json"
        run_input = RunInput.from_path(docx)
        
        def fake_process(_source, out, extractor=None):
            out.write_text("{}", encoding="utf-8")
            return mock_cv_data
        
        monkeypatch.setattr(p, "process_single_docx", fake_process)
        
        ok, errs, warns = p.extract_single(run_input, out_json, debug=False)
        assert ok is True
        assert errs == []
    
    def test_extract_single_accepts_path_backward_compatibility(self, monkeypatch, tmp_path: Path, mock_cv_data):
        """Test extract_single still accepts Path for backward compatibility."""
        from cvextract import pipeline_helpers as p
        
        docx = tmp_path / "test.docx"
        out_json = tmp_path / "test.json"
        
        def fake_process(_source, out, extractor=None):
            out.write_text("{}", encoding="utf-8")
            return mock_cv_data
        
        monkeypatch.setattr(p, "process_single_docx", fake_process)
        
        # Pass Path directly instead of RunInput
        ok, errs, warns = p.extract_single(docx, out_json, debug=False)
        assert ok is True
        assert errs == []
    
    def test_process_single_docx_accepts_run_input(self, monkeypatch, tmp_path: Path, mock_cv_data_minimal):
        """Test process_single_docx accepts RunInput."""
        from cvextract.pipeline_highlevel import process_single_docx
        from cvextract.extractors import DocxCVExtractor
        
        docx = tmp_path / "test.docx"
        out_json = tmp_path / "test.json"
        run_input = RunInput.from_path(docx)
        
        # Mock the extractor
        def fake_extract(self, _path):
            return mock_cv_data_minimal
        
        monkeypatch.setattr(DocxCVExtractor, "extract", fake_extract)
        
        data = process_single_docx(run_input, out=out_json)
        assert data is not None
        assert "identity" in data
        assert out_json.exists()
    
    def test_process_single_docx_accepts_path_backward_compatibility(self, monkeypatch, tmp_path: Path, mock_cv_data_minimal):
        """Test process_single_docx still accepts Path for backward compatibility."""
        from cvextract.pipeline_highlevel import process_single_docx
        from cvextract.extractors import DocxCVExtractor
        
        docx = tmp_path / "test.docx"
        out_json = tmp_path / "test.json"
        
        # Mock the extractor
        def fake_extract(self, _path):
            return mock_cv_data_minimal
        
        monkeypatch.setattr(DocxCVExtractor, "extract", fake_extract)
        
        # Pass Path directly instead of RunInput
        data = process_single_docx(docx, out=out_json)
        assert data is not None
        assert "identity" in data
        assert out_json.exists()
    
    def test_extract_single_records_paths_to_run_input(self, monkeypatch, tmp_path: Path, mock_cv_data):
        """Test that extract_single records the extracted JSON path to RunInput."""
        from cvextract import pipeline_helpers as p
        
        docx = tmp_path / "test.docx"
        out_json = tmp_path / "test.json"
        run_input = RunInput.from_path(docx)
        
        def fake_process(_source, out, extractor=None):
            out.write_text("{}", encoding="utf-8")
            return mock_cv_data
        
        monkeypatch.setattr(p, "process_single_docx", fake_process)
        
        ok, errs, warns = p.extract_single(run_input, out_json, debug=False)
        
        # Verify the extracted JSON path was recorded
        assert run_input.extracted_json_path == out_json
    
    def test_extract_single_records_errors_to_run_input(self, monkeypatch, tmp_path: Path):
        """Test that extract_single records errors to RunInput."""
        from cvextract import pipeline_helpers as p
        
        docx = tmp_path / "test.docx"
        out_json = tmp_path / "test.json"
        run_input = RunInput.from_path(docx)
        
        def fake_process(_source, out, extractor=None):
            raise ValueError("Test extraction error")
        
        monkeypatch.setattr(p, "process_single_docx", fake_process)
        
        ok, errs, warns = p.extract_single(run_input, out_json, debug=False)
        
        # Verify error was recorded to RunInput
        assert not ok
        assert run_input.has_errors()
        assert len(run_input.errors) > 0
    
    def test_extract_single_records_warnings_to_run_input(self, monkeypatch, tmp_path: Path, mock_cv_data):
        """Test that extract_single records warnings to RunInput."""
        from cvextract import pipeline_helpers as p
        from cvextract.shared import VerificationResult
        
        docx = tmp_path / "test.docx"
        out_json = tmp_path / "test.json"
        run_input = RunInput.from_path(docx)
        
        def fake_process(_source, out, extractor=None):
            out.write_text("{}", encoding="utf-8")
            return mock_cv_data
        
        class MockVerifier:
            def verify(self, _data):
                return VerificationResult(ok=True, errors=[], warnings=["Test warning"])
        
        def fake_get_verifier(_name):
            return MockVerifier()
        
        monkeypatch.setattr(p, "process_single_docx", fake_process)
        monkeypatch.setattr(p, "get_verifier", fake_get_verifier)
        
        ok, errs, warns = p.extract_single(run_input, out_json, debug=False)
        
        # Verify warning was recorded to RunInput
        assert ok
        assert run_input.has_warnings()
        assert "Test warning" in run_input.warnings
    
    def test_render_and_verify_records_output_path(self, monkeypatch, tmp_path: Path, mock_cv_data):
        """Test that render_and_verify records the rendered output path to RunInput."""
        from cvextract import pipeline_helpers as p
        
        json_path = tmp_path / "test.json"
        template_path = tmp_path / "template.docx"
        output_path = tmp_path / "output.docx"
        run_input = RunInput.from_path(tmp_path / "original.docx")
        
        # Create mock JSON file
        import json
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(mock_cv_data, f)
        
        # Mock the render function
        def fake_render(cv_data, template, output):
            output.write_text("fake docx", encoding="utf-8")
            return output
        
        monkeypatch.setattr(p, "render_cv_data", fake_render)
        
        ok, errs, warns, cmp = p.render_and_verify(
            json_path, template_path, output_path, debug=False,
            skip_compare=True, run_input=run_input
        )
        
        # Verify the rendered output path was recorded
        assert run_input.rendered_output_path == output_path
    
    def test_render_and_verify_records_errors_to_run_input(self, monkeypatch, tmp_path: Path):
        """Test that render_and_verify records errors to RunInput."""
        from cvextract import pipeline_helpers as p
        
        json_path = tmp_path / "test.json"
        template_path = tmp_path / "template.docx"
        output_path = tmp_path / "output.docx"
        run_input = RunInput.from_path(tmp_path / "original.docx")
        
        # Create mock JSON file
        json_path.write_text("{}", encoding="utf-8")
        
        # Mock the render function to raise an error
        def fake_render(cv_data, template, output):
            raise ValueError("Test render error")
        
        monkeypatch.setattr(p, "render_cv_data", fake_render)
        
        ok, errs, warns, cmp = p.render_and_verify(
            json_path, template_path, output_path, debug=False,
            skip_compare=True, run_input=run_input
        )
        
        # Verify error was recorded to RunInput
        assert not ok
        assert run_input.has_errors()
        assert len(run_input.errors) > 0
