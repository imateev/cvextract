"""Tests for customer_adjust module."""

import json
import logging
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
from cvextract.customer_adjust import (
    adjust_for_customer,
    _fetch_customer_page,
    _research_company_profile,
    _load_research_schema,
)


class TestFetchCustomerPage:
    """Tests for _fetch_customer_page helper."""

    def test_fetch_customer_page_success(self, monkeypatch):
        """Test successful page fetch."""
        mock_requests = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html>Customer page content</html>"
        mock_requests.get.return_value = mock_response
        
        monkeypatch.setattr("cvextract.customer_adjust.requests", mock_requests)
        
        result = _fetch_customer_page("https://example.com")
        assert result == "<html>Customer page content</html>"
        mock_requests.get.assert_called_once_with("https://example.com", timeout=15)

    def test_fetch_customer_page_http_error(self, monkeypatch):
        """Test fetch when HTTP status is not 200."""
        mock_requests = Mock()
        mock_response = Mock()
        mock_response.status_code = 404
        mock_requests.get.return_value = mock_response
        
        monkeypatch.setattr("cvextract.customer_adjust.requests", mock_requests)
        
        result = _fetch_customer_page("https://example.com")
        assert result == ""

    def test_fetch_customer_page_request_exception(self, monkeypatch):
        """Test fetch when requests raises an exception."""
        mock_requests = Mock()
        mock_requests.get.side_effect = Exception("Network error")
        
        monkeypatch.setattr("cvextract.customer_adjust.requests", mock_requests)
        
        result = _fetch_customer_page("https://example.com")
        assert result == ""

    def test_fetch_customer_page_no_requests_lib(self, monkeypatch):
        """Test fetch when requests library is not available."""
        monkeypatch.setattr("cvextract.customer_adjust.requests", None)
        
        result = _fetch_customer_page("https://example.com")
        assert result == ""

    def test_fetch_customer_page_empty_response(self, monkeypatch):
        """Test fetch when response text is empty."""
        mock_requests = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_requests.get.return_value = mock_response
        
        monkeypatch.setattr("cvextract.customer_adjust.requests", mock_requests)
        
        result = _fetch_customer_page("https://example.com")
        assert result == ""


