"""Tests for adjuster framework and registry."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from cvextract.adjusters import (
    CVAdjuster,
    OpenAICompanyResearchAdjuster,
    OpenAIJobSpecificAdjuster,
    get_adjuster,
    list_adjusters,
    register_adjuster,
)


class TestAdjusterRegistry:
    """Tests for the adjuster registry system."""
    
    def test_list_adjusters_returns_builtin_adjusters(self):
        """list_adjusters should return all registered adjusters."""
        adjusters = list_adjusters()
        assert len(adjusters) >= 2
        adjuster_names = [a['name'] for a in adjusters]
        assert 'openai-company-research' in adjuster_names
        assert 'openai-job-specific' in adjuster_names
    
    def test_get_adjuster_returns_instance(self):
        """get_adjuster should return an instance of the requested adjuster."""
        adjuster = get_adjuster('openai-company-research')
        assert adjuster is not None
        assert isinstance(adjuster, OpenAICompanyResearchAdjuster)
    
    def test_get_adjuster_unknown_returns_none(self):
        """get_adjuster should return None for unknown adjusters."""
        adjuster = get_adjuster('unknown-adjuster')
        assert adjuster is None
    
    def test_register_custom_adjuster(self):
        """Custom adjusters can be registered."""
        class CustomAdjuster(CVAdjuster):
            def name(self):
                return "custom-test"
            
            def description(self):
                return "Test adjuster"
            
            def adjust(self, cv_data, **kwargs):
                return cv_data
        
        register_adjuster(CustomAdjuster)
        adjuster = get_adjuster('custom-test')
        assert adjuster is not None
        assert adjuster.name() == 'custom-test'


class TestOpenAICompanyResearchAdjuster:
    """Tests for the OpenAI company research adjuster."""
    
    def test_adjuster_name(self):
        """Adjuster should return correct name."""
        adjuster = OpenAICompanyResearchAdjuster()
        assert adjuster.name() == 'openai-company-research'
    
    def test_adjuster_description(self):
        """Adjuster should return a description."""
        adjuster = OpenAICompanyResearchAdjuster()
        desc = adjuster.description()
        assert isinstance(desc, str)
        assert len(desc) > 0
    
    def test_validate_params_requires_customer_url(self):
        """validate_params should raise error if customer_url is missing."""
        adjuster = OpenAICompanyResearchAdjuster()
        with pytest.raises(ValueError, match="requires 'customer-url' parameter"):
            adjuster.validate_params()
    
    def test_validate_params_accepts_customer_url(self):
        """validate_params should accept customer_url parameter."""
        adjuster = OpenAICompanyResearchAdjuster()
        adjuster.validate_params(customer_url="https://example.com")
    
    @patch('cvextract.adjusters.openai_company_research_adjuster.MLAdjuster')
    def test_adjust_calls_ml_adjuster(self, mock_ml_adjuster):
        """adjust should delegate to MLAdjuster."""
        mock_instance = MagicMock()
        mock_instance.adjust.return_value = {"adjusted": True}
        mock_ml_adjuster.return_value = mock_instance
        
        adjuster = OpenAICompanyResearchAdjuster(model="test-model", api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        result = adjuster.adjust(cv_data, customer_url="https://example.com")
        
        assert result == {"adjusted": True}
        mock_instance.adjust.assert_called_once_with(
            cv_data,
            "https://example.com",
            cache_path=None
        )


class TestOpenAIJobSpecificAdjuster:
    """Tests for the OpenAI job-specific adjuster."""
    
    def test_adjuster_name(self):
        """Adjuster should return correct name."""
        adjuster = OpenAIJobSpecificAdjuster()
        assert adjuster.name() == 'openai-job-specific'
    
    def test_adjuster_description(self):
        """Adjuster should return a description."""
        adjuster = OpenAIJobSpecificAdjuster()
        desc = adjuster.description()
        assert isinstance(desc, str)
        assert len(desc) > 0
    
    def test_validate_params_requires_job_url_or_description(self):
        """validate_params should raise error if neither job_url nor job_description is provided."""
        adjuster = OpenAIJobSpecificAdjuster()
        with pytest.raises(ValueError, match="requires either 'job-url' or 'job-description'"):
            adjuster.validate_params()
    
    def test_validate_params_accepts_job_url(self):
        """validate_params should accept job_url parameter."""
        adjuster = OpenAIJobSpecificAdjuster()
        adjuster.validate_params(job_url="https://careers.example.com/job/123")
    
    def test_validate_params_accepts_job_description(self):
        """validate_params should accept job_description parameter."""
        adjuster = OpenAIJobSpecificAdjuster()
        adjuster.validate_params(job_description="Job description text")
    
    def test_adjust_with_job_description(self):
        """adjust should work with job_description parameter (no API call)."""
        adjuster = OpenAIJobSpecificAdjuster(api_key=None)  # No API key
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        # Without API key, should return original data
        result = adjuster.adjust(cv_data, job_description="Test job")
        assert result == cv_data


class TestCLIListAdjusters:
    """Tests for CLI --list adjusters functionality."""
    
    def test_list_adjusters_command(self, capsys):
        """--list adjusters should print available adjusters."""
        from cvextract.cli_gather import _handle_list_command
        
        _handle_list_command('adjusters')
        captured = capsys.readouterr()
        
        assert 'openai-company-research' in captured.out
        assert 'openai-job-specific' in captured.out
        assert 'Available Adjusters' in captured.out


class TestCLIMultipleAdjusters:
    """Tests for CLI with multiple adjusters."""
    
    def test_parse_multiple_adjust_flags(self):
        """Should parse multiple --adjust flags into separate adjusters."""
        from cvextract.cli_gather import gather_user_requirements
        
        config = gather_user_requirements([
            "--extract", "source=/path/to/cv.docx",
            "--adjust", "name=openai-company-research", "customer-url=https://example.com",
            "--adjust", "name=openai-job-specific", "job-url=https://careers.example.com/job/123",
            "--target", "/output"
        ])
        
        assert config.adjust is not None
        assert len(config.adjust.adjusters) == 2
        assert config.adjust.adjusters[0].name == 'openai-company-research'
        assert config.adjust.adjusters[0].params.get('customer-url') == 'https://example.com'
        assert config.adjust.adjusters[1].name == 'openai-job-specific'
        assert config.adjust.adjusters[1].params.get('job-url') == 'https://careers.example.com/job/123'
    
    def test_parse_multiple_adjusters_with_model(self):
        """Should parse multiple adjusters with different OpenAI models."""
        from cvextract.cli_gather import gather_user_requirements
        
        config = gather_user_requirements([
            "--extract", "source=/path/to/cv.docx",
            "--adjust", "name=openai-company-research", "customer-url=https://example.com", "openai-model=gpt-4",
            "--adjust", "name=openai-job-specific", "job-url=https://careers.example.com/job/123", "openai-model=gpt-3.5-turbo",
            "--target", "/output"
        ])
        
        assert config.adjust.adjusters[0].openai_model == 'gpt-4'
        assert config.adjust.adjusters[1].openai_model == 'gpt-3.5-turbo'
    
    def test_backward_compatibility_customer_url(self):
        """Old customer-url syntax should still work (backward compatibility)."""
        from cvextract.cli_gather import gather_user_requirements
        
        config = gather_user_requirements([
            "--extract", "source=/path/to/cv.docx",
            "--adjust", "customer-url=https://example.com",
            "--target", "/output"
        ])
        
        assert config.adjust is not None
        assert len(config.adjust.adjusters) == 1
        assert config.adjust.adjusters[0].name == 'openai-company-research'
        assert config.adjust.adjusters[0].params.get('customer-url') == 'https://example.com'
