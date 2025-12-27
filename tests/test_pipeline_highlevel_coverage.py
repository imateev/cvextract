"""Tests to improve coverage of pipeline_highlevel module."""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from cvextract.pipeline_highlevel import extract_cv_structure, process_single_docx


class TestExtractCvStructure:
    """Tests for extract_cv_structure function."""

    def test_extract_cv_structure_integrates_all_parsers(self, tmp_path):
        """Test extract_cv_structure uses the DocxCVExtractor."""
        mock_docx = tmp_path / "test.docx"
        mock_docx.touch()
        
        mock_data = {
            "identity": {"title": "Engineer", "full_name": "John Doe", "first_name": "John", "last_name": "Doe"},
            "sidebar": {"languages": ["EN"], "tools": ["Python"]},
            "overview": "Overview text",
            "experiences": [{"heading": "Job", "description": "desc"}],
        }
        
        with patch("cvextract.pipeline_highlevel.DocxCVExtractor") as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor.extract.return_value = mock_data
            mock_extractor_class.return_value = mock_extractor
            
            result = extract_cv_structure(mock_docx)
            
            assert result == mock_data
            mock_extractor_class.assert_called_once()
            mock_extractor.extract.assert_called_once_with(mock_docx)


class TestProcessSingleDocx:
    """Tests for process_single_docx function."""

    def test_process_single_docx_without_output(self, tmp_path):
        """Test process_single_docx extracts data without writing to file."""
        mock_docx = tmp_path / "test.docx"
        mock_docx.touch()
        
        mock_data = {
            "identity": {"title": "Engineer", "full_name": "Jane", "first_name": "Jane", "last_name": "Doe"},
            "sidebar": {"languages": ["EN"]},
            "overview": "Overview",
            "experiences": [],
        }
        
        with patch("cvextract.pipeline_highlevel.extract_cv_structure") as mock_extract:
            mock_extract.return_value = mock_data
            
            result = process_single_docx(mock_docx, out=None)
            
            assert result == mock_data
            mock_extract.assert_called_once_with(mock_docx)

    def test_process_single_docx_with_output_creates_file(self, tmp_path):
        """Test process_single_docx writes JSON to specified output path."""
        mock_docx = tmp_path / "test.docx"
        mock_docx.touch()
        output_file = tmp_path / "output.json"
        
        mock_data = {
            "identity": {"title": "Senior Dev", "full_name": "Bob Smith", "first_name": "Bob", "last_name": "Smith"},
            "sidebar": {"tools": ["Python", "Rust"]},
            "overview": "Experienced developer",
            "experiences": [{"heading": "2020-Present", "description": "Senior role"}],
        }
        
        with patch("cvextract.pipeline_highlevel.extract_cv_structure") as mock_extract:
            mock_extract.return_value = mock_data
            
            result = process_single_docx(mock_docx, out=output_file)
            
            assert result == mock_data
            assert output_file.exists()
            
            with output_file.open("r", encoding="utf-8") as f:
                saved_data = json.load(f)
            
            assert saved_data == mock_data

    def test_process_single_docx_creates_parent_directories(self, tmp_path):
        """Test process_single_docx creates parent directories if needed."""
        mock_docx = tmp_path / "test.docx"
        mock_docx.touch()
        
        # Output path with non-existent parent directories
        deep_output = tmp_path / "deep" / "nested" / "dirs" / "output.json"
        
        mock_data = {
            "identity": {"title": "T", "full_name": "A B", "first_name": "A", "last_name": "B"},
            "sidebar": {},
            "overview": "",
            "experiences": [],
        }
        
        with patch("cvextract.pipeline_highlevel.extract_cv_structure") as mock_extract:
            mock_extract.return_value = mock_data
            
            result = process_single_docx(mock_docx, out=deep_output)
            
            assert result == mock_data
            assert deep_output.parent.exists()
            assert deep_output.exists()

    def test_process_single_docx_with_unicode_characters(self, tmp_path):
        """Test process_single_docx handles Unicode in data correctly."""
        mock_docx = tmp_path / "test.docx"
        mock_docx.touch()
        output_file = tmp_path / "output.json"
        
        mock_data = {
            "identity": {
                "title": "工程师 (Engineer)",
                "full_name": "José García",
                "first_name": "José",
                "last_name": "García"
            },
            "sidebar": {"languages": ["中文", "English", "Français"]},
            "overview": "Multilingual developer with emoji 🚀",
            "experiences": [{"heading": "2020-Present", "description": "Ðoing çöðé"}],
        }
        
        with patch("cvextract.pipeline_highlevel.extract_cv_structure") as mock_extract:
            mock_extract.return_value = mock_data
            
            result = process_single_docx(mock_docx, out=output_file)
            
            assert result == mock_data
            
            with output_file.open("r", encoding="utf-8") as f:
                saved_data = json.load(f)
            
            # Verify Unicode is preserved (ensure_ascii=False)
            assert saved_data["identity"]["title"] == "工程师 (Engineer)"
            assert saved_data["sidebar"]["languages"] == ["中文", "English", "Français"]
            assert "🚀" in saved_data["overview"]

    def test_process_single_docx_json_formatting(self, tmp_path):
        """Test process_single_docx writes formatted JSON with proper indentation."""
        mock_docx = tmp_path / "test.docx"
        mock_docx.touch()
        output_file = tmp_path / "output.json"
        
        mock_data = {
            "identity": {"title": "Dev", "full_name": "A B", "first_name": "A", "last_name": "B"},
            "sidebar": {"tools": ["Python"]},
            "overview": "Text",
            "experiences": [{"heading": "2020-Now", "description": "Work"}],
        }
        
        with patch("cvextract.pipeline_highlevel.extract_cv_structure") as mock_extract:
            mock_extract.return_value = mock_data
            
            process_single_docx(mock_docx, out=output_file)
            
            with output_file.open("r", encoding="utf-8") as f:
                content = f.read()
            
            # Verify formatting with indentation
            assert "\n" in content  # Multi-line format
            assert "    " in content  # 2-level indent (indent=2 becomes spaces)
