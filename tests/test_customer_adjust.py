"""Tests for research and company analysis functions."""

import json
import logging
import os
from unittest.mock import Mock
from cvextract.adjusters.openai_company_research_adjuster import (
    _url_to_cache_filename,
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
        
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.requests", mock_requests)
        
        result = _fetch_customer_page("https://example.com")
        assert result == "<html>Customer page content</html>"
        mock_requests.get.assert_called_once_with("https://example.com", timeout=15)

    def test_fetch_customer_page_http_error(self, monkeypatch):
        """Test fetch when HTTP status is not 200."""
        mock_requests = Mock()
        mock_response = Mock()
        mock_response.status_code = 404
        mock_requests.get.return_value = mock_response
        
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.requests", mock_requests)
        
        result = _fetch_customer_page("https://example.com")
        assert result == ""

    def test_fetch_customer_page_request_exception(self, monkeypatch):
        """Test fetch when requests raises an exception."""
        mock_requests = Mock()
        mock_requests.get.side_effect = Exception("Network error")
        
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.requests", mock_requests)
        
        result = _fetch_customer_page("https://example.com")
        assert result == ""

    def test_fetch_customer_page_no_requests_lib(self, monkeypatch):
        """Test fetch when requests library is not available."""
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.requests", None)
        
        result = _fetch_customer_page("https://example.com")
        assert result == ""

    def test_fetch_customer_page_empty_response(self, monkeypatch):
        """Test fetch when response text is empty."""
        mock_requests = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_requests.get.return_value = mock_response
        
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.requests", mock_requests)
        
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

class TestLoadResearchSchema:
    """Tests for _load_research_schema function."""

    def test_load_research_schema_success(self, monkeypatch, tmp_path):
        """Test successful schema loading."""
        schema = {"$schema": "test", "type": "object"}
        schema_file = tmp_path / "research_schema.json"
        schema_file.write_text(json.dumps(schema))
        
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster._SCHEMA_PATH", schema_file)
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster._RESEARCH_SCHEMA", None)
        
        result = _load_research_schema()
        assert result == schema

    def test_load_research_schema_caching(self, monkeypatch, tmp_path):
        """Test that schema is cached after first load."""
        schema = {"$schema": "test", "type": "object"}
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster._RESEARCH_SCHEMA", schema)
        
        result = _load_research_schema()
        assert result == schema

    def test_load_research_schema_file_not_found(self, monkeypatch, caplog, tmp_path):
        """Test schema loading when file doesn't exist."""
        schema_file = tmp_path / "nonexistent.json"
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster._SCHEMA_PATH", schema_file)
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster._RESEARCH_SCHEMA", None)
        
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
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.get_verifier", Mock(return_value=mock_verifier))
        
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
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster._load_research_schema", Mock(return_value=None))
        
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
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.OpenAI", None)
        
        result = _research_company_profile(
            "https://example.com",
            "test-key",
            "gpt-4o-mini"
        )
        
        assert result is None
        assert "OpenAI unavailable" in caplog.text

    def test_research_company_profile_schema_load_fails(self, caplog, monkeypatch):
        """Test when schema loading fails."""
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster._load_research_schema", Mock(return_value=None))
        
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
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.get_verifier", Mock(return_value=mock_verifier))
        
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps(research_data)
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster._load_research_schema", Mock(return_value={"type": "object"}))
        
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
        
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster._load_research_schema", Mock(return_value={"type": "object"}))
        
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
        
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster._load_research_schema", Mock(return_value={"type": "object"}))
        
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
        
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster._load_research_schema", Mock(return_value={"type": "object"}))
        
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
        
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster._load_research_schema", Mock(return_value={"type": "object"}))
        
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
        
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster._load_research_schema", Mock(return_value={"type": "object"}))
        
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
        
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster._load_research_schema", Mock(return_value={"type": "object"}))
        
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
        
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster._load_research_schema", Mock(return_value={"type": "object"}))
        
        result = _research_company_profile(
            "https://example.com",
            "test-key",
            "gpt-4o-mini"
        )
        
        assert result is None
        assert "Company research error (RuntimeError)" in caplog.text

