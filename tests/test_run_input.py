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
    
    def test_run_input_direct_construction(self, tmp_path: Path):
        """Test direct construction of RunInput."""
        file_path = tmp_path / "test.docx"
        run_input = RunInput(file_path=file_path)
        
        assert run_input.file_path == file_path
    
    def test_run_input_preserves_path_type(self, tmp_path: Path):
        """Test that RunInput preserves Path type."""
        file_path = tmp_path / "test.docx"
        run_input = RunInput.from_path(file_path)
        
        assert isinstance(run_input.file_path, Path)
        assert run_input.file_path == file_path
    
    def test_run_input_has_optional_fields(self, tmp_path: Path):
        """Test that RunInput has all required optional fields."""
        file_path = tmp_path / "test.docx"
        run_input = RunInput.from_path(file_path)
        
        assert run_input.extracted_json_path is None
        assert run_input.adjusted_json_path is None
        assert run_input.rendered_docx_path is None
        assert run_input.metadata == {}
    
    def test_run_input_is_immutable(self, tmp_path: Path):
        """Test that RunInput is immutable (frozen dataclass)."""
        file_path = tmp_path / "test.docx"
        run_input = RunInput.from_path(file_path)
        
        # Attempting to modify a field should raise an error
        with pytest.raises(AttributeError):
            run_input.file_path = tmp_path / "other.docx"
        
        with pytest.raises(AttributeError):
            run_input.extracted_json_path = tmp_path / "test.json"
    
    def test_get_current_json_path_none_when_empty(self, tmp_path: Path):
        """Test get_current_json_path returns None when no JSON paths are set."""
        file_path = tmp_path / "test.docx"
        run_input = RunInput.from_path(file_path)
        
        assert run_input.get_current_json_path() is None
    
    def test_get_current_json_path_returns_extracted(self, tmp_path: Path):
        """Test get_current_json_path returns extracted_json_path when only extracted is set."""
        file_path = tmp_path / "test.docx"
        extracted_json = tmp_path / "extracted.json"
        run_input = RunInput(file_path=file_path, extracted_json_path=extracted_json)
        
        assert run_input.get_current_json_path() == extracted_json
    
    def test_get_current_json_path_prefers_adjusted(self, tmp_path: Path):
        """Test get_current_json_path prefers adjusted_json_path over extracted_json_path."""
        file_path = tmp_path / "test.docx"
        extracted_json = tmp_path / "extracted.json"
        adjusted_json = tmp_path / "adjusted.json"
        run_input = RunInput(
            file_path=file_path, 
            extracted_json_path=extracted_json,
            adjusted_json_path=adjusted_json
        )
        
        assert run_input.get_current_json_path() == adjusted_json
    
    def test_with_extracted_json_returns_new_instance(self, tmp_path: Path):
        """Test with_extracted_json returns a new RunInput instance."""
        file_path = tmp_path / "test.docx"
        extracted_json = tmp_path / "extracted.json"
        run_input = RunInput.from_path(file_path)
        
        updated = run_input.with_extracted_json(extracted_json)
        
        # Original should be unchanged
        assert run_input.extracted_json_path is None
        # New instance should have the path set
        assert updated.extracted_json_path == extracted_json
        assert updated.file_path == file_path
        assert updated is not run_input
    
    def test_with_adjusted_json_returns_new_instance(self, tmp_path: Path):
        """Test with_adjusted_json returns a new RunInput instance."""
        file_path = tmp_path / "test.docx"
        extracted_json = tmp_path / "extracted.json"
        adjusted_json = tmp_path / "adjusted.json"
        run_input = RunInput(file_path=file_path, extracted_json_path=extracted_json)
        
        updated = run_input.with_adjusted_json(adjusted_json)
        
        # Original should be unchanged
        assert run_input.adjusted_json_path is None
        # New instance should have the path set
        assert updated.adjusted_json_path == adjusted_json
        assert updated.extracted_json_path == extracted_json
        assert updated.file_path == file_path
        assert updated is not run_input
    
    def test_with_rendered_docx_returns_new_instance(self, tmp_path: Path):
        """Test with_rendered_docx returns a new RunInput instance."""
        file_path = tmp_path / "test.docx"
        rendered_docx = tmp_path / "rendered.docx"
        run_input = RunInput.from_path(file_path)
        
        updated = run_input.with_rendered_docx(rendered_docx)
        
        # Original should be unchanged
        assert run_input.rendered_docx_path is None
        # New instance should have the path set
        assert updated.rendered_docx_path == rendered_docx
        assert updated.file_path == file_path
        assert updated is not run_input
    
    def test_immutable_helpers_preserve_all_fields(self, tmp_path: Path):
        """Test that with_* methods preserve all existing fields."""
        file_path = tmp_path / "test.docx"
        extracted_json = tmp_path / "extracted.json"
        adjusted_json = tmp_path / "adjusted.json"
        rendered_docx = tmp_path / "rendered.docx"
        metadata = {"key": "value"}
        
        run_input = RunInput(
            file_path=file_path,
            extracted_json_path=extracted_json,
            metadata=metadata
        )
        
        # Add adjusted JSON
        with_adjusted = run_input.with_adjusted_json(adjusted_json)
        assert with_adjusted.extracted_json_path == extracted_json
        assert with_adjusted.adjusted_json_path == adjusted_json
        assert with_adjusted.metadata == metadata
        
        # Add rendered DOCX
        with_rendered = with_adjusted.with_rendered_docx(rendered_docx)
        assert with_rendered.extracted_json_path == extracted_json
        assert with_rendered.adjusted_json_path == adjusted_json
        assert with_rendered.rendered_docx_path == rendered_docx
        assert with_rendered.metadata == metadata


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
        
        ok, errs, warns, updated_run_input = p.extract_single(run_input, out_json, debug=False)
        assert ok is True
        assert errs == []
        # Verify RunInput is returned with extracted_json_path set
        assert isinstance(updated_run_input, RunInput)
        assert updated_run_input.extracted_json_path == out_json
    
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
        ok, errs, warns, updated_run_input = p.extract_single(docx, out_json, debug=False)
        assert ok is True
        assert errs == []
        # Verify RunInput is created and returned
        assert isinstance(updated_run_input, RunInput)
        assert updated_run_input.file_path == docx
        assert updated_run_input.extracted_json_path == out_json
    
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