class TestAdjustForCustomer:
    """Tests for adjust_for_customer main function."""

    def test_adjust_for_customer_no_api_key(self, monkeypatch, caplog):
        """Test when no API key is available."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        
        data = {"identity": {"title": "Test"}}
        result = adjust_for_customer(data, "https://example.com", api_key=None)
        
        assert result == data
        assert "OpenAI unavailable or API key missing" in caplog.text

    def test_adjust_for_customer_openai_not_available(self, monkeypatch, caplog):
        """Test when OpenAI library is not available."""
        monkeypatch.setattr("cvextract.customer_adjust.OpenAI", None)
        
        data = {"identity": {"title": "Test"}}
        result = adjust_for_customer(
            data, 
            "https://example.com", 
            api_key="test-key"
        )
        
        assert result == data
        assert "OpenAI unavailable or API key missing" in caplog.text

    def test_adjust_for_customer_success(self, monkeypatch, caplog):
        """Test successful adjustment with OpenAI."""
        caplog.set_level(logging.INFO)
        
        # Mock research to return valid data
        research_data = {"name": "Test", "domains": ["Tech"]}
        monkeypatch.setattr("cvextract.customer_adjust._research_company_profile", Mock(return_value=research_data))
        
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        
        adjusted_json = {"identity": {"title": "Adjusted"}}
        mock_message.content = json.dumps({"adjusted_json": adjusted_json})
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.customer_adjust.OpenAI", mock_openai)
        
        data = {"identity": {"title": "Original"}}
        result = adjust_for_customer(
            data, 
            "https://example.com", 
            api_key="test-key",
            model="gpt-4o-mini"
        )
        
        assert result == adjusted_json
        assert "adjusted to better fit" in caplog.text

    def test_adjust_for_customer_empty_completion(self, monkeypatch, caplog):
        """Test when completion is empty."""
        # Mock research to return valid data
        research_data = {"name": "Test", "domains": ["Tech"]}
        monkeypatch.setattr("cvextract.customer_adjust._research_company_profile", Mock(return_value=research_data))
        
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_completion.choices = []
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.customer_adjust.OpenAI", mock_openai)
        
        data = {"identity": {"title": "Original"}}
        result = adjust_for_customer(
            data, 
            "https://example.com", 
            api_key="test-key"
        )
        
        assert result == data
        assert "empty completion" in caplog.text

    def test_adjust_for_customer_invalid_json_response(self, monkeypatch, caplog):
        """Test when OpenAI returns invalid JSON."""
        # Mock research to return valid data
        research_data = {"name": "Test", "domains": ["Tech"]}
        monkeypatch.setattr("cvextract.customer_adjust._research_company_profile", Mock(return_value=research_data))
        
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        
        mock_message.content = "not valid json"
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.customer_adjust.OpenAI", mock_openai)
        
        data = {"identity": {"title": "Original"}}
        result = adjust_for_customer(
            data, 
            "https://example.com", 
            api_key="test-key"
        )
        
        assert result == data
        assert "invalid JSON response" in caplog.text

    def test_adjust_for_customer_not_dict_response(self, monkeypatch, caplog):
        """Test when OpenAI returns JSON that is not a dict."""
        # Mock research to return valid data
        research_data = {"name": "Test", "domains": ["Tech"]}
        monkeypatch.setattr("cvextract.customer_adjust._research_company_profile", Mock(return_value=research_data))
        
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        
        mock_message.content = json.dumps(["not", "a", "dict"])
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.customer_adjust.OpenAI", mock_openai)
        
        data = {"identity": {"title": "Original"}}
        result = adjust_for_customer(
            data, 
            "https://example.com", 
            api_key="test-key"
        )
        
        assert result == data
        assert "completion is not a dict" in caplog.text

    def test_adjust_for_customer_api_exception(self, monkeypatch, caplog):
        """Test when OpenAI API call raises exception."""
        # Mock research to return valid data
        research_data = {"name": "Test", "domains": ["Tech"]}
        monkeypatch.setattr("cvextract.customer_adjust._research_company_profile", Mock(return_value=research_data))
        
        mock_openai = Mock()
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = RuntimeError("API error")
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.customer_adjust.OpenAI", mock_openai)
        
        data = {"identity": {"title": "Original"}}
        result = adjust_for_customer(
            data, 
            "https://example.com", 
            api_key="test-key"
        )
        
        assert result == data
        assert "error (RuntimeError)" in caplog.text

    def test_adjust_for_customer_uses_default_model(self, monkeypatch):
        """Test that default model is used when not specified."""
        # Mock research to return valid data
        research_data = {"name": "Test", "domains": ["Tech"]}
        monkeypatch.setattr("cvextract.customer_adjust._research_company_profile", Mock(return_value=research_data))
        
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        
        adjusted_json = {"identity": {"title": "Adjusted"}}
        mock_message.content = json.dumps({"adjusted_json": adjusted_json})
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.customer_adjust.OpenAI", mock_openai)
        monkeypatch.delenv("OPENAI_MODEL", raising=False)
        
        data = {"identity": {"title": "Original"}}
        adjust_for_customer(data, "https://example.com", api_key="test-key")
        
        # Verify default model "gpt-4o-mini" is used
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o-mini"

    def test_adjust_for_customer_uses_env_model(self, monkeypatch):
        """Test that OPENAI_MODEL env var is used."""
        # Mock research to return valid data
        research_data = {"name": "Test", "domains": ["Tech"]}
        monkeypatch.setattr("cvextract.customer_adjust._research_company_profile", Mock(return_value=research_data))
        
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        
        adjusted_json = {"identity": {"title": "Adjusted"}}
        mock_message.content = json.dumps({"adjusted_json": adjusted_json})
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.customer_adjust.OpenAI", mock_openai)
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4-turbo")
        
        data = {"identity": {"title": "Original"}}
        adjust_for_customer(data, "https://example.com", api_key="test-key")
        
        # Verify env model is used
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4-turbo"

    def test_adjust_for_customer_parameter_model_overrides_env(self, monkeypatch):
        """Test that parameter model overrides env variable."""
        # Mock research to return valid data
        research_data = {"name": "Test", "domains": ["Tech"]}
        monkeypatch.setattr("cvextract.customer_adjust._research_company_profile", Mock(return_value=research_data))
        
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        
        adjusted_json = {"identity": {"title": "Adjusted"}}
        mock_message.content = json.dumps({"adjusted_json": adjusted_json})
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.customer_adjust.OpenAI", mock_openai)
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4-turbo")
        
        data = {"identity": {"title": "Original"}}
        adjust_for_customer(
            data, 
            "https://example.com", 
            api_key="test-key",
            model="gpt-3.5-turbo"
        )
        
        # Verify parameter model is used (not env)
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-3.5-turbo"


class TestLoadResearchSchema:
    """Tests for _load_research_schema function."""

    def test_load_research_schema_success(self, monkeypatch, tmp_path):
        """Test successful schema loading."""
        schema = {"$schema": "test", "type": "object"}
        schema_file = tmp_path / "research_schema.json"
        schema_file.write_text(json.dumps(schema))
        
        monkeypatch.setattr("cvextract.customer_adjust._SCHEMA_PATH", schema_file)
        monkeypatch.setattr("cvextract.customer_adjust._RESEARCH_SCHEMA", None)
        
        result = _load_research_schema()
        assert result == schema

    def test_load_research_schema_caching(self, monkeypatch, tmp_path):
        """Test that schema is cached after first load."""
        schema = {"$schema": "test", "type": "object"}
        monkeypatch.setattr("cvextract.customer_adjust._RESEARCH_SCHEMA", schema)
        
        result = _load_research_schema()
        assert result == schema

    def test_load_research_schema_file_not_found(self, monkeypatch, caplog, tmp_path):
        """Test schema loading when file doesn't exist."""
        schema_file = tmp_path / "nonexistent.json"
        monkeypatch.setattr("cvextract.customer_adjust._SCHEMA_PATH", schema_file)
        monkeypatch.setattr("cvextract.customer_adjust._RESEARCH_SCHEMA", None)
        
        result = _load_research_schema()
        assert result is None
        assert "Failed to load research schema" in caplog.text


