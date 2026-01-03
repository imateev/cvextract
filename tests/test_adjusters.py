"""Tests for adjuster framework and registry."""

import json
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
from cvextract.adjusters.adjuster_registry import unregister_adjuster
from cvextract.adjusters.openai_job_specific_adjuster import _fetch_job_description


class TestCVAdjusterBase:
    """Tests for the CVAdjuster abstract base class."""
    
    def test_cvadjuster_is_abstract(self):
        """CVAdjuster cannot be instantiated directly."""
        with pytest.raises(TypeError):
            CVAdjuster()
    
    def test_cvadjuster_requires_name_method(self):
        """Concrete adjuster must implement name() method."""
        with pytest.raises(TypeError):
            class IncompleteAdjuster(CVAdjuster):
                def description(self):
                    return "Test"
                def adjust(self, cv_data, **kwargs):
                    return cv_data
            
            IncompleteAdjuster()
    
    def test_cvadjuster_requires_description_method(self):
        """Concrete adjuster must implement description() method."""
        with pytest.raises(TypeError):
            class IncompleteAdjuster(CVAdjuster):
                def name(self):
                    return "test"
                def adjust(self, cv_data, **kwargs):
                    return cv_data
            
            IncompleteAdjuster()
    
    def test_cvadjuster_requires_adjust_method(self):
        """Concrete adjuster must implement adjust() method."""
        with pytest.raises(TypeError):
            class IncompleteAdjuster(CVAdjuster):
                def name(self):
                    return "test"
                def description(self):
                    return "Test"
            
            IncompleteAdjuster()
    
    def test_cvadjuster_validate_params_has_default_implementation(self):
        """validate_params has a default implementation that does nothing."""
        class TestAdjuster(CVAdjuster):
            def name(self):
                return "test"
            def description(self):
                return "Test"
            def adjust(self, cv_data, **kwargs):
                return cv_data
        
        adjuster = TestAdjuster()
        # Should not raise any exception with default implementation
        adjuster.validate_params(arbitrary_param="value")
    
    def test_cvadjuster_concrete_implementation_all_methods(self):
        """Test a complete concrete implementation of CVAdjuster."""
        class FullAdjuster(CVAdjuster):
            def name(self):
                return "full-test-adjuster"
            
            def description(self):
                return "A fully implemented test adjuster"
            
            def adjust(self, cv_data, **kwargs):
                cv_data['adjusted'] = True
                return cv_data
            
            def validate_params(self, **kwargs):
                if 'required' not in kwargs:
                    raise ValueError("Missing required param")
        
        adjuster = FullAdjuster()
        
        # Test all methods work
        assert adjuster.name() == "full-test-adjuster"
        assert adjuster.description() == "A fully implemented test adjuster"
        
        cv = {"original": True}
        result = adjuster.adjust(cv)
        assert result['adjusted'] is True
        
        # Validate works
        adjuster.validate_params(required="value")
    
    def test_cvadjuster_validate_params_can_be_overridden(self):
        """Subclasses can override validate_params."""
        class StrictAdjuster(CVAdjuster):
            def name(self):
                return "strict"
            def description(self):
                return "Strict test adjuster"
            def adjust(self, cv_data, **kwargs):
                return cv_data
            def validate_params(self, **kwargs):
                if 'required_param' not in kwargs:
                    raise ValueError("required_param is required")
        
        adjuster = StrictAdjuster()
        
        # Should pass with required param
        adjuster.validate_params(required_param="value")
        
        # Should fail without required param
        with pytest.raises(ValueError, match="required_param is required"):
            adjuster.validate_params(other_param="value")


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
        
        try:
            adjuster = get_adjuster('custom-test')
            assert adjuster is not None
            assert adjuster.name() == 'custom-test'
        finally:
            # Clean up the custom adjuster
            unregister_adjuster('custom-test')


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
    
    @patch('cvextract.adjusters.openai_company_research_adjuster._research_company_profile')
    @patch('cvextract.adjusters.openai_company_research_adjuster._build_system_prompt')
    @patch('cvextract.adjusters.openai_company_research_adjuster.MLAdjuster')
    @patch('cvextract.adjusters.openai_company_research_adjuster.get_verifier')
    def test_adjust_calls_ml_adjuster(self, mock_get_verifier, mock_ml_adjuster, 
                                       mock_build_prompt, mock_research):
        """adjust should delegate to MLAdjuster after researching company."""
        # Setup mocks for research and prompt building
        mock_research.return_value = {"company": "Test Corp"}
        mock_build_prompt.return_value = "System prompt for Test Corp"
        
        # Setup MLAdjuster mock
        mock_ml_instance = MagicMock()
        mock_ml_instance.adjust.return_value = {"adjusted": True}
        mock_ml_adjuster.return_value = mock_ml_instance
        
        # Setup verifier mock
        mock_verifier = MagicMock()
        mock_verifier.verify.return_value = MagicMock(ok=True)
        mock_get_verifier.return_value = mock_verifier
        
        adjuster = OpenAICompanyResearchAdjuster(model="test-model", api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        result = adjuster.adjust(cv_data, customer_url="https://example.com")
        
        # Should return the adjusted result
        assert result == {"adjusted": True}
        
        # Verify MLAdjuster was called with system_prompt and user_context
        mock_ml_instance.adjust.assert_called_once()
        call_args = mock_ml_instance.adjust.call_args
        assert call_args[0][0] == cv_data  # cv_data
        assert call_args[0][1] == "System prompt for Test Corp"  # system_prompt
        assert 'user_context' in call_args[1]  # user_context kwarg


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
        # Override the API key to ensure it's None (in case OPENAI_API_KEY env var is set)
        adjuster._api_key = None
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        # Without API key, should return original data
        result = adjuster.adjust(cv_data, job_description="Test job")
        assert result == cv_data
    
    def test_adjust_missing_api_key(self):
        """adjust should return original CV when API key is missing."""
        adjuster = OpenAIJobSpecificAdjuster(api_key=None)
        # Override the API key to ensure it's None (in case OPENAI_API_KEY env var is set)
        adjuster._api_key = None
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        result = adjuster.adjust(cv_data, job_description="Test job")
        assert result == cv_data
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI', None)
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_openai_none_in_adjust_method(self, mock_format):
        """adjust should check if OpenAI is None and return original CV."""
        mock_format.return_value = "System prompt"
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        result = adjuster.adjust(cv_data, job_description="Test job")
        assert result == cv_data
    
    def test_adjust_with_openai_not_installed(self, monkeypatch):
        """adjust should handle case where OpenAI module is not installed (monkeypatch version)."""
        # Mock the OpenAI module as None to simulate it not being installed
        monkeypatch.setattr(
            'cvextract.adjusters.openai_job_specific_adjuster.OpenAI',
            None
        )
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        result = adjuster.adjust(cv_data, job_description="Test job")
        assert result == cv_data
    
    def test_adjust_second_openai_check_unreachable(self):
        """The second OpenAI check at line 159 is logically unreachable by design.
        
        The first check (line 131) already handles the case where OpenAI is None,
        so if code reaches line 159, OpenAI cannot be None (it would have returned
        at line 131). This second check is defensive/redundant but impossible to reach
        in normal operation without code modification between the two checks.
        """
        # This documents the limitation: we can achieve 98% coverage (95/97 statements)
        # with the remaining 2 statements (lines 160-161) being unreachable by design.
        pass
    
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
        
        adjusted_cv = {
            "identity": {
                "name": "John",
                "title": "Software Engineer",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe"
            },
            "sidebar": {},
            "overview": "Adjusted",
            "experiences": []
        }
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(adjusted_cv)))]
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key", model="gpt-4o-mini")
        cv_data = {
            "identity": {"name": "", "title": "", "full_name": "", "first_name": "", "last_name": ""},
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        
        result = adjuster.adjust(cv_data, job_description="Test job")
        assert "John" in str(result)  # Verify the adjusted data is in result
        # Client should be created once (not in the retry loop)
        mock_openai_class.assert_called_once_with(api_key="test-key", max_retries=5)
    
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
        """adjust should return original CV if JSON response is not a dict."""
        mock_format.return_value = "System prompt"
        
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content='[1, 2, 3]'))]
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        result = adjuster.adjust(cv_data, job_description="Test job")
        assert result == cv_data  # Should return original since schema validation expects dict
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_empty_choices_list(self, mock_format, mock_openai_class):
        """adjust should return original CV if completion has no choices."""
        mock_format.return_value = "System prompt"
        
        mock_completion = MagicMock()
        mock_completion.choices = []  # Empty choices list
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        result = adjuster.adjust(cv_data, job_description="Test job")
        assert result == cv_data
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_rate_limit_retry_succeeds(self, mock_format, mock_openai_class):
        """adjust should retry on rate limit and eventually succeed."""
        mock_format.return_value = "System prompt"
        
        adjusted_cv = {
            "identity": {
                "name": "Adjusted",
                "title": "Engineer",
                "full_name": "Test User",
                "first_name": "Test",
                "last_name": "User"
            },
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        
        # First call fails with rate limit, second call succeeds
        mock_completion_success = MagicMock()
        mock_completion_success.choices = [MagicMock(message=MagicMock(content=json.dumps(adjusted_cv)))]
        
        from openai import RateLimitError
        mock_client = MagicMock()
        # Mock the create method to fail once with RateLimitError, then succeed
        mock_client.chat.completions.create.side_effect = [
            RateLimitError("Rate limited", response=MagicMock(status_code=429), body={}),
            mock_completion_success
        ]
        mock_openai_class.return_value = mock_client
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {
            "identity": {"name": "", "title": "", "full_name": "", "first_name": "", "last_name": ""},
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        
        result = adjuster.adjust(cv_data, job_description="Test job")
        assert "Adjusted" in str(result)  # Should succeed on retry
        # Should have called create twice
        assert mock_client.chat.completions.create.call_count == 2
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_rate_limit_exhausts_retries(self, mock_format, mock_openai_class):
        """adjust should return original CV if rate limits exhaust retries."""
        mock_format.return_value = "System prompt"
        
        from openai import RateLimitError
        mock_client = MagicMock()
        # Always fail with rate limit
        mock_client.chat.completions.create.side_effect = RateLimitError(
            "Rate limited", response=MagicMock(status_code=429), body={}
        )
        mock_openai_class.return_value = mock_client
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        result = adjuster.adjust(cv_data, job_description="Test job")
        assert result == cv_data
        # Should have exhausted max_retries (3)
        assert mock_client.chat.completions.create.call_count == 3
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_non_rate_limit_exception(self, mock_format, mock_openai_class):
        """adjust should not retry on non-rate-limit exceptions."""
        mock_format.return_value = "System prompt"
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = ValueError("Invalid input")
        mock_openai_class.return_value = mock_client
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        result = adjuster.adjust(cv_data, job_description="Test job")
        assert result == cv_data
        # Should have called create only once (no retry)
        assert mock_client.chat.completions.create.call_count == 1
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_json_parsed_to_none(self, mock_format, mock_openai_class):
        """adjust should return original CV if JSON parses to None."""
        mock_format.return_value = "System prompt"
        
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content='null'))]
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        result = adjuster.adjust(cv_data, job_description="Test job")
        assert result == cv_data
    
    def test_validate_params_accepts_hyphenated_job_url(self):
        """validate_params should accept job-url (hyphenated) parameter."""
        adjuster = OpenAIJobSpecificAdjuster()
        adjuster.validate_params(**{"job-url": "https://careers.example.com/job/123"})
    
    def test_validate_params_accepts_hyphenated_job_description(self):
        """validate_params should accept job-description (hyphenated) parameter."""
        adjuster = OpenAIJobSpecificAdjuster()
        adjuster.validate_params(**{"job-description": "Job description text"})
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI', None)
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_openai_none_before_client_creation(self, mock_format):
        """adjust should return original CV if OpenAI is None during adjust call."""
        mock_format.return_value = "System prompt"
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        result = adjuster.adjust(cv_data, job_description="Test job")
        assert result == cv_data
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.time')
    def test_adjust_rate_limit_with_sleep(self, mock_time, mock_format, mock_openai_class):
        """adjust should sleep with exponential backoff on rate limit retry."""
        mock_format.return_value = "System prompt"
        
        adjusted_cv = {
            "identity": {
                "name": "Adjusted",
                "title": "Engineer",
                "full_name": "Test User",
                "first_name": "Test",
                "last_name": "User"
            },
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        
        mock_completion_success = MagicMock()
        mock_completion_success.choices = [MagicMock(message=MagicMock(content=json.dumps(adjusted_cv)))]
        
        from openai import RateLimitError
        mock_client = MagicMock()
        # Fail twice with rate limit, then succeed
        mock_client.chat.completions.create.side_effect = [
            RateLimitError("Rate limited", response=MagicMock(status_code=429), body={}),
            RateLimitError("Rate limited", response=MagicMock(status_code=429), body={}),
            mock_completion_success
        ]
        mock_openai_class.return_value = mock_client
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {
            "identity": {"name": "", "title": "", "full_name": "", "first_name": "", "last_name": ""},
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        
        result = adjuster.adjust(cv_data, job_description="Test job")
        assert "Adjusted" in str(result)
        # Should have called sleep twice with exponential backoff (2.0, 4.0)
        assert mock_time.sleep.call_count == 2
        sleep_calls = [call[0][0] for call in mock_time.sleep.call_args_list]
        assert sleep_calls[0] == 2.0  # 2.0 * (2^0)
        assert sleep_calls[1] == 4.0  # 2.0 * (2^1)
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_completion_choices_false(self, mock_format, mock_openai_class):
        """adjust should handle completion with falsy choices."""
        mock_format.return_value = "System prompt"
        
        mock_completion = MagicMock()
        mock_completion.choices = False  # Falsy but not None or empty list
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        result = adjuster.adjust(cv_data, job_description="Test job")
        assert result == cv_data
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_with_both_job_url_and_description(self, mock_format, mock_openai_class):
        """adjust should prefer job_description when both job_url and job_description are provided."""
        mock_format.return_value = "System prompt"
        
        adjusted_cv = {
            "identity": {
                "name": "Test",
                "title": "Engineer",
                "full_name": "Test User",
                "first_name": "Test",
                "last_name": "User"
            },
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(adjusted_cv)))]
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {
            "identity": {"name": "", "title": "", "full_name": "", "first_name": "", "last_name": ""},
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        
        # Pass both job_url and job_description - should use job_description
        result = adjuster.adjust(
            cv_data,
            job_description="Direct description",
            job_url="https://example.com/job/123"
        )
        assert result == adjusted_cv
        # format_prompt should be called with the direct job_description, not fetched from URL
        mock_format.assert_called_once_with("job_specific_prompt", job_description="Direct description")
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_rate_limit_with_429_in_error_message(self, mock_format, mock_openai_class):
        """adjust should detect rate limit by '429' in error message."""
        mock_format.return_value = "System prompt"
        
        adjusted_cv = {
            "identity": {
                "name": "Adjusted",
                "title": "Engineer",
                "full_name": "Test User",
                "first_name": "Test",
                "last_name": "User"
            },
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        mock_completion_success = MagicMock()
        mock_completion_success.choices = [MagicMock(message=MagicMock(content=json.dumps(adjusted_cv)))]
        
        mock_client = MagicMock()
        # Fail with error containing '429' in message (not RateLimitError)
        mock_client.chat.completions.create.side_effect = [
            Exception("HTTP 429 Too Many Requests"),
            mock_completion_success
        ]
        mock_openai_class.return_value = mock_client
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {
            "identity": {"name": "", "title": "", "full_name": "", "first_name": "", "last_name": ""},
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        
        result = adjuster.adjust(cv_data, job_description="Test job")
        assert "Adjusted" in str(result)
        # Should have retried after seeing 429
        assert mock_client.chat.completions.create.call_count == 2
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.time')
    def test_adjust_final_retry_attempt_rate_limit(self, mock_time, mock_format, mock_openai_class):
        """adjust should not retry when rate limit occurs on the final attempt."""
        mock_format.return_value = "System prompt"
        
        from openai import RateLimitError
        mock_client = MagicMock()
        # Fail with rate limit on the final attempt (attempt 2 out of 3, so attempt < max_retries - 1 is False)
        mock_client.chat.completions.create.side_effect = [
            RateLimitError("Rate limited", response=MagicMock(status_code=429), body={}),
            RateLimitError("Rate limited", response=MagicMock(status_code=429), body={}),
            RateLimitError("Rate limited", response=MagicMock(status_code=429), body={}),
        ]
        mock_openai_class.return_value = mock_client
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        result = adjuster.adjust(cv_data, job_description="Test job")
        assert result == cv_data
        # Should have called sleep only twice (for attempts 0 and 1, not for attempt 2)
        assert mock_time.sleep.call_count == 2
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.get_verifier')
    def test_adjust_schema_validation_fails(self, mock_get_verifier, mock_format, mock_openai_class):
        """adjust should return original CV if adjusted CV fails schema validation."""
        mock_format.return_value = "System prompt"
        
        adjusted_cv = {
            "identity": {"name": "John"},  # Missing required fields for schema
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(adjusted_cv)))]
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        
        # Mock verifier to return validation failure
        mock_verifier = MagicMock()
        mock_verifier.verify.return_value = MagicMock(ok=False, errors=["identity missing required field: title"])
        mock_get_verifier.return_value = mock_verifier
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {
            "identity": {"name": "", "title": "", "full_name": "", "first_name": "", "last_name": ""},
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        
        result = adjuster.adjust(cv_data, job_description="Test job")
        assert result == cv_data  # Should return original due to validation failure
        mock_get_verifier.assert_called_once_with("cv-schema-verifier")
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.requests', None)
    def test_fetch_job_description_requests_not_available(self):
        """_fetch_job_description should return empty string if requests is not available."""
        from cvextract.adjusters.openai_job_specific_adjuster import _fetch_job_description
        
        result = _fetch_job_description("https://example.com/job")
        assert result == ""
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.requests')
    def test_fetch_job_description_non_200_status(self, mock_requests):
        """_fetch_job_description should return empty string if status code is not 200."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_requests.get.return_value = mock_response
        
        from cvextract.adjusters.openai_job_specific_adjuster import _fetch_job_description
        result = _fetch_job_description("https://example.com/job")
        
        assert result == ""
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.requests')
    def test_fetch_job_description_empty_response(self, mock_requests):
        """_fetch_job_description should return empty string if response text is empty."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_requests.get.return_value = mock_response
        
        from cvextract.adjusters.openai_job_specific_adjuster import _fetch_job_description
        result = _fetch_job_description("https://example.com/job")
        
        assert result == ""
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.requests')
    def test_fetch_job_description_cleans_html(self, mock_requests):
        """_fetch_job_description should remove HTML tags and clean whitespace."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><p>Senior  Engineer</p><script>alert('x')</script></body></html>"
        mock_requests.get.return_value = mock_response
        
        from cvextract.adjusters.openai_job_specific_adjuster import _fetch_job_description
        result = _fetch_job_description("https://example.com/job")
        
        assert "Senior Engineer" in result
        assert "script" not in result.lower() or "alert" not in result
        assert "  " not in result  # No double spaces
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.requests')
    def test_fetch_job_description_truncates_long_content(self, mock_requests):
        """_fetch_job_description should truncate content to 5000 chars."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "A" * 10000  # 10000 characters
        mock_requests.get.return_value = mock_response
        
        from cvextract.adjusters.openai_job_specific_adjuster import _fetch_job_description
        result = _fetch_job_description("https://example.com/job")
        
        assert len(result) == 5000
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.requests')
    def test_fetch_job_description_request_exception(self, mock_requests):
        """_fetch_job_description should return empty string on request exception."""
        mock_requests.get.side_effect = Exception("Network error")
        
        from cvextract.adjusters.openai_job_specific_adjuster import _fetch_job_description
        result = _fetch_job_description("https://example.com/job")
        
        assert result == ""
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.get_verifier')
    def test_adjust_schema_validation_exception(self, mock_get_verifier, mock_format, mock_openai_class):
        """adjust should return original CV if schema validation raises exception."""
        mock_format.return_value = "System prompt"
        
        adjusted_cv = {
            "identity": {
                "name": "John",
                "title": "Engineer",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe"
            },
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(adjusted_cv)))]
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        
        # Mock get_verifier to raise exception
        mock_get_verifier.side_effect = Exception("Verifier not found")
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {
            "identity": {"name": "", "title": "", "full_name": "", "first_name": "", "last_name": ""},
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        
        # Should handle exception and return original CV
        result = adjuster.adjust(cv_data, job_description="Test job")
        assert result == cv_data  # Returns original due to validation exception


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
    
    def test_adjust_requires_name_parameter(self):
        """Adjust stage should require name parameter."""
        from cvextract.cli_gather import gather_user_requirements
        import pytest
        
        with pytest.raises(ValueError, match="requires 'name' parameter"):
            gather_user_requirements([
                "--extract", "source=/path/to/cv.docx",
                "--adjust", "customer-url=https://example.com",
                "--target", "/output"
            ])
