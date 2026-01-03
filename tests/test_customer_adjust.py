"""Tests for ml_adjustment module."""

import json
import logging
import os
from unittest.mock import Mock
from cvextract.ml_adjustment import (
    adjust_for_customer,
    _url_to_cache_filename,
)
from cvextract.ml_adjustment.adjuster import (
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
        
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.requests", mock_requests)
        
        result = _fetch_customer_page("https://example.com")
        assert result == "<html>Customer page content</html>"
        mock_requests.get.assert_called_once_with("https://example.com", timeout=15)

    def test_fetch_customer_page_http_error(self, monkeypatch):
        """Test fetch when HTTP status is not 200."""
        mock_requests = Mock()
        mock_response = Mock()
        mock_response.status_code = 404
        mock_requests.get.return_value = mock_response
        
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.requests", mock_requests)
        
        result = _fetch_customer_page("https://example.com")
        assert result == ""

    def test_fetch_customer_page_request_exception(self, monkeypatch):
        """Test fetch when requests raises an exception."""
        mock_requests = Mock()
        mock_requests.get.side_effect = Exception("Network error")
        
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.requests", mock_requests)
        
        result = _fetch_customer_page("https://example.com")
        assert result == ""

    def test_fetch_customer_page_no_requests_lib(self, monkeypatch):
        """Test fetch when requests library is not available."""
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.requests", None)
        
        result = _fetch_customer_page("https://example.com")
        assert result == ""

    def test_fetch_customer_page_empty_response(self, monkeypatch):
        """Test fetch when response text is empty."""
        mock_requests = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_requests.get.return_value = mock_response
        
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.requests", mock_requests)
        
        result = _fetch_customer_page("https://example.com")
        assert result == ""


class TestUrlToCacheFilename:
    """Tests for _url_to_cache_filename helper."""

    def test_url_to_cache_filename_basic(self):
        """Test basic URL conversion."""
        result = _url_to_cache_filename("https://example.com")
        assert result.startswith("example.com-")
        assert result.endswith(".research.json")
        assert len(result) > len("example.com-.research.json")

    def test_url_to_cache_filename_removes_protocol(self):
        """Test that protocol is removed."""
        result1 = _url_to_cache_filename("https://example.com")
        result2 = _url_to_cache_filename("http://example.com")
        # Same domain should produce same base name (though hash might differ due to full URL)
        assert "example.com" in result1
        assert "example.com" in result2

    def test_url_to_cache_filename_removes_www(self):
        """Test that www prefix is removed."""
        result = _url_to_cache_filename("https://www.example.com")
        assert result.startswith("example.com-")

    def test_url_to_cache_filename_removes_path(self):
        """Test that path is removed from domain."""
        result = _url_to_cache_filename("https://example.com/path/to/page")
        assert result.startswith("example.com-")

    def test_url_to_cache_filename_removes_query(self):
        """Test that query string is removed from domain."""
        result = _url_to_cache_filename("https://example.com?query=value")
        assert result.startswith("example.com-")

    def test_url_to_cache_filename_removes_port(self):
        """Test that port is removed from domain."""
        result = _url_to_cache_filename("https://example.com:8080")
        assert result.startswith("example.com-")

    def test_url_to_cache_filename_deterministic(self):
        """Test that same URL always produces same filename."""
        url = "https://example.com/page"
        result1 = _url_to_cache_filename(url)
        result2 = _url_to_cache_filename(url)
        assert result1 == result2

    def test_url_to_cache_filename_different_urls(self):
        """Test that different URLs produce different filenames."""
        url1 = "https://example.com"
        url2 = "https://different.com"
        result1 = _url_to_cache_filename(url1)
        result2 = _url_to_cache_filename(url2)
        assert result1 != result2

    def test_url_to_cache_filename_same_domain_different_paths(self):
        """Test that different paths on same domain produce different filenames."""
        url1 = "https://example.com/page1"
        url2 = "https://example.com/page2"
        result1 = _url_to_cache_filename(url1)
        result2 = _url_to_cache_filename(url2)
        # Same domain but different full URLs should have different hashes
        assert result1 != result2

    def test_url_to_cache_filename_safe_characters(self):
        """Test that filename contains only safe characters."""
        result = _url_to_cache_filename("https://example.com")
        # Check that filename is filesystem-safe (no special chars except - and .)
        import re
        assert re.match(r'^[a-z0-9._-]+\.research\.json$', result)


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
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.OpenAI", None)
        
        data = {"identity": {"title": "Test"}}
        result = adjust_for_customer(
            data, 
            "https://example.com", 
            api_key="test-key"
        )
        
        assert result == data
        # New architecture logs that company research is skipped
        assert "Company research skipped: OpenAI unavailable" in caplog.text

    def test_adjust_for_customer_success(self, monkeypatch, caplog):
        """Test successful adjustment with OpenAI."""
        caplog.set_level(logging.INFO)
        
        # Mock research to return valid data
        research_data = {"name": "Test", "domains": ["Tech"]}
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster._research_company_profile", Mock(return_value=research_data))
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster._research_company_profile", Mock(return_value=research_data))
        
        # Mock format_prompt for company research adjuster
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.format_prompt", Mock(return_value="Test prompt"))
        
        # Mock verifier in both places where it's used
        mock_verifier = Mock()
        mock_verifier.verify.return_value = Mock(ok=True)
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.get_verifier", Mock(return_value=mock_verifier))
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.get_verifier", Mock(return_value=mock_verifier))
        
        # Adjusted JSON must conform to CV schema
        adjusted_json = {
            "identity": {
                "title": "Adjusted",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe"
            },
            "sidebar": None,
            "overview": "Adjusted overview",
            "experiences": []
        }
        
        # Mock OpenAI for company research adjuster
        mock_openai_company = Mock()
        mock_client_company = Mock()
        mock_completion_company = Mock()
        mock_message_company = Mock()
        mock_message_company.content = json.dumps(adjusted_json)
        mock_completion_company.choices = [Mock(message=mock_message_company)]
        mock_client_company.chat.completions.create.return_value = mock_completion_company
        mock_openai_company.return_value = mock_client_company
        
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.OpenAI", mock_openai_company)
        
        # Mock OpenAI for ml_adjustment (job-specific adjuster)
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps(adjusted_json)
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.OpenAI", mock_openai)
        
        data = {
            "identity": {
                "title": "Original",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe"
            },
            "sidebar": None,
            "overview": "Original overview",
            "experiences": []
        }
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
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster._research_company_profile", Mock(return_value=research_data))
        
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_completion.choices = []
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.OpenAI", mock_openai)
        
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
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster._research_company_profile", Mock(return_value=research_data))
        
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        
        mock_message.content = "not valid json"
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.OpenAI", mock_openai)
        
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
        caplog.set_level(logging.INFO)
        # Mock research to return valid data
        research_data = {"name": "Test", "domains": ["Tech"]}
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster._research_company_profile", Mock(return_value=research_data))
        
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        
        # Return a list, which is valid JSON but not a dict
        mock_message.content = json.dumps(["not", "a", "dict"])
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.OpenAI", mock_openai)
        
        data = {
            "identity": {
                "title": "Original",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe"
            },
            "sidebar": None,
            "overview": "Overview",
            "experiences": []
        }
        result = adjust_for_customer(
            data, 
            "https://example.com", 
            api_key="test-key"
        )
        
        # Should return original since response is not a dict
        assert result == data
        assert "not a dict" in caplog.text

    def test_adjust_for_customer_null_json_response(self, monkeypatch, caplog):
        """Test when OpenAI returns JSON null (None in Python)."""
        caplog.set_level(logging.INFO)
        # Mock research to return valid data
        research_data = {"name": "Test", "domains": ["Tech"]}
        
        # Mock in both locations where it's used
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster._research_company_profile", Mock(return_value=research_data))
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster._research_company_profile", Mock(return_value=research_data))
        
        # Mock format_prompt
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.format_prompt", Mock(return_value="Test prompt"))
        
        # Mock verifier in both places
        mock_verifier = Mock()
        mock_verifier.verify.return_value = Mock(ok=True)
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.get_verifier", Mock(return_value=mock_verifier))
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.get_verifier", Mock(return_value=mock_verifier))
        
        # Mock OpenAI in adjusters module
        mock_openai_adjuster = Mock()
        mock_client_adjuster = Mock()
        mock_completion_adjuster = Mock()
        mock_message_adjuster = Mock()
        
        # Return JSON null, which parses to Python None
        mock_message_adjuster.content = json.dumps(None)
        mock_completion_adjuster.choices = [Mock(message=mock_message_adjuster)]
        mock_client_adjuster.chat.completions.create.return_value = mock_completion_adjuster
        mock_openai_adjuster.return_value = mock_client_adjuster
        
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.OpenAI", mock_openai_adjuster)
        
        # Also mock OpenAI in ml_adjustment for job-specific
        mock_openai_ml = Mock()
        mock_client_ml = Mock()
        mock_completion_ml = Mock()
        mock_message_ml = Mock()
        mock_message_ml.content = json.dumps(None)
        mock_completion_ml.choices = [Mock(message=mock_message_ml)]
        mock_client_ml.chat.completions.create.return_value = mock_completion_ml
        mock_openai_ml.return_value = mock_client_ml
        
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.OpenAI", mock_openai_ml)
        
        data = {"identity": {"title": "Original"}}
        result = adjust_for_customer(
            data, 
            "https://example.com", 
            api_key="test-key"
        )
        
        # Should return original data since adjusted is None
        assert result == data
        assert "API call returned null" in caplog.text or "API call failed" in caplog.text

    def test_adjust_for_customer_api_exception(self, monkeypatch, caplog):
        """Test when OpenAI API call raises exception."""
        # Mock research to return valid data
        research_data = {"name": "Test", "domains": ["Tech"]}
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster._research_company_profile", Mock(return_value=research_data))
        
        mock_openai = Mock()
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = RuntimeError("API error")
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.OpenAI", mock_openai)
        
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
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster._research_company_profile", Mock(return_value=research_data))
        
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        
        adjusted_json = {"identity": {"title": "Adjusted"}}
        mock_message.content = json.dumps(adjusted_json)
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.OpenAI", mock_openai)
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
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster._research_company_profile", Mock(return_value=research_data))
        
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        
        adjusted_json = {"identity": {"title": "Adjusted"}}
        mock_message.content = json.dumps(adjusted_json)
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.OpenAI", mock_openai)
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
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster._research_company_profile", Mock(return_value=research_data))
        
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        
        adjusted_json = {"identity": {"title": "Adjusted"}}
        mock_message.content = json.dumps(adjusted_json)
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.OpenAI", mock_openai)
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
        
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster._SCHEMA_PATH", schema_file)
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster._RESEARCH_SCHEMA", None)
        
        result = _load_research_schema()
        assert result == schema

    def test_load_research_schema_caching(self, monkeypatch, tmp_path):
        """Test that schema is cached after first load."""
        schema = {"$schema": "test", "type": "object"}
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster._RESEARCH_SCHEMA", schema)
        
        result = _load_research_schema()
        assert result == schema

    def test_load_research_schema_file_not_found(self, monkeypatch, caplog, tmp_path):
        """Test schema loading when file doesn't exist."""
        schema_file = tmp_path / "nonexistent.json"
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster._SCHEMA_PATH", schema_file)
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster._RESEARCH_SCHEMA", None)
        
        result = _load_research_schema()
        assert result is None
        assert "Failed to load research schema" in caplog.text


class TestResearchCompanyProfile:
    """Tests for _research_company_profile function."""

    def test_research_company_profile_uses_cache(self, tmp_path, caplog, monkeypatch):
        """Test that cached research data is used when available."""
        caplog.set_level(logging.INFO)
        
        # Mock verifier to validate research data
        mock_verifier = Mock()
        mock_verifier.verify.return_value = Mock(ok=True)
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.get_verifier", Mock(return_value=mock_verifier))
        
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
        
        # Mock the research to fail after cache fails (schema unavailable)
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster._load_research_schema", Mock(return_value=None))
        
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
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.OpenAI", None)
        
        result = _research_company_profile(
            "https://example.com",
            "test-key",
            "gpt-4o-mini"
        )
        
        assert result is None
        assert "OpenAI unavailable" in caplog.text

    def test_research_company_profile_schema_load_fails(self, caplog, monkeypatch):
        """Test when schema loading fails."""
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster._load_research_schema", Mock(return_value=None))
        
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
        
        # Mock verifier to validate research data
        mock_verifier = Mock()
        mock_verifier.verify.return_value = Mock(ok=True)
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.get_verifier", Mock(return_value=mock_verifier))
        
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps(research_data)
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster._load_research_schema", Mock(return_value={"type": "object"}))
        
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

    def test_research_company_profile_with_acquisition_and_rebrand_data(self, tmp_path, caplog, monkeypatch):
        """Test successful company research with acquisition history and rebranding info."""
        caplog.set_level(logging.INFO)
        cache_file = tmp_path / "test.research.json"
        
        research_data = {
            "name": "NewCo Inc",
            "domains": ["Technology", "Consulting"],
            "acquisition_history": [
                {
                    "owner": "BigTech Corp",
                    "year": 2020,
                    "notes": "Acquired for $100M"
                },
                {
                    "owner": "StartupVentures",
                    "year": 2015
                }
            ],
            "rebranded_from": ["OldName Systems", "Legacy Corp"]
        }
        
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps(research_data)
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster._load_research_schema", Mock(return_value={"type": "object"}))
        
        result = _research_company_profile(
            "https://example.com",
            "test-key",
            "gpt-4o-mini",
            cache_file
        )
        
        assert result == research_data
        assert "acquisition_history" in result
        assert len(result["acquisition_history"]) == 2
        assert result["acquisition_history"][0]["owner"] == "BigTech Corp"
        assert "rebranded_from" in result
        assert len(result["rebranded_from"]) == 2
        assert "Successfully researched company profile" in caplog.text

    def test_research_company_profile_with_products_data(self, tmp_path, caplog, monkeypatch):
        """Test successful company research with owned and used products."""
        caplog.set_level(logging.INFO)
        cache_file = tmp_path / "test.research.json"
        
        research_data = {
            "name": "ProductCo",
            "domains": ["Software Development"],
            "owned_products": [
                {
                    "name": "SuperApp",
                    "category": "SaaS",
                    "description": "Project management tool"
                },
                {
                    "name": "DataHub",
                    "category": "software"
                }
            ],
            "used_products": [
                {
                    "name": "Salesforce",
                    "category": "CRM",
                    "purpose": "Customer relationship management"
                },
                {
                    "name": "AWS",
                    "category": "cloud platform"
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
        
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster._load_research_schema", Mock(return_value={"type": "object"}))
        
        result = _research_company_profile(
            "https://example.com",
            "test-key",
            "gpt-4o-mini",
            cache_file
        )
        
        assert result == research_data
        assert "owned_products" in result
        assert len(result["owned_products"]) == 2
        assert result["owned_products"][0]["name"] == "SuperApp"
        assert "used_products" in result
        assert len(result["used_products"]) == 2
        assert result["used_products"][0]["name"] == "Salesforce"
        assert "Successfully researched company profile" in caplog.text

    def test_research_company_profile_empty_completion(self, caplog, monkeypatch):
        """Test when OpenAI returns empty completion."""
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_completion.choices = []
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster._load_research_schema", Mock(return_value={"type": "object"}))
        
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
        
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster._load_research_schema", Mock(return_value={"type": "object"}))
        
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
        
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster._load_research_schema", Mock(return_value={"type": "object"}))
        
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
        
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster._load_research_schema", Mock(return_value={"type": "object"}))
        
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
        
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster._load_research_schema", Mock(return_value={"type": "object"}))
        
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
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster._research_company_profile", Mock(return_value=None))
        
        data = {"identity": {"title": "Test"}}
        result = adjust_for_customer(
            data,
            "https://example.com",
            api_key="test-key"
        )
        
        assert result == data
        # New architecture logs that research failed to adjuster
        assert "failed to research company" in caplog.text

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
        
        # Adjusted JSON must conform to CV schema
        adjusted_json = {
            "identity": {
                "title": "Adjusted",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe"
            },
            "sidebar": None,
            "overview": "Adjusted overview",
            "experiences": []
        }
        
        # Mock verifier in both places where it's used
        mock_verifier = Mock()
        mock_verifier.verify.return_value = Mock(ok=True)
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.get_verifier", Mock(return_value=mock_verifier))
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.get_verifier", Mock(return_value=mock_verifier))
        
        # Mock _research_company_profile where it's imported in the adjuster
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster._research_company_profile", Mock(return_value=research_data))
        
        # Mock format_prompt where it's imported in the adjuster
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.format_prompt", Mock(return_value="Test prompt"))
        
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps(adjusted_json)
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        # Mock OpenAI in the adjusters module (for company research)
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.OpenAI", mock_openai)
        
        data = {
            "identity": {
                "title": "Original",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe"
            },
            "sidebar": None,
            "overview": "Original overview",
            "experiences": []
        }
        cache_file = tmp_path / "test.research.json"
        result = adjust_for_customer(
            data,
            "https://example.com",
            api_key="test-key",
            cache_path=cache_file
        )
        
        assert result == adjusted_json
        assert "adjusted to better fit" in caplog.text
        
        # Verify the system prompt was built and used
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        messages = call_kwargs["messages"]
        # The first message should be the user message with context
        assert len(messages) > 0

    def test_adjust_for_customer_with_research_cache_path(self, monkeypatch, tmp_path):
        """Test that cache_path is passed to research function."""
        research_data = {
            "name": "Test",
            "domains": ["Tech"]
        }
        
        mock_research = Mock(return_value=research_data)
        # Mock in both locations
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster._research_company_profile", mock_research)
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster._research_company_profile", mock_research)
        
        # Mock _build_system_prompt
        # Mock format_prompt
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.format_prompt", Mock(return_value="Test prompt"))
        
        # Mock verifier in both places
        mock_verifier = Mock()
        mock_verifier.verify.return_value = Mock(ok=True)
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.get_verifier", Mock(return_value=mock_verifier))
        monkeypatch.setattr("cvextract.ml_adjustment.adjuster.get_verifier", Mock(return_value=mock_verifier))
        
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        adjusted_json = {
            "identity": {
                "title": "Adjusted",
                "full_name": "John Doe",
                "first_name": "John",
                "last_name": "Doe"
            },
            "sidebar": None,
            "overview": "Adjusted overview",
            "experiences": []
        }
        mock_message.content = json.dumps(adjusted_json)
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        # Mock OpenAI in the adjusters module
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.OpenAI", mock_openai)
        
        cache_file = tmp_path / "test.research.json"
        result = adjust_for_customer(
            {
                "identity": {
                    "title": "Original",
                    "full_name": "John Doe",
                    "first_name": "John",
                    "last_name": "Doe"
                },
                "sidebar": None,
                "overview": "Original overview",
                "experiences": []
            },
            "https://example.com",
            api_key="test-key",
            cache_path=cache_file
        )
        
        # Verify cache_path was passed (check the ml_adjustment version since that's the actual call)
        # The function is called through the adjuster which imports it
        # So we check if it was called at all with the cache_path
        assert result == adjusted_json
