"""Tests for prompt loading functions."""

from cvextract.shared import load_prompt, format_prompt


class TestLoadPrompt:
    """Tests for load_prompt function."""

    def test_load_website_analysis_prompt(self):
        """Test loading website_analysis_prompt.md file."""
        result = load_prompt("website_analysis_prompt")
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
        assert "expert company research" in result

    def test_load_cv_extraction_system_prompt(self):
        """Test loading cv_extraction_system.md file."""
        result = load_prompt("cv_extraction_system")
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
        assert "CV/resume data extraction expert" in result
        assert "Return ONLY valid JSON" in result

    def test_load_cv_extraction_user_prompt(self):
        """Test loading cv_extraction_user.md file."""
        result = load_prompt("cv_extraction_user")
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
        assert "schema_json" in result  # Template variable
        assert "Extraction guidelines" in result

    def test_load_job_specific_prompt(self):
        """Test loading adjuster_promp_for_specific_job.md file."""
        result = load_prompt("adjuster_promp_for_specific_job")
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_load_nonexistent_prompt(self):
        """Test loading a prompt that doesn't exist."""
        result = load_prompt("nonexistent_prompt")
        assert result is None


class TestFormatPrompt:
    """Tests for format_prompt function."""

    def test_format_website_analysis_prompt(self):
        """Test formatting website_analysis_prompt with variables."""
        result = format_prompt(
            "website_analysis_prompt",
            customer_url="https://example.com",
            schema='{"type": "object"}'
        )
        assert result is not None
        assert "https://example.com" in result
        assert '"type": "object"' in result

    def test_format_cv_extraction_user_prompt(self):
        """Test formatting cv_extraction_user with variables."""
        result = format_prompt(
            "cv_extraction_user",
            schema_json='{"type": "object"}',
            file_name="test.docx"
        )
        assert result is not None
        assert '"type": "object"' in result
        assert "test.docx" in result
        assert "Extraction guidelines" in result

    def test_format_nonexistent_prompt(self):
        """Test formatting a prompt that doesn't exist."""
        result = format_prompt("nonexistent_prompt", var="value")
        assert result is None

    def test_format_prompt_extra_variables(self):
        """Test formatting with extra variables (should be ignored)."""
        result = format_prompt(
            "website_analysis_prompt",
            customer_url="https://example.com",
            schema='{"type": "object"}',
            extra_var="ignored"  # Extra variable
        )
        assert result is not None
        assert "https://example.com" in result
        # Extra variable should be ignored, not cause an error
