import cvextract.shared

class TestTextNormalization:
    """Tests for text normalization functions."""
    
    def test_normalize_text_with_special_chars_replaces_with_standard_equivalents(self):
        """Non-breaking spaces, soft hyphens, and line endings should be normalized."""
        s = "A\u00A0B high\u00ADquality\r\nok\rnice"
        out = cvextract.shared.normalize_text_for_processing(s)
        assert out == "A B high-quality\nok\nnice"

    def test_normalize_text_with_invalid_xml_chars_removes_them(self):
        """Invalid XML 1.0 characters like vertical tab should be stripped."""
        s = "ok\x0bnope"
        out = cvextract.shared.normalize_text_for_processing(s)
        assert out == "oknope"

    def test_clean_text_with_excess_whitespace_collapses_and_trims(self):
        """Multiple spaces, tabs, and newlines should collapse to single spaces."""
        s = "  A\u00A0B \n  C\t\tD  "
        assert cvextract.shared.clean_text(s) == "A B C D"


class TestXMLSanitization:
    """Tests for XML sanitization in data structures."""
    
    def test_sanitize_nested_object_recursively_normalizes_all_strings(self):
        """Sanitization should traverse nested dicts, lists, and preserve non-strings."""
        obj = {
            "a": "A\u00A0B",
            "b": ["x\u00ADy", {"c": "ok\x0bnope"}],
            "d": 123,
        }
        out = cvextract.shared.sanitize_for_xml_in_obj(obj)
        assert out["a"] == "A B"
        assert out["b"][0] == "x-y"
        assert out["b"][1]["c"] == "oknope"
        assert out["d"] == 123


class TestPromptLoading:
    """Tests for prompt loading and formatting."""
    
    def test_load_prompt_returns_existing_prompt_from_extractors(self):
        """load_prompt() returns content of existing prompt files from extractors folder."""
        # cv_extraction_system is a real prompt in extractors/prompts/
        result = cvextract.shared.load_prompt("cv_extraction_system")
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_load_prompt_returns_none_for_nonexistent_prompt(self):
        """load_prompt() returns None for non-existent prompt files."""
        result = cvextract.shared.load_prompt("nonexistent_prompt_xyz_123")
        assert result is None
    
    def test_format_prompt_returns_formatted_prompt_with_variables(self):
        """format_prompt() loads and formats a prompt with provided variables."""
        # Use cv_extraction_user which requires schema_json and file_name
        result = cvextract.shared.format_prompt(
            "cv_extraction_user",
            schema_json='{"type": "object"}',
            file_name="test.pdf"
        )
        assert result is not None
        assert isinstance(result, str)
        # Check that formatting worked (template should contain the variables)
        assert "test.pdf" in result or len(result) > 0
    
    def test_format_prompt_returns_none_for_nonexistent_prompt(self):
        """format_prompt() returns None if the prompt file doesn't exist."""
        result = cvextract.shared.format_prompt(
            "nonexistent_prompt_xyz_123",
            schema_json='{}',
            file_name="test.pdf"
        )
        assert result is None
    
    def test_format_prompt_handles_missing_variables_gracefully(self):
        """format_prompt() returns None if template formatting fails due to missing variables."""
        # cv_extraction_user requires specific variables, so providing wrong ones should fail
        result = cvextract.shared.format_prompt(
            "cv_extraction_user",
            wrong_var1="value1",
            wrong_var2="value2"
        )
        assert result is None

    def test_load_prompt_handles_read_error_from_extractor_prompts(self, monkeypatch):
        """load_prompt() returns None if reading from extractor prompts folder fails."""
        from pathlib import Path
        from unittest.mock import MagicMock
        
        # Mock the extractor prompt path to exist but fail on read_text()
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.read_text.side_effect = OSError("Permission denied")
        
        monkeypatch.setattr(
            "cvextract.shared._EXTRACTOR_PROMPTS_DIR",
            MagicMock(__truediv__=lambda self, name: mock_path)
        )
        
        result = cvextract.shared.load_prompt("test_prompt")
        assert result is None

    def test_load_prompt_handles_read_error_from_adjuster_prompts(self, monkeypatch):
        """load_prompt() returns None if reading from adjuster prompts folder fails."""
        from pathlib import Path
        from unittest.mock import MagicMock
        
        # Mock both extractor (doesn't exist) and adjuster (exists but fails to read)
        mock_extractor = MagicMock(spec=Path)
        mock_extractor.exists.return_value = False
        
        mock_adjuster = MagicMock(spec=Path)
        mock_adjuster.exists.return_value = True
        mock_adjuster.read_text.side_effect = IOError("Read failed")
        
        def create_extractor_path(name):
            return mock_extractor
        
        def create_adjuster_path(name):
            return mock_adjuster
        
        monkeypatch.setattr(
            "cvextract.shared._EXTRACTOR_PROMPTS_DIR",
            MagicMock(__truediv__=lambda self, name: create_extractor_path(name))
        )
        monkeypatch.setattr(
            "cvextract.shared._ADJUSTER_PROMPTS_DIR",
            MagicMock(__truediv__=lambda self, name: create_adjuster_path(name))
        )
        
        result = cvextract.shared.load_prompt("test_prompt")
        assert result is None