class TestResearchCompanyProfile:
    """Tests for _research_company_profile function."""

    def test_research_company_profile_uses_cache(self, tmp_path, caplog):
        """Test that cached research data is used when available."""
        caplog.set_level(logging.INFO)
        cache_file = tmp_path / "test.research.json"
        research_data = {
            "name": "Test Company",
            "domains": ["Technology"],
            "description": "A test company"
        }
        cache_file.write_text(json.dumps(research_data))
        
        result = _research_company_profile(
            "https://example.com",
            "test-key",
            "gpt-4o-mini",
            cache_file
        )
        
        assert result == research_data
        assert "Using cached company research" in caplog.text

    def test_research_company_profile_invalid_cache(self, tmp_path, caplog, monkeypatch):
        """Test that invalid cache is ignored and research proceeds."""
        cache_file = tmp_path / "test.research.json"
        cache_file.write_text("invalid json")
        
        # Mock the research to fail after cache fails
        monkeypatch.setattr("cvextract.customer_adjust._fetch_customer_page", Mock(return_value=""))
        
        result = _research_company_profile(
            "https://example.com",
            "test-key",
            "gpt-4o-mini",
            cache_file
        )
        
        assert result is None
        assert "Failed to load cached research" in caplog.text

    def test_research_company_profile_openai_unavailable(self, caplog, monkeypatch):
        """Test when OpenAI is not available."""
        monkeypatch.setattr("cvextract.customer_adjust.OpenAI", None)
        
        result = _research_company_profile(
            "https://example.com",
            "test-key",
            "gpt-4o-mini"
        )
        
        assert result is None
        assert "OpenAI unavailable" in caplog.text

    def test_research_company_profile_page_fetch_fails(self, caplog, monkeypatch):
        """Test when page fetch fails."""
        monkeypatch.setattr("cvextract.customer_adjust._fetch_customer_page", Mock(return_value=""))
        
        result = _research_company_profile(
            "https://example.com",
            "test-key",
            "gpt-4o-mini"
        )
        
        assert result is None
        assert "could not fetch page content" in caplog.text

    def test_research_company_profile_schema_load_fails(self, caplog, monkeypatch):
        """Test when schema loading fails."""
        monkeypatch.setattr("cvextract.customer_adjust._fetch_customer_page", Mock(return_value="content"))
        monkeypatch.setattr("cvextract.customer_adjust._load_research_schema", Mock(return_value=None))
        
        result = _research_company_profile(
            "https://example.com",
            "test-key",
            "gpt-4o-mini"
        )
        
        assert result is None
        assert "schema not available" in caplog.text

    def test_research_company_profile_success(self, tmp_path, caplog, monkeypatch):
        """Test successful company research."""
        caplog.set_level(logging.INFO)
        cache_file = tmp_path / "test.research.json"
        
        research_data = {
            "name": "Example Corp",
            "domains": ["Software", "Cloud"],
            "technology_signals": [
                {
                    "technology": "Python",
                    "interest_level": "high",
                    "confidence": 0.9
                }
            ]
        }
        
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps(research_data)
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.customer_adjust.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.customer_adjust._fetch_customer_page", Mock(return_value="<html>content</html>"))
        monkeypatch.setattr("cvextract.customer_adjust._load_research_schema", Mock(return_value={"type": "object"}))
        
        result = _research_company_profile(
            "https://example.com",
            "test-key",
            "gpt-4o-mini",
            cache_file
        )
        
        assert result == research_data
        assert "Successfully researched company profile" in caplog.text
        assert cache_file.exists()
        
        # Verify cached content
        with open(cache_file) as f:
            cached = json.load(f)
        assert cached == research_data

    def test_research_company_profile_empty_completion(self, caplog, monkeypatch):
        """Test when OpenAI returns empty completion."""
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_completion.choices = []
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.customer_adjust.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.customer_adjust._fetch_customer_page", Mock(return_value="content"))
        monkeypatch.setattr("cvextract.customer_adjust._load_research_schema", Mock(return_value={"type": "object"}))
        
        result = _research_company_profile(
            "https://example.com",
            "test-key",
            "gpt-4o-mini"
        )
        
        assert result is None
        assert "empty completion" in caplog.text

    def test_research_company_profile_invalid_json(self, caplog, monkeypatch):
        """Test when OpenAI returns invalid JSON."""
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        mock_message.content = "not valid json"
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.customer_adjust.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.customer_adjust._fetch_customer_page", Mock(return_value="content"))
        monkeypatch.setattr("cvextract.customer_adjust._load_research_schema", Mock(return_value={"type": "object"}))
        
        result = _research_company_profile(
            "https://example.com",
            "test-key",
            "gpt-4o-mini"
        )
        
        assert result is None
        assert "invalid JSON response" in caplog.text

    def test_research_company_profile_not_dict(self, caplog, monkeypatch):
        """Test when OpenAI returns non-dict JSON."""
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps(["array", "not", "dict"])
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.customer_adjust.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.customer_adjust._fetch_customer_page", Mock(return_value="content"))
        monkeypatch.setattr("cvextract.customer_adjust._load_research_schema", Mock(return_value={"type": "object"}))
        
        result = _research_company_profile(
            "https://example.com",
            "test-key",
            "gpt-4o-mini"
        )
        
        assert result is None
        assert "response is not a dict" in caplog.text

    def test_research_company_profile_missing_required_fields(self, caplog, monkeypatch):
        """Test when research data is missing required fields."""
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps({"description": "no name or domains"})
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.customer_adjust.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.customer_adjust._fetch_customer_page", Mock(return_value="content"))
        monkeypatch.setattr("cvextract.customer_adjust._load_research_schema", Mock(return_value={"type": "object"}))
        
        result = _research_company_profile(
            "https://example.com",
            "test-key",
            "gpt-4o-mini"
        )
        
        assert result is None
        assert "missing required fields" in caplog.text

    def test_research_company_profile_api_exception(self, caplog, monkeypatch):
        """Test when OpenAI API raises exception."""
        mock_openai = Mock()
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = RuntimeError("API error")
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.customer_adjust.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.customer_adjust._fetch_customer_page", Mock(return_value="content"))
        monkeypatch.setattr("cvextract.customer_adjust._load_research_schema", Mock(return_value={"type": "object"}))
        
        result = _research_company_profile(
            "https://example.com",
            "test-key",
            "gpt-4o-mini"
        )
        
        assert result is None
        assert "Company research error (RuntimeError)" in caplog.text


