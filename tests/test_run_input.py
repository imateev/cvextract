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
        assert run_input.extracted_json_path is None
        assert run_input.adjusted_json_path is None
        assert run_input.rendered_docx_path is None
        assert run_input.metadata == {}
    
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
    
    def test_run_input_is_immutable(self, tmp_path: Path):
        """Test that RunInput is immutable (frozen dataclass)."""
        file_path = tmp_path / "test.docx"
        run_input = RunInput.from_path(file_path)
        
        # Attempt to modify should raise an error
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            run_input.file_path = tmp_path / "other.docx"
    
    def test_with_extracted_json(self, tmp_path: Path):
        """Test with_extracted_json creates new instance."""
        file_path = tmp_path / "test.docx"
        json_path = tmp_path / "test.json"
        
        run_input = RunInput.from_path(file_path)
        updated = run_input.with_extracted_json(json_path)
        
        # Original unchanged
        assert run_input.extracted_json_path is None
        # New instance has the path
        assert updated.extracted_json_path == json_path
        assert updated.file_path == file_path
        assert updated is not run_input
    
    def test_with_adjusted_json(self, tmp_path: Path):
        """Test with_adjusted_json creates new instance."""
        file_path = tmp_path / "test.docx"
        json_path = tmp_path / "adjusted.json"
        
        run_input = RunInput.from_path(file_path)
        updated = run_input.with_adjusted_json(json_path)
        
        # Original unchanged
        assert run_input.adjusted_json_path is None
        # New instance has the path
        assert updated.adjusted_json_path == json_path
        assert updated.file_path == file_path
        assert updated is not run_input
    
    def test_with_rendered_docx(self, tmp_path: Path):
        """Test with_rendered_docx creates new instance."""
        file_path = tmp_path / "test.docx"
        output_path = tmp_path / "output.docx"
        
        run_input = RunInput.from_path(file_path)
        updated = run_input.with_rendered_docx(output_path)
        
        # Original unchanged
        assert run_input.rendered_docx_path is None
        # New instance has the path
        assert updated.rendered_docx_path == output_path
        assert updated.file_path == file_path
        assert updated is not run_input
    
    def test_get_current_json_path_none(self, tmp_path: Path):
        """Test get_current_json_path returns None when no JSON set."""
        file_path = tmp_path / "test.docx"
        run_input = RunInput.from_path(file_path)
        
        assert run_input.get_current_json_path() is None
    
    def test_get_current_json_path_extracted_only(self, tmp_path: Path):
        """Test get_current_json_path returns extracted when only extracted set."""
        file_path = tmp_path / "test.docx"
        json_path = tmp_path / "test.json"
        
        run_input = RunInput.from_path(file_path).with_extracted_json(json_path)
        
        assert run_input.get_current_json_path() == json_path
    
    def test_get_current_json_path_prefers_adjusted(self, tmp_path: Path):
        """Test get_current_json_path prefers adjusted over extracted."""
        file_path = tmp_path / "test.docx"
        extracted_path = tmp_path / "test.json"
        adjusted_path = tmp_path / "adjusted.json"
        
        run_input = (RunInput.from_path(file_path)
                     .with_extracted_json(extracted_path)
                     .with_adjusted_json(adjusted_path))
        
        assert run_input.get_current_json_path() == adjusted_path
    
    def test_with_metadata(self, tmp_path: Path):
        """Test with_metadata creates new instance with updated metadata."""
        file_path = tmp_path / "test.docx"
        
        run_input = RunInput.from_path(file_path)
        updated = run_input.with_metadata(timestamp="2024-01-01", user="test")
        
        # Original unchanged
        assert run_input.metadata == {}
        # New instance has metadata
        assert updated.metadata == {"timestamp": "2024-01-01", "user": "test"}
        assert updated is not run_input
    
    def test_chained_updates(self, tmp_path: Path):
        """Test chaining multiple updates works correctly."""
        file_path = tmp_path / "test.docx"
        extracted = tmp_path / "test.json"
        adjusted = tmp_path / "adjusted.json"
        rendered = tmp_path / "output.docx"
        
        run_input = (RunInput.from_path(file_path)
                     .with_extracted_json(extracted)
                     .with_adjusted_json(adjusted)
                     .with_rendered_docx(rendered)
                     .with_metadata(version="1.0"))
        
        assert run_input.file_path == file_path
        assert run_input.extracted_json_path == extracted
        assert run_input.adjusted_json_path == adjusted
        assert run_input.rendered_docx_path == rendered
        assert run_input.metadata == {"version": "1.0"}


class TestRunInputWithPipeline:
    """Test RunInput integration with pipeline functions."""
    
    def test_extract_single_accepts_run_input(self, monkeypatch, tmp_path: Path, mock_cv_data):
        """Test extract_single accepts RunInput and returns updated RunInput."""
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
        assert isinstance(updated_run_input, RunInput)
        assert updated_run_input.file_path == docx
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
