"""Tests for ml_adjustment.prompt_loader module."""

import pytest
from pathlib import Path
from cvextract.ml_adjustment.prompt_loader import load_prompt, format_prompt


class TestLoadPrompt:
    """Tests for load_prompt function."""

    def test_load_system_prompt(self):
        """Test loading system_prompt.md file."""
        result = load_prompt("system_prompt")
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
        assert "You are a helpful assistant" in result

    def test_load_website_analysis_prompt(self):
        """Test loading website_analysis_prompt.md file."""
        result = load_prompt("website_analysis_prompt")
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
        assert "expert company research" in result

    def test_load_nonexistent_prompt(self):
        """Test loading a prompt that doesn't exist."""
        result = load_prompt("nonexistent_prompt")
        assert result is None

    def test_load_prompt_with_extension(self):
        """Test that we can load prompts by name without .md extension."""
        result = load_prompt("system_prompt")
        assert result is not None


class TestFormatPrompt:
    """Tests for format_prompt function."""

    def test_format_system_prompt(self):
        """Test formatting system_prompt with variables."""
        result = format_prompt(
            "system_prompt",
            company_name="Test Corp",
            company_desc="A test company",
            domains_text="Technology",
            tech_signals_text="",
            acquisition_text="",
            rebrand_text="",
            owned_products_text="",
            used_products_text="",
            related_companies_text=""
        )
        assert result is not None
        assert "Test Corp" in result
        assert "A test company" in result
        assert "Technology" in result

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

    def test_format_nonexistent_prompt(self):
        """Test formatting a prompt that doesn't exist."""
        result = format_prompt("nonexistent_prompt", var="value")
        assert result is None

    def test_format_prompt_missing_variable(self):
        """Test formatting with missing required variables returns None."""
        # system_prompt requires: company_name, company_desc, domains_text,
        # tech_signals_text, acquisition_text, rebrand_text, 
        # owned_products_text, used_products_text
        result = format_prompt(
            "system_prompt",
            company_name="Test Corp"
            # Missing: company_desc, domains_text, tech_signals_text, etc.
        )
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