class TestAdjustForCustomerWithResearch:
    """Tests for adjust_for_customer with company research."""

    def test_adjust_for_customer_research_fails_skips_adjustment(self, caplog, monkeypatch):
        """Test that adjustment is skipped when research fails."""
        monkeypatch.setattr("cvextract.customer_adjust._research_company_profile", Mock(return_value=None))
        
        data = {"identity": {"title": "Test"}}
        result = adjust_for_customer(
            data,
            "https://example.com",
            api_key="test-key"
        )
        
        assert result == data
        assert "company research failed" in caplog.text

    def test_adjust_for_customer_with_research_success(self, caplog, monkeypatch, tmp_path):
        """Test successful adjustment with company research."""
        caplog.set_level(logging.INFO)
        
        research_data = {
            "name": "Tech Corp",
            "description": "A technology company",
            "domains": ["Cloud Computing", "AI"],
            "technology_signals": [
                {
                    "technology": "Python",
                    "interest_level": "high",
                    "confidence": 0.9,
                    "signals": ["Used in products", "Job postings"]
                }
            ]
        }
        
        adjusted_json = {"identity": {"title": "Adjusted"}}
        
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps({"adjusted_json": adjusted_json})
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.customer_adjust.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.customer_adjust._research_company_profile", Mock(return_value=research_data))
        
        data = {"identity": {"title": "Original"}}
        cache_file = tmp_path / "test.research.json"
        result = adjust_for_customer(
            data,
            "https://example.com",
            api_key="test-key",
            cache_path=cache_file
        )
        
        assert result == adjusted_json
        assert "adjusted to better fit" in caplog.text
        
        # Verify the system prompt includes research data
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        messages = call_kwargs["messages"]
        system_msg = messages[0]["content"]
        
        assert "Tech Corp" in system_msg
        assert "Cloud Computing" in system_msg
        assert "Python" in system_msg
        assert "high" in system_msg

    def test_adjust_for_customer_with_research_cache_path(self, monkeypatch, tmp_path):
        """Test that cache_path is passed to research function."""
        research_data = {
            "name": "Test",
            "domains": ["Tech"]
        }
        
        mock_research = Mock(return_value=research_data)
        monkeypatch.setattr("cvextract.customer_adjust._research_company_profile", mock_research)
        
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps({"adjusted_json": {}})
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.customer_adjust.OpenAI", mock_openai)
        
        cache_file = tmp_path / "test.research.json"
        adjust_for_customer(
            {},
            "https://example.com",
            api_key="test-key",
            cache_path=cache_file
        )
        
        # Verify cache_path was passed
        mock_research.assert_called_once()
        call_args = mock_research.call_args
        assert call_args[0][3] == cache_file
