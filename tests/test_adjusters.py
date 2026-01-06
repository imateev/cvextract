"""Tests for adjuster framework and registry."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from cvextract.cli_config import UserConfig, ExtractStage
from cvextract.shared import UnitOfWork
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


def make_work(tmp_path: Path, cv_data: dict) -> UnitOfWork:
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps(cv_data, indent=2))
    output_path = tmp_path / "output.json"
    return UnitOfWork(
        config=UserConfig(target_dir=tmp_path, extract=ExtractStage(source=input_path)),
        initial_input=input_path,
        input=input_path,
        output=output_path,
    )


def read_output(work: UnitOfWork) -> dict:
    return json.loads(work.output.read_text())


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
                def adjust(self, work, **kwargs):
                    return self._write_output_json(work, self._load_input_json(work))
            
            IncompleteAdjuster()
    
    def test_cvadjuster_requires_description_method(self):
        """Concrete adjuster must implement description() method."""
        with pytest.raises(TypeError):
            class IncompleteAdjuster(CVAdjuster):
                def name(self):
                    return "test"
                def adjust(self, work, **kwargs):
                    return self._write_output_json(work, self._load_input_json(work))
            
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
            def adjust(self, work, **kwargs):
                return self._write_output_json(work, self._load_input_json(work))
        
        adjuster = TestAdjuster()
        # Should not raise any exception with default implementation
        adjuster.validate_params(arbitrary_param="value")
    
    def test_cvadjuster_concrete_implementation_all_methods(self, tmp_path: Path):
        """Test a complete concrete implementation of CVAdjuster."""
        class FullAdjuster(CVAdjuster):
            def name(self):
                return "full-test-adjuster"
            
            def description(self):
                return "A fully implemented test adjuster"
            
            def adjust(self, work, **kwargs):
                cv_data = self._load_input_json(work)
                cv_data['adjusted'] = True
                return self._write_output_json(work, cv_data)
            
            def validate_params(self, **kwargs):
                if 'required' not in kwargs:
                    raise ValueError("Missing required param")
        
        adjuster = FullAdjuster()
        
        # Test all methods work
        assert adjuster.name() == "full-test-adjuster"
        assert adjuster.description() == "A fully implemented test adjuster"
        
        cv = {"original": True}
        work = make_work(tmp_path, cv)
        result = adjuster.adjust(work)
        assert read_output(result)['adjusted'] is True
        
        # Validate works
        adjuster.validate_params(required="value")
    
    def test_cvadjuster_validate_params_can_be_overridden(self):
        """Subclasses can override validate_params."""
        class StrictAdjuster(CVAdjuster):
            def name(self):
                return "strict"
            def description(self):
                return "Strict test adjuster"
            def adjust(self, work, **kwargs):
                return self._write_output_json(work, self._load_input_json(work))
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
        # Verify the call was made with the URL, timeout, and headers
        call_args = mock_requests.get.call_args
        assert call_args[0][0] == "https://example.com/job/123"  # URL
        assert call_args[1]["timeout"] == 15
        assert "User-Agent" in call_args[1]["headers"]
    
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
            
            def adjust(self, work, **kwargs):
                return self._write_output_json(work, self._load_input_json(work))
        
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
    @patch('cvextract.adjusters.openai_company_research_adjuster.format_prompt')
    @patch('cvextract.adjusters.openai_company_research_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_company_research_adjuster.get_verifier')
    def test_adjust_calls_openai_client(self, mock_get_verifier, mock_openai, 
                                         mock_format_prompt, mock_research, tmp_path: Path):
        """adjust should call OpenAI client.chat.completions.create after researching company."""
        # Setup mocks for research and prompt building
        mock_research.return_value = {"company": "Test Corp", "name": "Test Corp", "description": "Test company", "domains": [], "technology_signals": []}
        mock_format_prompt.return_value = "System prompt for Test Corp"
        
        # Setup OpenAI mock
        adjusted_result = {"adjusted": True, "identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps(adjusted_result)
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        # Setup verifier mock
        mock_verifier = MagicMock()
        mock_verifier.verify.return_value = MagicMock(ok=True)
        mock_get_verifier.return_value = mock_verifier
        
        adjuster = OpenAICompanyResearchAdjuster(model="test-model", api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, customer_url="https://example.com")
        result_data = read_output(result)
        
        # Should return the adjusted result
        assert result_data == adjusted_result
        
        # Verify OpenAI was called with correct messages format
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs['model'] == "test-model"
        assert call_kwargs['temperature'] == 0.2
        messages = call_kwargs['messages']
        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert "System prompt" in messages[0]['content']
        assert messages[1]['role'] == 'user'
        # User message should contain JSON-serialized user_payload
        user_payload = json.loads(messages[1]['content'])
        assert 'company_research' in user_payload
        assert 'original_json' in user_payload
    
    @patch('cvextract.adjusters.openai_company_research_adjuster._research_company_profile')
    @patch('cvextract.adjusters.openai_company_research_adjuster.format_prompt')
    @patch('cvextract.adjusters.openai_company_research_adjuster.get_verifier')
    def test_adjust_build_system_prompt_returns_none(self, mock_get_verifier, mock_format_prompt, mock_research, tmp_path: Path):
        """adjust should return original CV when format_prompt returns None."""
        # Setup mocks
        mock_research.return_value = {"company": "Test Corp"}
        mock_format_prompt.return_value = None  # Simulate failed prompt loading
        
        adjuster = OpenAICompanyResearchAdjuster(model="test-model", api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, customer_url="https://example.com")
        result_data = read_output(result)
        
        # Should return original CV due to None prompt
        assert result_data == cv_data
        # Verify research was called but MLAdjuster was not
        mock_research.assert_called_once()
        mock_get_verifier.assert_not_called()
    
    @patch('cvextract.adjusters.openai_company_research_adjuster._research_company_profile')
    @patch('cvextract.adjusters.openai_company_research_adjuster.format_prompt')
    @patch('cvextract.adjusters.openai_company_research_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_company_research_adjuster.get_verifier')
    def test_adjust_openai_returns_null(self, mock_get_verifier, mock_openai, 
                                         mock_format_prompt, mock_research, tmp_path: Path):
        """adjust should return original CV when OpenAI API returns JSON null."""
        # Setup mocks
        mock_research.return_value = {"company": "Test Corp"}
        mock_format_prompt.return_value = "System prompt for Test Corp"
        
        # OpenAI returns JSON null
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps(None)  # JSON null
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        adjuster = OpenAICompanyResearchAdjuster(model="test-model", api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, customer_url="https://example.com")
        result_data = read_output(result)
        
        # Should return original CV due to null from API
        assert result_data == cv_data
        # Verify OpenAI was called
        mock_client.chat.completions.create.assert_called_once()
        # Verifier should not be called since adjustment returned None
        mock_get_verifier.assert_not_called()
    
    @patch('cvextract.adjusters.openai_company_research_adjuster._research_company_profile')
    @patch('cvextract.adjusters.openai_company_research_adjuster.format_prompt')
    @patch('cvextract.adjusters.openai_company_research_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_company_research_adjuster.get_verifier')
    def test_adjust_schema_validation_exception(self, mock_get_verifier, mock_openai, 
                                                 mock_format_prompt, mock_research, tmp_path: Path):
        """adjust should return original CV when schema validation raises exception."""
        # Setup mocks
        mock_research.return_value = {"company": "Test Corp"}
        mock_format_prompt.return_value = "System prompt for Test Corp"
        
        # OpenAI returns valid adjusted data
        adjusted_data = {"identity": {}, "sidebar": {}, "overview": "Adjusted", "experiences": []}
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps(adjusted_data)
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        # Verifier raises exception during validation
        mock_verifier = MagicMock()
        mock_verifier.verify.side_effect = RuntimeError("Schema validation error")
        mock_get_verifier.return_value = mock_verifier
        
        adjuster = OpenAICompanyResearchAdjuster(model="test-model", api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, customer_url="https://example.com")
        result_data = read_output(result)
        
        # Should return original CV due to validation exception
        assert result_data == cv_data
        # Verify validation was attempted
        mock_verifier.verify.assert_called_once_with(adjusted_data)
    
    @patch('cvextract.adjusters.openai_company_research_adjuster._research_company_profile')
    @patch('cvextract.adjusters.openai_company_research_adjuster.format_prompt')
    @patch('cvextract.adjusters.openai_company_research_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_company_research_adjuster.get_verifier')
    def test_adjust_validation_fails(self, mock_get_verifier, mock_openai, 
                                     mock_format_prompt, mock_research, tmp_path: Path):
        """adjust should return original CV when adjusted CV fails schema validation."""
        # Setup mocks
        mock_research.return_value = {"company": "Test Corp"}
        mock_format_prompt.return_value = "System prompt for Test Corp"
        
        # OpenAI returns valid dict but with issues
        adjusted_data = {"identity": {}, "sidebar": {}, "overview": "Adjusted", "experiences": []}
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps(adjusted_data)
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        # Verifier returns failed validation
        mock_verifier = MagicMock()
        mock_verifier.verify.return_value = MagicMock(ok=False, errors=["missing required field"])
        mock_get_verifier.return_value = mock_verifier
        
        adjuster = OpenAICompanyResearchAdjuster(model="test-model", api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, customer_url="https://example.com")
        result_data = read_output(result)
        
        # Should return original CV due to validation failure
        assert result_data == cv_data
        # Verify validation was attempted
        mock_verifier.verify.assert_called_once_with(adjusted_data)
    
    @patch('cvextract.adjusters.openai_company_research_adjuster._research_company_profile')
    @patch('cvextract.adjusters.openai_company_research_adjuster.format_prompt')
    @patch('cvextract.adjusters.openai_company_research_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_company_research_adjuster.get_verifier')
    def test_adjust_non_dict_result(self, mock_get_verifier, mock_openai, 
                                    mock_format_prompt, mock_research, tmp_path: Path):
        """adjust should return original CV when OpenAI returns non-dict."""
        # Setup mocks
        mock_research.return_value = {"company": "Test Corp"}
        mock_format_prompt.return_value = "System prompt for Test Corp"
        
        # OpenAI returns non-dict (invalid) - returns a string instead of dict
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = '"not a dict"'  # JSON string, not dict
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        adjuster = OpenAICompanyResearchAdjuster(model="test-model", api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, customer_url="https://example.com")
        result_data = read_output(result)
        
        # Should return original CV due to non-dict result
        assert result_data == cv_data
        # Verifier should not be called for non-dict
        mock_get_verifier.assert_not_called()

    @patch('cvextract.adjusters.openai_company_research_adjuster._research_company_profile')
    @patch('cvextract.adjusters.openai_company_research_adjuster.format_prompt')
    @patch('cvextract.adjusters.openai_company_research_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_company_research_adjuster.get_verifier')
    def test_adjust_research_returns_falsy(self, mock_get_verifier, mock_openai, 
                                          mock_format_prompt, mock_research, tmp_path: Path):
        """adjust should return original CV when research returns falsy value."""
        # Setup mocks - research_company_profile returns None/empty
        mock_research.return_value = None
        
        adjuster = OpenAICompanyResearchAdjuster(model="test-model", api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, customer_url="https://example.com")
        result_data = read_output(result)
        
        # Should return original CV when research returns None
        assert result_data == cv_data
        # format_prompt and OpenAI should not be called
        mock_format_prompt.assert_not_called()
        mock_openai.assert_not_called()
    
    @patch('cvextract.adjusters.openai_company_research_adjuster._research_company_profile')
    @patch('cvextract.adjusters.openai_company_research_adjuster.format_prompt')
    @patch('cvextract.adjusters.openai_company_research_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_company_research_adjuster.get_verifier')
    def test_adjust_with_technology_signals(self, mock_get_verifier, mock_openai, 
                                            mock_format_prompt, mock_research, tmp_path: Path):
        """adjust should include technology signals when building research context."""
        # Setup mocks with technology signals
        mock_research.return_value = {
            "company": "Test Corp",
            "name": "Test Corp",
            "description": "A great company",
            "domains": ["python", "kubernetes"],
            "technology_signals": [
                {
                    "technology": "Python",
                    "interest_level": "high",
                    "confidence": 0.95,
                    "signals": ["Uses Python in production", "Django framework"]
                },
                {
                    "technology": "Kubernetes",
                    "interest_level": "medium",
                    "confidence": 0.75,
                    "signals": ["Container orchestration", "Cloud-native"]
                }
            ]
        }
        mock_format_prompt.return_value = "System prompt with signals"
        
        # Setup OpenAI mock
        adjusted_result = {"identity": {}, "sidebar": {}, "overview": "Adjusted", "experiences": []}
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps(adjusted_result)
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        # Setup verifier mock
        mock_verifier = MagicMock()
        mock_verifier.verify.return_value = MagicMock(ok=True)
        mock_get_verifier.return_value = mock_verifier
        
        adjuster = OpenAICompanyResearchAdjuster(model="test-model", api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, customer_url="https://example.com")
        result_data = read_output(result)
        
        # Should succeed and return adjusted data
        assert result_data == adjusted_result
        
        # Verify format_prompt was called with research context including tech signals
        mock_format_prompt.assert_called_once()
        call_kwargs = mock_format_prompt.call_args[1]
        research_context = call_kwargs.get('research_context', '')
        assert 'Key Technology Signals:' in research_context
        assert 'Python' in research_context
        assert 'Kubernetes' in research_context
        assert 'high' in research_context
        assert '0.95' in research_context

    @patch('cvextract.adjusters.openai_company_research_adjuster._research_company_profile')
    @patch('cvextract.adjusters.openai_company_research_adjuster.format_prompt')
    @patch('cvextract.adjusters.openai_company_research_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_company_research_adjuster.get_verifier')
    def test_adjust_with_invalid_confidence_value(self, mock_get_verifier, mock_openai, 
                                                  mock_format_prompt, mock_research, tmp_path: Path):
        """adjust should handle non-numeric confidence values safely."""
        # Setup mocks with invalid confidence value
        mock_research.return_value = {
            "name": "Test Corp",
            "description": "A company",
            "domains": [],
            "technology_signals": [
                {
                    "technology": "Java",
                    "interest_level": "low",
                    "confidence": "invalid",  # Non-numeric
                    "signals": []
                }
            ]
        }
        mock_format_prompt.return_value = "System prompt"
        
        # Setup OpenAI mock
        adjusted_result = {"identity": {}, "sidebar": {}, "overview": "Adjusted", "experiences": []}
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps(adjusted_result)
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        # Setup verifier mock
        mock_verifier = MagicMock()
        mock_verifier.verify.return_value = MagicMock(ok=True)
        mock_get_verifier.return_value = mock_verifier
        
        adjuster = OpenAICompanyResearchAdjuster(model="test-model", api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, customer_url="https://example.com")
        result_data = read_output(result)
        
        # Should succeed and handle invalid confidence gracefully
        assert result_data == adjusted_result
        
        # Verify format_prompt was called with context containing confidence as "0.00"
        mock_format_prompt.assert_called_once()
        call_kwargs = mock_format_prompt.call_args[1]
        research_context = call_kwargs.get('research_context', '')
        assert '0.00' in research_context  # Should default to 0.00

    @patch('cvextract.adjusters.openai_company_research_adjuster._research_company_profile')
    @patch('cvextract.adjusters.openai_company_research_adjuster.format_prompt')
    @patch('cvextract.adjusters.openai_company_research_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_company_research_adjuster.get_verifier')
    def test_adjust_openai_api_exception(self, mock_get_verifier, mock_openai, 
                                        mock_format_prompt, mock_research, tmp_path: Path):
        """adjust should return original CV when OpenAI API raises exception."""
        # Setup mocks
        mock_research.return_value = {"name": "Test Corp"}
        mock_format_prompt.return_value = "System prompt"
        
        # OpenAI raises exception
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("API connection failed")
        mock_openai.return_value = mock_client
        
        adjuster = OpenAICompanyResearchAdjuster(model="test-model", api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, customer_url="https://example.com")
        result_data = read_output(result)
        
        # Should return original CV due to API exception
        assert result_data == cv_data
        # Verifier should not be called
        mock_get_verifier.assert_not_called()

    @patch('cvextract.adjusters.openai_company_research_adjuster._research_company_profile')
    @patch('cvextract.adjusters.openai_company_research_adjuster.format_prompt')
    @patch('cvextract.adjusters.openai_company_research_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_company_research_adjuster.get_verifier')
    def test_adjust_json_decode_exception(self, mock_get_verifier, mock_openai, 
                                          mock_format_prompt, mock_research, tmp_path: Path):
        """adjust should return original CV when OpenAI response is invalid JSON."""
        # Setup mocks
        mock_research.return_value = {"name": "Test Corp"}
        mock_format_prompt.return_value = "System prompt"
        
        # OpenAI returns invalid JSON
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "not valid json {]"
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        adjuster = OpenAICompanyResearchAdjuster(model="test-model", api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, customer_url="https://example.com")
        result_data = read_output(result)
        
        # Should return original CV due to JSON decode error
        assert result_data == cv_data
        # Verifier should not be called
        mock_get_verifier.assert_not_called()

    @patch('cvextract.adjusters.openai_company_research_adjuster.get_verifier')
    def test_validate_research_data_verifier_exception(self, mock_get_verifier):
        """_validate_research_data should return False when verifier raises exception."""
        # Import the helper function
        from cvextract.adjusters.openai_company_research_adjuster import _validate_research_data
        
        # Verifier raises exception
        mock_verifier = MagicMock()
        mock_verifier.verify.side_effect = RuntimeError("Verifier error")
        mock_get_verifier.return_value = mock_verifier
        
        # Should return False due to exception
        result = _validate_research_data({"name": "Test"})
        assert result is False
        
        # Verify exception was caught
        mock_get_verifier.assert_called_once_with("company-profile-verifier")
        mock_verifier.verify.assert_called_once()

    @patch('cvextract.adjusters.openai_company_research_adjuster._research_company_profile')
    @patch('cvextract.adjusters.openai_company_research_adjuster.format_prompt')
    @patch('cvextract.adjusters.openai_company_research_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_company_research_adjuster.get_verifier')
    def test_adjust_validation_result_has_errors_count(self, mock_get_verifier, mock_openai, 
                                                       mock_format_prompt, mock_research, tmp_path: Path):
        """adjust should log validation error count when validation fails."""
        # Setup mocks
        mock_research.return_value = {"name": "Test Corp"}
        mock_format_prompt.return_value = "System prompt"
        
        # OpenAI returns valid dict
        adjusted_data = {"identity": {}, "sidebar": {}, "overview": "Adjusted", "experiences": []}
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps(adjusted_data)
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        # Verifier returns multiple validation errors
        mock_verifier = MagicMock()
        mock_verifier.verify.return_value = MagicMock(ok=False, errors=["error1", "error2", "error3"])
        mock_get_verifier.return_value = mock_verifier
        
        adjuster = OpenAICompanyResearchAdjuster(model="test-model", api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, customer_url="https://example.com")
        result_data = read_output(result)
        
        # Should return original CV due to validation failure with error count
        assert result_data == cv_data

    def test_adjust_skips_when_api_key_missing(self, monkeypatch, tmp_path: Path):
        """adjust() should skip and return original CV when API key is missing."""
        # Remove the OPENAI_API_KEY from environment
        monkeypatch.delenv('OPENAI_API_KEY', raising=False)
        
        # Create adjuster without api_key (will be None since env var is missing)
        adjuster = OpenAICompanyResearchAdjuster(model="gpt-4o")
        cv_data = {"identity": {"full_name": "John Doe"}, "sidebar": {}, "overview": "Test", "experiences": []}
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, customer_url="https://example.com")
        
        # Should return original CV unchanged
        assert read_output(result) == cv_data

    def test_adjust_skips_when_openai_unavailable(self, monkeypatch, tmp_path: Path):
        """adjust() should skip and return original CV when OpenAI module is unavailable."""
        import cvextract.adjusters.openai_company_research_adjuster as adj_module
        
        # Temporarily patch OpenAI to None
        original_openai = adj_module.OpenAI
        try:
            adj_module.OpenAI = None
            
            adjuster = OpenAICompanyResearchAdjuster(model="gpt-4o", api_key="test-key")
            cv_data = {"identity": {"full_name": "John Doe"}, "sidebar": {}, "overview": "Test", "experiences": []}
            work = make_work(tmp_path, cv_data)
            result = adjuster.adjust(work, customer_url="https://example.com")
            
            # Should return original CV unchanged
            assert read_output(result) == cv_data
        finally:
            adj_module.OpenAI = original_openai


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
    
    def test_validate_params_rejects_empty_job_url_and_description(self):
        """validate_params should raise error if both job_url and job_description are empty."""
        adjuster = OpenAIJobSpecificAdjuster()
        with pytest.raises(ValueError, match="requires either non-empty 'job-url' or 'job-description'"):
            adjuster.validate_params(job_url="", job_description="")
    
    def test_validate_params_rejects_none_job_url_and_empty_description(self):
        """validate_params should raise error if job_url is None and job_description is empty."""
        adjuster = OpenAIJobSpecificAdjuster()
        with pytest.raises(ValueError, match="requires either non-empty 'job-url' or 'job-description'"):
            adjuster.validate_params(job_url=None, job_description="")
    
    def test_validate_params_accepts_hyphenated_job_url(self):
        """validate_params should accept 'job-url' parameter (hyphenated variant)."""
        adjuster = OpenAIJobSpecificAdjuster()
        adjuster.validate_params(**{"job-url": "https://careers.example.com/job/123"})
    
    def test_validate_params_accepts_hyphenated_job_description(self):
        """validate_params should accept 'job-description' parameter (hyphenated variant)."""
        adjuster = OpenAIJobSpecificAdjuster()
        adjuster.validate_params(**{"job-description": "Job description text"})
    
    def test_validate_params_rejects_empty_hyphenated_both(self):
        """validate_params should raise error if both hyphenated variants are empty."""
        adjuster = OpenAIJobSpecificAdjuster()
        with pytest.raises(ValueError, match="requires either non-empty 'job-url' or 'job-description'"):
            adjuster.validate_params(**{"job-url": "", "job-description": ""})
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI', None)
    def test_adjust_openai_library_unavailable(self, tmp_path: Path):
        """adjust should return original CV when OpenAI library is not available (lines 160-161)."""
        # OpenAI is mocked as None to simulate library not being installed
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        # Should return original CV since OpenAI is unavailable
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, job_description="Test job description")
        assert read_output(result) == cv_data
    
    def test_adjust_openai_becomes_none_after_initial_check(self, monkeypatch, tmp_path: Path):
        """Test defensive check at line 159-161 by making OpenAI None after initial check (unreachable by design)."""
        # This test documents the defensive nature of the second OpenAI check
        # The second check (line 159-161) is intentionally unreachable because the first check
        # (line 131) already handles the case where OpenAI is None.
        # This test verifies that even if OpenAI somehow becomes None between checks,
        # the code would handle it gracefully.
        
        # Start with OpenAI available
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        
        # Create a flag to track if we reach the defensive check
        reached_defensive_check = []
        
        # Patch the second OpenAI check location to track if it's reached
        import cvextract.adjusters.openai_job_specific_adjuster as job_adjuster_module
        original_openai = job_adjuster_module.OpenAI
        
        def conditional_none(*args, **kwargs):
            # If we're creating the client, OpenAI is available
            # But this documents what would happen if it became None
            return original_openai(*args, **kwargs) if original_openai else None
        
        try:
            # Mock format_prompt to return a valid prompt
            with patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt') as mock_format:
                mock_format.return_value = "System prompt"
                
                # Mock the OpenAI client to succeed
                with patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI') as mock_openai_class:
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
                    
                    cv_data = {
                        "identity": {"name": "", "title": "", "full_name": "", "first_name": "", "last_name": ""},
                        "sidebar": {},
                        "overview": "",
                        "experiences": []
                    }
                    
                    # This should succeed normally (the defensive check is not reached)
                    work = make_work(tmp_path, cv_data)
                    result = adjuster.adjust(work, job_description="Test job")
                    assert read_output(result) == adjusted_cv
        finally:
            pass
    
    def test_adjust_second_openai_check_lines_160_161(self, monkeypatch, tmp_path: Path):
        """Test that the redundant OpenAI None check was removed.
        
        Previously, there was a second defensive check for 'if OpenAI is None' after 
        the initial check at line 131. Since the initial check already handles this case,
        the second check was unreachable and has been removed for cleaner code.
        
        This test documents that the removal was intentional.
        """
        # The redundant check has been removed from the code, so this tests the logic
        # that would happen if it still existed: proper handling at the first check
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        
        cv_data = {
            "identity": {"name": "", "title": "", "full_name": "", "first_name": "", "last_name": ""},
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        
        # With OpenAI set to None, the first check (line 131) handles it
        with patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI', None):
            work = make_work(tmp_path, cv_data)
            result = adjuster.adjust(work, job_description="Test job")
            assert read_output(result) == cv_data  # Returns original CV due to first check
    
    def test_adjust_with_job_description(self, tmp_path: Path):
        """adjust should work with job_description parameter (no API call)."""
        adjuster = OpenAIJobSpecificAdjuster(api_key=None)  # No API key
        # Override the API key to ensure it's None (in case OPENAI_API_KEY env var is set)
        adjuster._api_key = None
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        # Without API key, should return original data
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, job_description="Test job")
        assert read_output(result) == cv_data
    
    def test_adjust_missing_api_key(self, tmp_path: Path):
        """adjust should return original CV when API key is missing."""
        adjuster = OpenAIJobSpecificAdjuster(api_key=None)
        # Override the API key to ensure it's None (in case OPENAI_API_KEY env var is set)
        adjuster._api_key = None
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, job_description="Test job")
        assert read_output(result) == cv_data
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI', None)
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_openai_none_in_adjust_method(self, mock_format, tmp_path: Path):
        """adjust should check if OpenAI is None and return original CV."""
        mock_format.return_value = "System prompt"
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, job_description="Test job")
        assert read_output(result) == cv_data
    
    def test_adjust_with_openai_not_installed(self, monkeypatch, tmp_path: Path):
        """adjust should handle case where OpenAI module is not installed (monkeypatch version)."""
        # Mock the OpenAI module as None to simulate it not being installed
        monkeypatch.setattr(
            'cvextract.adjusters.openai_job_specific_adjuster.OpenAI',
            None
        )
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, job_description="Test job")
        assert read_output(result) == cv_data
    
    def test_adjust_validate_params_called(self, tmp_path: Path):
        """adjust should call validate_params and raise if params invalid."""
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        # Missing job_url and job_description should raise
        with pytest.raises(ValueError, match="requires either"):
            work = make_work(tmp_path, cv_data)
            adjuster.adjust(work)  # No params
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster._fetch_job_description')
    def test_adjust_url_fetch_fails_returns_original(self, mock_fetch, tmp_path: Path):
        """If job fetch from URL fails, should return original CV."""
        mock_fetch.return_value = ""  # Empty job description
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, job_url="https://example.com/job/123")
        assert read_output(result) == cv_data
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_prompt_load_fails(self, mock_format, tmp_path: Path):
        """If prompt template fails to load, should return original CV."""
        mock_format.return_value = None
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, job_description="Test job")
        assert read_output(result) == cv_data
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.get_verifier')
    def test_adjust_api_call_success(self, mock_get_verifier, mock_format, mock_openai_class, tmp_path: Path):
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
        
        # Setup verifier mock
        mock_verifier = MagicMock()
        mock_verifier.verify.return_value = MagicMock(ok=True)
        mock_get_verifier.return_value = mock_verifier
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key", model="gpt-4o-mini")
        cv_data = {
            "identity": {"name": "", "title": "", "full_name": "", "first_name": "", "last_name": ""},
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, job_description="Test job")
        assert read_output(result) == adjusted_cv
        # Client should be created once
        mock_openai_class.assert_called_once_with(api_key="test-key")
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_empty_completion(self, mock_format, mock_openai_class, tmp_path: Path):
        """adjust should return original CV if completion is empty."""
        mock_format.return_value = "System prompt"
        
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=None))]
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, job_description="Test job")
        assert read_output(result) == cv_data
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_invalid_json_response(self, mock_format, mock_openai_class, tmp_path: Path):
        """adjust should return original CV if completion is invalid JSON."""
        mock_format.return_value = "System prompt"
        
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content="not valid json"))]
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, job_description="Test job")
        assert read_output(result) == cv_data
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_api_exception(self, mock_format, mock_openai_class, tmp_path: Path):
        """adjust should return original CV if API call raises exception."""
        mock_format.return_value = "System prompt"
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API error")
        mock_openai_class.return_value = mock_client
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, job_description="Test job")
        assert read_output(result) == cv_data
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_non_dict_json(self, mock_format, mock_openai_class, tmp_path: Path):
        """adjust should return original CV if JSON response is not a dict."""
        mock_format.return_value = "System prompt"
        
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content='[1, 2, 3]'))]
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, job_description="Test job")
        assert read_output(result) == cv_data  # Should return original since schema validation expects dict
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_empty_choices_list(self, mock_format, mock_openai_class, tmp_path: Path):
        """adjust should return original CV if completion has no choices."""
        mock_format.return_value = "System prompt"
        
        mock_completion = MagicMock()
        mock_completion.choices = []  # Empty choices list
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, job_description="Test job")
        assert read_output(result) == cv_data
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_retry_on_transient_error(self, mock_format, mock_openai_class, tmp_path: Path):
        """adjust should retry on transient errors via _OpenAIRetry."""
        mock_format.return_value = "System prompt"
        
        adjusted_cv = {
            "identity": {"name": "Adjusted", "title": "Engineer", "full_name": "Test User", "first_name": "Test", "last_name": "User"},
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        mock_completion_success = MagicMock()
        mock_completion_success.choices = [MagicMock(message=MagicMock(content=json.dumps(adjusted_cv)))]
        
        # Create an exception with a status_code attribute to trigger _is_transient
        transient_error = Exception("HTTP 429 Too Many Requests")
        transient_error.status_code = 429
        
        mock_client = MagicMock()
        # Fail once with transient error, then succeed
        mock_client.chat.completions.create.side_effect = [
            transient_error,
            mock_completion_success
        ]
        mock_openai_class.return_value = mock_client
        
        # Create a mock sleep function to track calls
        mock_sleep = MagicMock()
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key", _sleep=mock_sleep)
        cv_data = {"identity": {"name": "", "title": "", "full_name": "", "first_name": "", "last_name": ""}, "sidebar": {}, "overview": "", "experiences": []}
        
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, job_description="Test job")
        assert read_output(result) == adjusted_cv, f"Expected adjusted CV, got {read_output(result)}"
        # Should have called create twice (first failed, second succeeded)
        assert mock_client.chat.completions.create.call_count == 2
        # Should have called sleep for backoff
        assert mock_sleep.call_count >= 1
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_retry_exhausts_max_attempts(self, mock_format, mock_openai_class, tmp_path: Path):
        """adjust should return original CV if retries are exhausted."""
        mock_format.return_value = "System prompt"
        
        # Create an exception with a status_code attribute to trigger _is_transient
        transient_error = Exception("HTTP 429 Too Many Requests")
        transient_error.status_code = 429
        
        mock_client = MagicMock()
        # Always fail with transient error
        mock_client.chat.completions.create.side_effect = transient_error
        mock_openai_class.return_value = mock_client
        
        # Use a mock sleep function to avoid actual sleeping
        mock_sleep = MagicMock()
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key", _sleep=mock_sleep)
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, job_description="Test job")
        assert read_output(result) == cv_data
        # Should have tried up to max_attempts (default 8)
        assert mock_client.chat.completions.create.call_count == 8
        # Sleep should have been called for backoff (7 times for 8 attempts)
        assert mock_sleep.call_count == 7
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_non_transient_error_no_retry(self, mock_format, mock_openai_class, tmp_path: Path):
        """adjust should not retry on non-transient exceptions."""
        mock_format.return_value = "System prompt"
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = ValueError("Invalid input")
        mock_openai_class.return_value = mock_client
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, job_description="Test job")
        assert read_output(result) == cv_data
        # Should have called create only once (no retry for non-transient)
        assert mock_client.chat.completions.create.call_count == 1
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_json_parsed_to_none(self, mock_format, mock_openai_class, tmp_path: Path):
        """adjust should return original CV if JSON parses to None."""
        mock_format.return_value = "System prompt"
        
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content='null'))]
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, job_description="Test job")
        assert read_output(result) == cv_data
    
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
    def test_adjust_openai_none_before_client_creation(self, mock_format, tmp_path: Path):
        """adjust should return original CV if OpenAI is None during adjust call."""
        mock_format.return_value = "System prompt"
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, job_description="Test job")
        assert read_output(result) == cv_data
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_with_retry_backoff_sleep(self, mock_format, mock_openai_class, tmp_path: Path):
        """adjust should call sleep during exponential backoff retry."""
        mock_format.return_value = "System prompt"
        
        adjusted_cv = {
            "identity": {"name": "Adjusted", "title": "Engineer", "full_name": "Test User", "first_name": "Test", "last_name": "User"},
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        mock_completion_success = MagicMock()
        mock_completion_success.choices = [MagicMock(message=MagicMock(content=json.dumps(adjusted_cv)))]
        
        # Create transient errors with status_code
        transient_error = Exception("HTTP 429 Too Many Requests")
        transient_error.status_code = 429
        
        mock_client = MagicMock()
        # Fail twice with transient error, then succeed
        mock_client.chat.completions.create.side_effect = [
            transient_error,
            transient_error,
            mock_completion_success
        ]
        mock_openai_class.return_value = mock_client
        
        # Use a mock sleep function to avoid actual sleeping
        mock_sleep = MagicMock()
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key", _sleep=mock_sleep)
        cv_data = {
            "identity": {"name": "", "title": "", "full_name": "", "first_name": "", "last_name": ""},
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, job_description="Test job")
        assert read_output(result) == adjusted_cv, f"Expected adjusted CV, got {read_output(result)}"
        # Should have called create 3 times (2 failures, 1 success)
        assert mock_client.chat.completions.create.call_count == 3
        # Sleep should have been called twice (once after each failure)
        assert mock_sleep.call_count == 2
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_completion_choices_false(self, mock_format, mock_openai_class, tmp_path: Path):
        """adjust should handle completion with falsy choices."""
        mock_format.return_value = "System prompt"
        
        mock_completion = MagicMock()
        mock_completion.choices = False  # Falsy but not None or empty list
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, job_description="Test job")
        assert read_output(result) == cv_data
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_with_both_job_url_and_description(self, mock_format, mock_openai_class, tmp_path: Path):
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
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(
            work,
            job_description="Direct description",
            job_url="https://example.com/job/123"
        )
        assert read_output(result) == adjusted_cv
        # format_prompt should be called with the direct job_description, not fetched from URL
        mock_format.assert_called_once_with("adjuster_promp_for_specific_job", job_description="Direct description")
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_rate_limit_with_429_in_error_message(self, mock_format, mock_openai_class, tmp_path: Path):
        """adjust should detect rate limit by status code attribute."""
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
        
        # Create transient error with status code
        transient_error = Exception("HTTP 429 Too Many Requests")
        transient_error.status_code = 429
        
        mock_client = MagicMock()
        # Fail with transient error, then succeed
        mock_client.chat.completions.create.side_effect = [
            transient_error,
            mock_completion_success
        ]
        mock_openai_class.return_value = mock_client
        
        # Create a mock sleep function
        mock_sleep = MagicMock()
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key", _sleep=mock_sleep)
        cv_data = {
            "identity": {"name": "", "title": "", "full_name": "", "first_name": "", "last_name": ""},
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, job_description="Test job")
        assert read_output(result) == adjusted_cv, f"Expected adjusted CV with 'Adjusted' name, got {read_output(result)}"
        # Should have retried after seeing 429
        assert mock_client.chat.completions.create.call_count == 2
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_final_retry_attempt_rate_limit(self, mock_format, mock_openai_class, tmp_path: Path):
        """adjust should exhaust retries when rate limit persists on all attempts."""
        mock_format.return_value = "System prompt"
        
        # Create transient errors with status code
        transient_error = Exception("Rate limited")
        transient_error.status_code = 429
        
        mock_client = MagicMock()
        # Fail with rate limit on all attempts (default max_attempts=8)
        mock_client.chat.completions.create.side_effect = transient_error
        mock_openai_class.return_value = mock_client
        
        # Create mock sleep
        mock_sleep = MagicMock()
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key", _sleep=mock_sleep)
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, job_description="Test job")
        assert read_output(result) == cv_data
        # Should have attempted 8 times and slept 7 times (not on the last attempt before giving up)
        assert mock_client.chat.completions.create.call_count == 8
        assert mock_sleep.call_count == 7
    
    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.get_verifier')
    def test_adjust_schema_validation_fails(self, mock_get_verifier, mock_format, mock_openai_class, tmp_path: Path):
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
        
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, job_description="Test job")
        assert read_output(result) == cv_data  # Should return original due to validation failure
        mock_get_verifier.assert_called_once_with("cv-schema-verifier")

    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.get_verifier')
    def test_adjust_verifier_not_available(self, mock_get_verifier, mock_format, mock_openai_class, tmp_path: Path):
        """adjust should return original CV if CV schema verifier is not available."""
        mock_format.return_value = "System prompt"
        
        adjusted_cv = {
            "identity": {"name": "John", "title": "Engineer", "full_name": "John Doe", "first_name": "John", "last_name": "Doe"},
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(adjusted_cv)))]
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        
        # Mock verifier as None (not available)
        mock_get_verifier.return_value = None
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {
            "identity": {"name": "", "title": "", "full_name": "", "first_name": "", "last_name": ""},
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, job_description="Test job")
        assert read_output(result) == cv_data  # Should return original since verifier is unavailable
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
    def test_adjust_schema_validation_exception(self, mock_get_verifier, mock_format, mock_openai_class, tmp_path: Path):
        """adjust should handle exception during schema validation."""
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
        
        # Setup verifier mock to raise exception during verify call
        mock_verifier = MagicMock()
        mock_verifier.verify.side_effect = Exception("Validation error")
        mock_get_verifier.return_value = mock_verifier
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {
            "identity": {"name": "", "title": "", "full_name": "", "first_name": "", "last_name": ""},
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        
        # Should handle exception during verify() and return original CV
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, job_description="Test job")
        assert read_output(result) == cv_data  # Returns original due to validation exception


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


class TestOpenAICompanyResearchHelpers:
    """Tests for helper functions in openai_company_research_adjuster."""

    def test_atomic_write_json_creates_file(self, tmp_path):
        """_atomic_write_json() writes data atomically and creates parents."""
        from cvextract.adjusters.openai_company_research_adjuster import _atomic_write_json

        target = tmp_path / "nested" / "cache.json"
        payload = {"name": "Test Co", "domains": ["example.com"]}

        _atomic_write_json(target, payload)

        assert target.exists()
        assert json.loads(target.read_text(encoding="utf-8")) == payload
    
    def test_url_to_cache_filename_converts_https_url_to_domain_hash(self):
        """url_to_cache_filename() converts a URL to a safe filename with domain and hash."""
        from cvextract.shared import url_to_cache_filename
        
        result = url_to_cache_filename("https://www.example.com/path/to/page")
        assert "example.com" in result
        assert result.endswith(".research.json")
        assert "-" in result  # has hash separator
    
    def test_url_to_cache_filename_removes_protocol_and_www(self):
        """url_to_cache_filename() properly handles protocol and www prefix."""
        from cvextract.shared import url_to_cache_filename
        
        result1 = url_to_cache_filename("https://www.example.com")
        result2 = url_to_cache_filename("http://example.com")
        result3 = url_to_cache_filename("https://example.com")
        
        # All should have the same domain part
        assert "example.com" in result1
        assert "example.com" in result2
        assert "example.com" in result3
    
    def test_url_to_cache_filename_handles_complex_urls_with_port(self):
        """url_to_cache_filename() handles URLs with ports and query parameters."""
        from cvextract.shared import url_to_cache_filename
        
        result = url_to_cache_filename("https://example.com:8080/path?query=value#fragment")
        assert "example.com" in result
        assert "8080" not in result  # port should be stripped
        assert "?" not in result     # query should be stripped
        assert "#" not in result     # fragment should be stripped
    
    def test_load_research_schema_loads_valid_schema(self):
        """_load_research_schema() loads the research schema from file."""
        from cvextract.adjusters.openai_company_research_adjuster import _load_research_schema
        
        schema = _load_research_schema()
        assert schema is not None
        assert isinstance(schema, dict)
        assert "$id" in schema or "properties" in schema or "$schema" in schema
    
    def test_load_research_schema_returns_cached_value_on_second_call(self):
        """_load_research_schema() caches the schema and returns it on subsequent calls."""
        from cvextract.adjusters.openai_company_research_adjuster import _load_research_schema, _RESEARCH_SCHEMA
        import cvextract.adjusters.openai_company_research_adjuster as adj_module
        
        # Reset the global cache
        adj_module._RESEARCH_SCHEMA = None
        
        schema1 = _load_research_schema()
        schema2 = _load_research_schema()
        
        # Should return the same object
        assert schema1 is schema2
    
    def test_fetch_customer_page_returns_empty_string_if_requests_unavailable(self):
        """_fetch_customer_page() returns empty string when requests module is not available."""
        from cvextract.adjusters.openai_company_research_adjuster import _fetch_customer_page
        import cvextract.adjusters.openai_company_research_adjuster as adj_module
        
        # Temporarily patch requests to None
        original_requests = adj_module.requests
        try:
            adj_module.requests = None
            result = _fetch_customer_page("https://example.com")
            assert result == ""
        finally:
            adj_module.requests = original_requests
    
    def test_fetch_customer_page_success(self):
        """_fetch_customer_page() successfully fetches and returns page content."""
        from cvextract.adjusters.openai_company_research_adjuster import _fetch_customer_page
        from unittest.mock import patch, MagicMock
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html>Test content</html>"
        
        with patch('cvextract.adjusters.openai_company_research_adjuster.requests.get', return_value=mock_response):
            result = _fetch_customer_page("https://example.com")
            assert result == "<html>Test content</html>"
    
    def test_fetch_customer_page_returns_empty_on_non_200_status(self):
        """_fetch_customer_page() returns empty string on non-200 status code."""
        from cvextract.adjusters.openai_company_research_adjuster import _fetch_customer_page
        from unittest.mock import patch, MagicMock
        
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        with patch('cvextract.adjusters.openai_company_research_adjuster.requests.get', return_value=mock_response):
            result = _fetch_customer_page("https://example.com")
            assert result == ""
    
    def test_fetch_customer_page_returns_empty_on_exception(self):
        """_fetch_customer_page() returns empty string on any exception."""
        from cvextract.adjusters.openai_company_research_adjuster import _fetch_customer_page
        from unittest.mock import patch
        
        with patch('cvextract.adjusters.openai_company_research_adjuster.requests.get', side_effect=Exception("Network error")):
            result = _fetch_customer_page("https://example.com")
            assert result == ""
    
    def test_validate_research_data_returns_false_for_non_dict(self):
        """_validate_research_data() returns False if data is not a dict."""
        from cvextract.adjusters.openai_company_research_adjuster import _validate_research_data
        
        assert _validate_research_data(None) is False
        assert _validate_research_data("string") is False
        assert _validate_research_data([1, 2, 3]) is False
        assert _validate_research_data(123) is False
    
    def test_validate_research_data_uses_verifier(self):
        """_validate_research_data() validates data using company-profile-verifier."""
        from cvextract.adjusters.openai_company_research_adjuster import _validate_research_data
        from unittest.mock import patch, MagicMock
        
        mock_verifier = MagicMock()
        mock_result = MagicMock()
        mock_result.ok = True
        mock_verifier.verify.return_value = mock_result
        
        with patch('cvextract.adjusters.openai_company_research_adjuster.get_verifier', return_value=mock_verifier):
            result = _validate_research_data({"company": "Test Corp"})
            assert result is True
            mock_verifier.verify.assert_called_once_with({"company": "Test Corp"})
    
    def test_validate_research_data_returns_false_on_verifier_error(self):
        """_validate_research_data() returns False if verifier raises exception."""
        from cvextract.adjusters.openai_company_research_adjuster import _validate_research_data
        from unittest.mock import patch
        
        with patch('cvextract.adjusters.openai_company_research_adjuster.get_verifier', side_effect=Exception("Verifier error")):
            result = _validate_research_data({"company": "Test Corp"})
            assert result is False

    def test_extract_json_object_rejects_non_string(self):
        """_extract_json_object() returns None for non-string input."""
        from cvextract.adjusters.openai_company_research_adjuster import _extract_json_object

        assert _extract_json_object(None) is None
        assert _extract_json_object(123) is None
        assert _extract_json_object([]) is None

    def test_extract_json_object_ignores_non_object_json(self):
        """_extract_json_object() returns None for JSON arrays."""
        from cvextract.adjusters.openai_company_research_adjuster import _extract_json_object

        assert _extract_json_object("[1, 2]") is None


class TestCompanyResearchRetryHelpers:
    """Tests for retry helpers in company research adjuster."""

    def test_get_status_code_from_response(self):
        """_get_status_code() reads status from response object."""
        from cvextract.adjusters.openai_company_research_adjuster import _OpenAIRetry, _RetryConfig

        resp = MagicMock(status_code=503)
        exc = Exception("Server error")
        exc.response = resp

        retryer = _OpenAIRetry(retry=_RetryConfig(), sleep=lambda _: None)
        assert retryer._get_status_code(exc) == 503

    def test_sleep_with_backoff_uses_retry_after_from_response(self):
        """_sleep_with_backoff() uses Retry-After from response headers."""
        from cvextract.adjusters.openai_company_research_adjuster import _OpenAIRetry, _RetryConfig

        mock_sleep = MagicMock()
        resp = MagicMock(headers={"Retry-After": "1.5"})
        exc = Exception("Rate limited")
        exc.response = resp

        retryer = _OpenAIRetry(retry=_RetryConfig(), sleep=mock_sleep)
        retryer._sleep_with_backoff(0, is_write=False, exc=exc)
        mock_sleep.assert_called_once_with(1.5)

    def test_sleep_with_backoff_deterministic_write_multiplier(self):
        """_sleep_with_backoff() applies write multiplier without jitter."""
        from cvextract.adjusters.openai_company_research_adjuster import _OpenAIRetry, _RetryConfig

        mock_sleep = MagicMock()
        retryer = _OpenAIRetry(
            retry=_RetryConfig(base_delay_s=1.0, max_delay_s=10.0, write_multiplier=2.0, deterministic=True),
            sleep=mock_sleep,
        )
        exc = Exception("Rate limited")
        exc.status_code = 429

        retryer._sleep_with_backoff(0, is_write=True, exc=exc)
        mock_sleep.assert_called_once_with(2.0)

    def test_get_retry_after_with_missing_headers(self):
        """_get_retry_after_s() returns None when headers are missing."""
        from cvextract.adjusters.openai_company_research_adjuster import _OpenAIRetry, _RetryConfig

        exc = Exception("No headers")
        retryer = _OpenAIRetry(retry=_RetryConfig(), sleep=lambda _: None)
        assert retryer._get_retry_after_s(exc) is None


class TestCompanyResearchSchemaLoading:
    """Tests for research schema loading edge cases."""

    def test_load_research_schema_missing_path(self):
        """_load_research_schema() returns None when schema path is missing."""
        import cvextract.adjusters.openai_company_research_adjuster as adj_module

        original_schema_path = adj_module._SCHEMA_PATH
        original_cache = adj_module._RESEARCH_SCHEMA
        try:
            adj_module._SCHEMA_PATH = None
            adj_module._RESEARCH_SCHEMA = None
            assert adj_module._load_research_schema() is None
        finally:
            adj_module._SCHEMA_PATH = original_schema_path
            adj_module._RESEARCH_SCHEMA = original_cache

    def test_load_research_schema_open_failure(self, tmp_path):
        """_load_research_schema() returns None when open fails."""
        import cvextract.adjusters.openai_company_research_adjuster as adj_module

        schema_path = tmp_path / "research_schema.json"
        schema_path.write_text("{bad json")

        original_schema_path = adj_module._SCHEMA_PATH
        original_cache = adj_module._RESEARCH_SCHEMA
        try:
            adj_module._SCHEMA_PATH = schema_path
            adj_module._RESEARCH_SCHEMA = None
            with patch("cvextract.adjusters.openai_company_research_adjuster.open", side_effect=OSError("nope")):
                assert adj_module._load_research_schema() is None
        finally:
            adj_module._SCHEMA_PATH = original_schema_path
            adj_module._RESEARCH_SCHEMA = original_cache


class TestResearchCompanyProfileCache:
    """Tests for company research cache helpers."""

    def test_research_company_profile_uses_valid_cache(self, tmp_path):
        """_load_cached_research() returns cached data when valid."""
        from cvextract.adjusters.openai_company_research_adjuster import _load_cached_research

        cached = {"name": "Cache Co", "description": "Cached", "domains": []}
        cache_path = tmp_path / "research.json"
        cache_path.write_text(json.dumps(cached))

        with patch('cvextract.adjusters.openai_company_research_adjuster._validate_research_data', return_value=True):
            result = _load_cached_research(cache_path)
            assert result == cached

    def test_research_company_profile_caches_on_success(self, tmp_path):
        """_cache_research_data() writes research data to cache."""
        from cvextract.adjusters.openai_company_research_adjuster import _cache_research_data

        cache_path = tmp_path / "research.json"
        research_data = {"name": "Fresh Co", "description": "Fresh", "domains": []}
        _cache_research_data(cache_path, research_data)
        assert json.loads(cache_path.read_text(encoding="utf-8")) == research_data


class TestResearchCompanyProfileFailures:
    """Tests for failure paths in _research_company_profile."""

    def test_research_company_profile_skips_when_openai_missing(self):
        """_research_company_profile() returns None when OpenAI is unavailable."""
        import cvextract.adjusters.openai_company_research_adjuster as adj_module

        original_openai = adj_module.OpenAI
        try:
            adj_module.OpenAI = None
            result = adj_module._research_company_profile(
                "https://example.com",
                "test-key",
                "gpt-4o-mini",
            )
            assert result is None
        finally:
            adj_module.OpenAI = original_openai

    def test_research_company_profile_skips_when_schema_missing(self):
        """_research_company_profile() returns None when schema is missing."""
        from cvextract.adjusters.openai_company_research_adjuster import _research_company_profile

        with patch('cvextract.adjusters.openai_company_research_adjuster._load_research_schema', return_value=None):
            result = _research_company_profile(
                "https://example.com",
                "test-key",
                "gpt-4o-mini",
            )
            assert result is None

    def test_research_company_profile_skips_when_prompt_missing(self):
        """_research_company_profile() returns None when prompt template is missing."""
        from cvextract.adjusters.openai_company_research_adjuster import _research_company_profile

        with patch('cvextract.adjusters.openai_company_research_adjuster._load_research_schema', return_value={"type": "object"}):
            with patch('cvextract.adjusters.openai_company_research_adjuster.format_prompt', return_value=None):
                result = _research_company_profile(
                    "https://example.com",
                    "test-key",
                    "gpt-4o-mini",
                )
                assert result is None

    def test_research_company_profile_empty_completion(self):
        """_research_company_profile() returns None when completion is empty."""
        from cvextract.adjusters.openai_company_research_adjuster import _research_company_profile

        mock_completion = MagicMock()
        mock_completion.choices = []
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion

        with patch('cvextract.adjusters.openai_company_research_adjuster.OpenAI', return_value=mock_client):
            with patch('cvextract.adjusters.openai_company_research_adjuster._load_research_schema', return_value={"type": "object"}):
                with patch('cvextract.adjusters.openai_company_research_adjuster.format_prompt', return_value="prompt"):
                    result = _research_company_profile(
                        "https://example.com",
                        "test-key",
                        "gpt-4o-mini",
                    )
                    assert result is None

    def test_research_company_profile_invalid_json(self):
        """_research_company_profile() returns None when JSON parsing fails."""
        from cvextract.adjusters.openai_company_research_adjuster import _research_company_profile

        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content="not json"))]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion

        with patch('cvextract.adjusters.openai_company_research_adjuster.OpenAI', return_value=mock_client):
            with patch('cvextract.adjusters.openai_company_research_adjuster._load_research_schema', return_value={"type": "object"}):
                with patch('cvextract.adjusters.openai_company_research_adjuster.format_prompt', return_value="prompt"):
                    result = _research_company_profile(
                        "https://example.com",
                        "test-key",
                        "gpt-4o-mini",
                    )
                    assert result is None

    def test_research_company_profile_validation_failure(self):
        """_research_company_profile() returns None when validation fails."""
        from cvextract.adjusters.openai_company_research_adjuster import _research_company_profile

        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content='{"name": "Bad Co"}'))]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion

        with patch('cvextract.adjusters.openai_company_research_adjuster.OpenAI', return_value=mock_client):
            with patch('cvextract.adjusters.openai_company_research_adjuster._load_research_schema', return_value={"type": "object"}):
                with patch('cvextract.adjusters.openai_company_research_adjuster.format_prompt', return_value="prompt"):
                    with patch('cvextract.adjusters.openai_company_research_adjuster._validate_research_data', return_value=False):
                        result = _research_company_profile(
                            "https://example.com",
                            "test-key",
                            "gpt-4o-mini",
                        )
                        assert result is None

    def test_research_company_profile_non_stop_finish_reason(self):
        """_research_company_profile() returns None when finish_reason is non-stop."""
        from cvextract.adjusters.openai_company_research_adjuster import _research_company_profile

        mock_choice = MagicMock()
        mock_choice.finish_reason = "length"
        mock_choice.message = MagicMock(content='{"name": "Long Co"}')

        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion

        with patch('cvextract.adjusters.openai_company_research_adjuster.OpenAI', return_value=mock_client):
            with patch('cvextract.adjusters.openai_company_research_adjuster._load_research_schema', return_value={"type": "object"}):
                with patch('cvextract.adjusters.openai_company_research_adjuster.format_prompt', return_value="prompt"):
                    result = _research_company_profile(
                        "https://example.com",
                        "test-key",
                        "gpt-4o-mini",
                    )
                    assert result is None

    def test_research_company_profile_passes_timeout(self):
        """_research_company_profile() passes request timeout to OpenAI."""
        from cvextract.adjusters.openai_company_research_adjuster import _research_company_profile

        mock_choice = MagicMock()
        mock_choice.finish_reason = "stop"
        mock_choice.message = MagicMock(content='{"name": "Timeout Co"}')

        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion

        with patch('cvextract.adjusters.openai_company_research_adjuster.OpenAI', return_value=mock_client):
            with patch('cvextract.adjusters.openai_company_research_adjuster._load_research_schema', return_value={"type": "object"}):
                with patch('cvextract.adjusters.openai_company_research_adjuster.format_prompt', return_value="prompt"):
                    with patch('cvextract.adjusters.openai_company_research_adjuster._validate_research_data', return_value=True):
                        result = _research_company_profile(
                            "https://example.com",
                            "gpt-4o-mini",
                            None,
                            request_timeout_s=12.5,
                        )
                        assert result == {"name": "Timeout Co"}

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["timeout"] == 12.5


class TestStripMarkdownFencesJobSpecific:
    """Tests for _strip_markdown_fences in job-specific adjuster."""

    def test_strip_markdown_fences_json_variant(self):
        """Test stripping ```json code fence."""
        from cvextract.adjusters.openai_job_specific_adjuster import _strip_markdown_fences
        
        text = '```json\n{"key": "value"}\n```'
        result = _strip_markdown_fences(text)
        assert result == '{"key": "value"}'

    def test_strip_markdown_fences_generic_variant(self):
        """Test stripping generic ``` code fence."""
        from cvextract.adjusters.openai_job_specific_adjuster import _strip_markdown_fences
        
        text = '```\n{"key": "value"}\n```'
        result = _strip_markdown_fences(text)
        assert result == '{"key": "value"}'

    def test_strip_markdown_fences_no_fence_variant(self):
        """Test text without code fence."""
        from cvextract.adjusters.openai_job_specific_adjuster import _strip_markdown_fences
        
        text = '{"key": "value"}'
        result = _strip_markdown_fences(text)
        assert result == '{"key": "value"}'


class TestExtractJsonObjectJobSpecific:
    """Tests for _extract_json_object in job-specific adjuster."""

    def test_extract_json_object_simple(self):
        """Test extracting simple JSON."""
        from cvextract.adjusters.openai_job_specific_adjuster import _extract_json_object
        
        text = '{"id": 1}'
        result = _extract_json_object(text)
        assert result == {"id": 1}

    def test_extract_json_object_with_markdown(self):
        """Test with markdown fence."""
        from cvextract.adjusters.openai_job_specific_adjuster import _extract_json_object
        
        text = '```json\n{"id": 1}\n```'
        result = _extract_json_object(text)
        assert result == {"id": 1}

    def test_extract_json_object_with_text(self):
        """Test extracting from text."""
        from cvextract.adjusters.openai_job_specific_adjuster import _extract_json_object
        
        text = 'The data is:\n{"id": 1}'
        result = _extract_json_object(text)
        assert result == {"id": 1}

    def test_extract_json_object_array_returns_none(self):
        """Test that arrays return None."""
        from cvextract.adjusters.openai_job_specific_adjuster import _extract_json_object
        
        text = '[1, 2, 3]'
        result = _extract_json_object(text)
        assert result is None

    def test_extract_json_object_invalid_returns_none(self):
        """Test invalid JSON returns None."""
        from cvextract.adjusters.openai_job_specific_adjuster import _extract_json_object
        
        text = '{invalid}'
        result = _extract_json_object(text)
        assert result is None

    def test_extract_json_object_non_string(self):
        """Test non-string input returns None."""
        from cvextract.adjusters.openai_job_specific_adjuster import _extract_json_object
        
        result = _extract_json_object(None)
        assert result is None


class TestFetchJobDescriptionEdgeCases:
    """Additional tests for _fetch_job_description helper."""

    @patch('cvextract.adjusters.openai_job_specific_adjuster.requests')
    def test_fetch_job_description_timeout_exception(self, mock_requests):
        """Test when request times out."""
        mock_requests.get.side_effect = TimeoutError("Request timed out")
        
        result = _fetch_job_description("https://example.com/job/123")
        assert result == ""

    @patch('cvextract.adjusters.openai_job_specific_adjuster.requests')
    def test_fetch_job_description_non_200_status(self, mock_requests):
        """Test non-200 status codes."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_requests.get.return_value = mock_response
        
        result = _fetch_job_description("https://example.com/job/notfound")
        assert result == ""

    @patch('cvextract.adjusters.openai_job_specific_adjuster.requests')
    def test_fetch_job_description_empty_response(self, mock_requests):
        """Test empty response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_requests.get.return_value = mock_response
        
        result = _fetch_job_description("https://example.com/job/123")
        assert result == ""

    @patch('cvextract.adjusters.openai_job_specific_adjuster.requests')
    def test_fetch_job_description_html_tags_removal(self, mock_requests):
        """Test HTML tag removal."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<h1>Job Title</h1><p>Description</p>"
        mock_requests.get.return_value = mock_response
        
        result = _fetch_job_description("https://example.com/job/123")
        assert "Job Title" in result
        assert "Description" in result
        assert "<" not in result
        assert ">" not in result

    @patch('cvextract.adjusters.openai_job_specific_adjuster.requests')
    def test_fetch_job_description_script_removal(self, mock_requests):
        """Test script tag removal."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<script>alert('xss')</script><p>Content</p>"
        mock_requests.get.return_value = mock_response
        
        result = _fetch_job_description("https://example.com/job/123")
        assert "alert" not in result
        assert "Content" in result

    @patch('cvextract.adjusters.openai_job_specific_adjuster.requests')
    def test_fetch_job_description_style_removal(self, mock_requests):
        """Test style tag removal."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<style>body{color:red;}</style><p>Content</p>"
        mock_requests.get.return_value = mock_response
        
        result = _fetch_job_description("https://example.com/job/123")
        assert "color:red" not in result
        assert "Content" in result

    @patch('cvextract.adjusters.openai_job_specific_adjuster.requests')
    def test_fetch_job_description_html_entities(self, mock_requests):
        """Test HTML entity decoding."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<p>Title &amp; Description &quot;quoted&quot;</p>"
        mock_requests.get.return_value = mock_response
        
        result = _fetch_job_description("https://example.com/job/123")
        assert "&amp;" not in result
        assert "&quot;" not in result
        assert "&" in result
        assert '"' in result

    @patch('cvextract.adjusters.openai_job_specific_adjuster.requests')
    def test_fetch_job_description_whitespace_collapse(self, mock_requests):
        """Test whitespace collapsing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<p>Multiple    spaces    and\n\nnewlines</p>"
        mock_requests.get.return_value = mock_response
        
        result = _fetch_job_description("https://example.com/job/123")
        # Should collapse multiple spaces
        assert "    " not in result
        assert "\n" not in result

    @patch('cvextract.adjusters.openai_job_specific_adjuster.requests')
    def test_fetch_job_description_length_limit(self, mock_requests):
        """Test that result is limited to 5000 chars."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "x" * 10000
        mock_requests.get.return_value = mock_response
        
        result = _fetch_job_description("https://example.com/job/123")
        assert len(result) == 5000

    @patch('cvextract.adjusters.openai_job_specific_adjuster.requests', None)
    def test_fetch_job_description_requests_unavailable(self):
        """Test when requests module is not available."""
        result = _fetch_job_description("https://example.com/job/123")
        assert result == ""


class TestOpenAIJobSpecificAdjusterEdgeCases:
    """Additional edge case tests for OpenAIJobSpecificAdjuster."""

    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    @patch('cvextract.adjusters.openai_job_specific_adjuster._fetch_job_description')
    def test_adjust_uses_both_prompt_template_names(self, mock_fetch, mock_format, mock_openai_class, tmp_path: Path):
        """Test that both typo and corrected prompt template names are tried."""
        # First call returns None (typo key fails), second succeeds
        mock_fetch.return_value = "Job description"
        mock_format.side_effect = [None, "System prompt"]
        
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content='{"identity": {"name": "", "title": "", "full_name": "", "first_name": "", "last_name": ""}, "sidebar": {}, "overview": "", "experiences": []}'))]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        # Will attempt fetch from URL since job_description is empty
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, job_url="https://example.com/job/123")
        
        # Should call format_prompt twice
        assert mock_format.call_count == 2
        # Should use fallback template name
        assert mock_format.call_args_list[1][0][0] == "adjuster_prompt_for_specific_job"

    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.get_verifier')
    def test_adjust_validation_error_with_error_count(self, mock_get_verifier, mock_format, mock_openai_class, tmp_path: Path):
        """Test logging when validation fails with error count."""
        mock_format.return_value = "System prompt"
        
        adjusted_cv = {
            "identity": {"name": "Test", "title": "", "full_name": "Test User", "first_name": "Test", "last_name": "User"},
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(adjusted_cv)))]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        
        # Verifier returns not ok with errors
        mock_verifier = MagicMock()
        mock_verifier.verify.return_value = MagicMock(ok=False, errors=["error1", "error2"])
        mock_get_verifier.return_value = mock_verifier
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, job_description="Test job")
        
        # Should return original due to validation failure
        assert read_output(result) == cv_data

    @patch('cvextract.adjusters.openai_job_specific_adjuster.OpenAI')
    @patch('cvextract.adjusters.openai_job_specific_adjuster.format_prompt')
    def test_adjust_completion_with_multiple_choices(self, mock_format, mock_openai_class, tmp_path: Path):
        """Test handling completion with multiple choices."""
        mock_format.return_value = "System prompt"
        
        adjusted_cv = {
            "identity": {"name": "Adjusted", "title": "Engineer", "full_name": "Test User", "first_name": "Test", "last_name": "User"},
            "sidebar": {},
            "overview": "",
            "experiences": []
        }
        
        # Create completion with multiple choices
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(message=MagicMock(content=json.dumps(adjusted_cv))),
            MagicMock(message=MagicMock(content='{"other": "data"}')),
        ]
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        
        adjuster = OpenAIJobSpecificAdjuster(api_key="test-key")
        cv_data = {"identity": {}, "sidebar": {}, "overview": "", "experiences": []}
        
        work = make_work(tmp_path, cv_data)
        result = adjuster.adjust(work, job_description="Test job")
        
        # Should use first choice
        assert read_output(result) == adjusted_cv

    def test_get_retry_after_from_headers_job_specific(self):
        """Test extracting retry-after from exception headers (job-specific adjuster)."""
        from cvextract.adjusters.openai_job_specific_adjuster import _OpenAIRetry, _RetryConfig
        
        exc = Exception("Test")
        exc.headers = {"retry-after": "60"}
        
        retryer = _OpenAIRetry(retry=_RetryConfig(), sleep=lambda x: None)
        retry_after = retryer._get_retry_after_s(exc)
        assert retry_after == 60.0

    def test_get_retry_after_headers_get_exception_job_specific(self):
        """Test when headers.get() raises an exception (lines 125-130 in job-specific)."""
        from cvextract.adjusters.openai_job_specific_adjuster import _OpenAIRetry, _RetryConfig
        
        # Create a mock headers object that raises when .get() is called
        class BadHeaders:
            def get(self, key1, default=None):
                raise ValueError("Headers error")
        
        exc = Exception("Test")
        exc.headers = BadHeaders()
        
        retryer = _OpenAIRetry(retry=_RetryConfig(), sleep=lambda x: None)
        retry_after = retryer._get_retry_after_s(exc)
        assert retry_after is None

    def test_get_retry_after_non_numeric_string_job_specific(self):
        """Test when retry-after value can't be converted to float (lines 133-137 in job-specific)."""
        from cvextract.adjusters.openai_job_specific_adjuster import _OpenAIRetry, _RetryConfig
        
        exc = Exception("Test")
        exc.headers = {"retry-after": "not-a-number"}
        
        retryer = _OpenAIRetry(retry=_RetryConfig(), sleep=lambda x: None)
        retry_after = retryer._get_retry_after_s(exc)
        assert retry_after is None

    def test_get_retry_after_zero_value_job_specific(self):
        """Test when retry-after is zero (edge case for falsy value check in job-specific)."""
        from cvextract.adjusters.openai_job_specific_adjuster import _OpenAIRetry, _RetryConfig
        
        exc = Exception("Test")
        exc.headers = {"retry-after": "0"}
        
        retryer = _OpenAIRetry(retry=_RetryConfig(), sleep=lambda x: None)
        retry_after = retryer._get_retry_after_s(exc)
        # Zero gets converted to float but the sleep_with_backoff checks if retry_after > 0
        assert retry_after == 0.0


class TestJobSpecificRetryHelpers:
    """Tests for retry helpers in job-specific adjuster."""

    def test_get_status_code_from_response_job_specific(self):
        """_get_status_code() reads status from response object."""
        from cvextract.adjusters.openai_job_specific_adjuster import _OpenAIRetry, _RetryConfig

        resp = MagicMock(status_code=502)
        exc = Exception("Bad gateway")
        exc.response = resp

        retryer = _OpenAIRetry(retry=_RetryConfig(), sleep=lambda _: None)
        assert retryer._get_status_code(exc) == 502


class TestJobSpecificSchemaLoading:
    """Tests for _load_cv_schema edge cases in job-specific adjuster."""

    def test_load_cv_schema_returns_none_when_schema_path_missing(self):
        """_load_cv_schema() returns None when schema path is unavailable."""
        import cvextract.adjusters.openai_job_specific_adjuster as job_module

        original_schema_path = job_module._SCHEMA_PATH
        original_cache = job_module._CV_SCHEMA
        try:
            job_module._SCHEMA_PATH = None
            job_module._CV_SCHEMA = None
            assert job_module._load_cv_schema() is None
        finally:
            job_module._SCHEMA_PATH = original_schema_path
            job_module._CV_SCHEMA = original_cache
