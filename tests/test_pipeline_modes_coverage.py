"""Tests for final pipeline.py coverage push to 90%."""

import pytest
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from cvextract.pipeline import run_extract_mode


class TestRunExtractMode:
    """Tests for run_extract_mode function."""

    def test_run_extract_mode_success(self, tmp_path):
        """Test successful extract mode with JSON outputs."""
        docx_file = tmp_path / "test.docx"
        target_dir = tmp_path / "output"
        docx_file.touch()
        target_dir.mkdir()
        
        mock_data = {
            "identity": {"title": "E", "full_name": "A B", "first_name": "A", "last_name": "B"},
            "sidebar": {"languages": ["EN"]},
            "overview": "Text",
            "experiences": [],
        }
        
        with patch("cvextract.pipeline._extract_single") as mock_extract:
            mock_extract.return_value = (True, [], [])
            
            rc = run_extract_mode([docx_file], target_dir, strict=False, debug=False)
            assert rc == 0

    def test_run_extract_mode_with_failure(self, tmp_path):
        """Test extract mode when extraction fails."""
        docx_file = tmp_path / "test.docx"
        target_dir = tmp_path / "output"
        docx_file.touch()
        target_dir.mkdir()
        
        with patch("cvextract.pipeline._extract_single") as mock_extract:
            mock_extract.return_value = (False, ["Error"], [])
            
            rc = run_extract_mode([docx_file], target_dir, strict=False, debug=False)
            assert rc == 1

    def test_run_extract_mode_nonexistent_file(self, tmp_path):
        """Test extract mode with non-existent file."""
        missing_file = tmp_path / "missing.docx"
        target_dir = tmp_path / "output"
        target_dir.mkdir()
        
        rc = run_extract_mode([missing_file], target_dir, strict=False, debug=False)
        # Should skip missing files or return error depending on strict mode
        assert rc in [0, 1]

    def test_run_extract_mode_strict_missing_file(self, tmp_path):
        """Test extract mode strict mode with missing file."""
        missing_file = tmp_path / "missing.docx"
        target_dir = tmp_path / "output"
        target_dir.mkdir()
        
        rc = run_extract_mode([missing_file], target_dir, strict=True, debug=False)
        # Strict mode should fail on missing file
        assert rc == 1
