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
from cvextract.adjusters.openai_job_specific_adjuster import _fetch_job_description


class TestFetchJobDescription:
    """Tests for _fetch_job_description helper function."""
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.requests')
    def test_fetch_job_description_success(self, mock_requests):
        """Test successful job description fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Senior Software Engineer position..."
        mock_requests.get.return_value = mock_response
        
        result = _fetch_job_description("https://example.com/job/123")
        
        assert result == "Senior Software Engineer position..."
        mock_requests.get.assert_called_once_with("https://example.com/job/123", timeout=15)
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.requests', None)
    def test_fetch_job_description_requests_unavailable(self):
        """Test when requests module is not available."""
        result = _fetch_job_description("https://example.com/job/123")
        assert result == ""
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.requests')
    def test_fetch_job_description_non_200_status(self, mock_requests):
        """Test when response status is not 200."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_requests.get.return_value = mock_response
        
        result = _fetch_job_description("https://example.com/job/notfound")
        
        assert result == ""
        mock_requests.get.assert_called_once()
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.requests')
    def test_fetch_job_description_empty_text(self, mock_requests):
        """Test when response text is empty."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_requests.get.return_value = mock_response
        
        result = _fetch_job_description("https://example.com/job/123")
        
        assert result == ""
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.requests')
    def test_fetch_job_description_none_text(self, mock_requests):
        """Test when response text is None."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = None
        mock_requests.get.return_value = mock_response
        
        result = _fetch_job_description("https://example.com/job/123")
        
        assert result == ""
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.requests')
    def test_fetch_job_description_connection_error(self, mock_requests):
        """Test when network error occurs during fetch."""
        mock_requests.get.side_effect = Exception("Connection timeout")
        
        result = _fetch_job_description("https://example.com/job/123")
        
        assert result == ""
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.requests')
    def test_fetch_job_description_request_exception(self, mock_requests):
        """Test when requests library raises an exception."""
        mock_requests.get.side_effect = RuntimeError("Request failed")
        
        result = _fetch_job_description("https://example.com/job/123")
        
        assert result == ""


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
    
    def test_adjust_missing_api_key(self):
        """adjust should return original CV when API key is missing."""
        adjuster = OpenAIJobSpecificAdjuster(api_key=None)
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        result = adjuster.adjust(cv_data, job_description="Test job")
        assert result == cv_data
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI', None)
    def test_adjust_openai_unavailable(self):
        """adjust should return original CV when OpenAI is not available."""
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        result = adjuster.adjust(cv_data, job_description="Test job")
        assert result == cv_data
    
    def test_adjust_validate_params_called(self):
        """adjust should call validate_params and raise if params invalid."""
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        # Missing job_url and job_description should raise
        with pytest.raises(ValueError, match="requires either"):
            adjuster.adjust(cv_data)  # No params
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster._fetch_job_description')
    def test_adjust_url_fetch_fails_returns_original(self, mock_fetch):
        """If job fetch from URL fails, should return original CV."""
        mock_fetch.return_value = ""  # Empty job description
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        result = adjuster.adjust(cv_data, job_url="https://example.com/job/123")
        assert result == cv_data
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_prompt_load_fails(self, mock_format):
        """If prompt template fails to load, should return original CV."""
        mock_format.return_value = None
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        result = adjuster.adjust(cv_data, job_description="Test job")
        assert result == cv_data
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_api_call_success(self, mock_format, mock_openai_class):
        """adjust should successfully call OpenAI and return adjusted CV."""
        mock_format.return_value = "System prompt"
        
        adjusted_cv = {"identity": {"name": "John"}, "sidebar": {}, "overview": "Adjusted", "experiences": []}
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=str(adjusted_cv).replace("'", '"')))]
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key", model="gpt-4o-mini")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        result = adjuster.adjust(cv_data, job_description="Test job")
        assert "John" in str(result)  # Verify the adjusted data is in result
        mock_openai_class.assert_called_once_with(api_key="test-key")
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_empty_completion(self, mock_format, mock_openai_class):
        """adjust should return original CV if completion is empty."""
        mock_format.return_value = "System prompt"
        
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=None))]
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        result = adjuster.adjust(cv_data, job_description="Test job")
        assert result == cv_data
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_invalid_json_response(self, mock_format, mock_openai_class):
        """adjust should return original CV if completion is invalid JSON."""
        mock_format.return_value = "System prompt"
        
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content="not valid json"))]
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        result = adjuster.adjust(cv_data, job_description="Test job")
        assert result == cv_data
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_api_exception(self, mock_format, mock_openai_class):
        """adjust should return original CV if API call raises exception."""
        mock_format.return_value = "System prompt"
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API error")
        mock_openai_class.return_value = mock_client
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        result = adjuster.adjust(cv_data, job_description="Test job")
        assert result == cv_data
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_non_dict_json(self, mock_format, mock_openai_class):
        """adjust should return JSON-parsed content even if not a dict (per the code logic)."""
        mock_format.return_value = "System prompt"
        
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content='[1, 2, 3]'))]
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        result = adjuster.adjust(cv_data, job_description="Test job")
        assert result == [1, 2, 3]  # Code accepts any JSON-parsed value that's not None


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
