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
