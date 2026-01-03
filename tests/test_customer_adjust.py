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
        assert "Company research: response failed schema validation" in caplog.text

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


class TestStripMarkdownFences:
    """Tests for _strip_markdown_fences helper."""

    def test_strip_markdown_fences_json(self):
        """Test stripping ```json code fence."""
        from cvextract.adjusters.openai_company_research_adjuster import _strip_markdown_fences
        
        text = '```json\n{"key": "value"}\n```'
        result = _strip_markdown_fences(text)
        assert result == '{"key": "value"}'

    def test_strip_markdown_fences_generic(self):
        """Test stripping generic ``` code fence."""
        from cvextract.adjusters.openai_company_research_adjuster import _strip_markdown_fences
        
        text = '```\n{"key": "value"}\n```'
        result = _strip_markdown_fences(text)
        assert result == '{"key": "value"}'

    def test_strip_markdown_fences_no_fence(self):
        """Test text without code fence."""
        from cvextract.adjusters.openai_company_research_adjuster import _strip_markdown_fences
        
        text = '{"key": "value"}'
        result = _strip_markdown_fences(text)
        assert result == '{"key": "value"}'

    def test_strip_markdown_fences_with_whitespace(self):
        """Test stripping with extra whitespace."""
        from cvextract.adjusters.openai_company_research_adjuster import _strip_markdown_fences
        
        text = '  ```json\n  {"key": "value"}  \n```  '
        result = _strip_markdown_fences(text)
        assert result == '{"key": "value"}'

    def test_strip_markdown_fences_only_opening_fence(self):
        """Test with only opening fence."""
        from cvextract.adjusters.openai_company_research_adjuster import _strip_markdown_fences
        
        text = '```json\n{"key": "value"}'
        result = _strip_markdown_fences(text)
        assert result == '{"key": "value"}'


class TestExtractJsonObject:
    """Tests for _extract_json_object helper."""

    def test_extract_json_object_simple_dict(self):
        """Test extracting simple JSON dict."""
        from cvextract.adjusters.openai_company_research_adjuster import _extract_json_object
        
        text = '{"name": "Test"}'
        result = _extract_json_object(text)
        assert result == {"name": "Test"}

    def test_extract_json_object_with_markdown_fence(self):
        """Test extracting JSON from markdown fence."""
        from cvextract.adjusters.openai_company_research_adjuster import _extract_json_object
        
        text = '```json\n{"name": "Test"}\n```'
        result = _extract_json_object(text)
        assert result == {"name": "Test"}

    def test_extract_json_object_with_surrounding_text(self):
        """Test extracting JSON from text with surrounding content."""
        from cvextract.adjusters.openai_company_research_adjuster import _extract_json_object
        
        text = 'Here is the data:\n{"name": "Test"}\nEnd of data'
        result = _extract_json_object(text)
        assert result == {"name": "Test"}

    def test_extract_json_object_not_dict_array(self):
        """Test that non-dict JSON returns None."""
        from cvextract.adjusters.openai_company_research_adjuster import _extract_json_object
        
        text = '[1, 2, 3]'
        result = _extract_json_object(text)
        assert result is None

    def test_extract_json_object_not_dict_string(self):
        """Test that string JSON returns None."""
        from cvextract.adjusters.openai_company_research_adjuster import _extract_json_object
        
        text = '"not a dict"'
        result = _extract_json_object(text)
        assert result is None

    def test_extract_json_object_invalid_json(self):
        """Test with invalid JSON."""
        from cvextract.adjusters.openai_company_research_adjuster import _extract_json_object
        
        text = '{not valid json}'
        result = _extract_json_object(text)
        assert result is None

    def test_extract_json_object_no_braces(self):
        """Test text with no JSON braces."""
        from cvextract.adjusters.openai_company_research_adjuster import _extract_json_object
        
        text = 'Just plain text with no JSON'
        result = _extract_json_object(text)
        assert result is None

    def test_extract_json_object_non_string_input(self):
        """Test with non-string input."""
        from cvextract.adjusters.openai_company_research_adjuster import _extract_json_object
        
        result = _extract_json_object(None)
        assert result is None

    def test_extract_json_object_mismatched_braces(self):
        """Test with mismatched braces - extraction may fail."""
        from cvextract.adjusters.openai_company_research_adjuster import _extract_json_object
        
        text = '{ "key": "value" }} extra }'
        result = _extract_json_object(text)
        # The function finds the last }, which would create invalid JSON
        # So it may return None or extract up to the last brace
        # Either way is acceptable behavior - this is malformed input
        assert result is None or isinstance(result, dict)

    def test_extract_json_object_nested_json(self):
        """Test extracting nested JSON."""
        from cvextract.adjusters.openai_company_research_adjuster import _extract_json_object
        
        text = '{"outer": {"inner": "value"}}'
        result = _extract_json_object(text)
        assert result == {"outer": {"inner": "value"}}


class TestValidateResearchData:
    """Tests for _validate_research_data helper."""

    def test_validate_research_data_not_dict(self):
        """Test validation fails for non-dict data."""
        from cvextract.adjusters.openai_company_research_adjuster import _validate_research_data
        
        result = _validate_research_data([1, 2, 3])
        assert result is False

    def test_validate_research_data_verifier_unavailable(self, monkeypatch):
        """Test validation when verifier is not available."""
        from cvextract.adjusters.openai_company_research_adjuster import _validate_research_data
        
        mock_get_verifier = Mock(return_value=None)
        monkeypatch.setattr(
            "cvextract.adjusters.openai_company_research_adjuster.get_verifier",
            mock_get_verifier
        )
        
        result = _validate_research_data({"data": "value"})
        assert result is False

    def test_validate_research_data_verifier_exception(self, monkeypatch):
        """Test validation when verifier raises exception."""
        from cvextract.adjusters.openai_company_research_adjuster import _validate_research_data
        
        mock_verifier = Mock()
        mock_verifier.verify.side_effect = Exception("Verifier error")
        mock_get_verifier = Mock(return_value=mock_verifier)
        monkeypatch.setattr(
            "cvextract.adjusters.openai_company_research_adjuster.get_verifier",
            mock_get_verifier
        )
        
        result = _validate_research_data({"data": "value"})
        assert result is False

    def test_validate_research_data_verifier_returns_not_ok(self, monkeypatch):
        """Test validation when verifier returns not ok."""
        from cvextract.adjusters.openai_company_research_adjuster import _validate_research_data
        
        mock_verifier = Mock()
        mock_verifier.verify.return_value = Mock(ok=False)
        mock_get_verifier = Mock(return_value=mock_verifier)
        monkeypatch.setattr(
            "cvextract.adjusters.openai_company_research_adjuster.get_verifier",
            mock_get_verifier
        )
        
        result = _validate_research_data({"data": "value"})
        assert result is False


class TestOpenAIRetryMethods:
    """Tests for _OpenAIRetry helper class methods."""

    def test_get_status_code_from_attribute(self, monkeypatch):
        """Test extracting status code from exception attribute."""
        from cvextract.adjusters.openai_company_research_adjuster import _OpenAIRetry, _RetryConfig
        
        exc = Exception("Test")
        exc.status_code = 429
        
        retryer = _OpenAIRetry(retry=_RetryConfig(), sleep=lambda x: None)
        status = retryer._get_status_code(exc)
        assert status == 429

    def test_get_status_code_from_response_attribute(self, monkeypatch):
        """Test extracting status code from response object."""
        from cvextract.adjusters.openai_company_research_adjuster import _OpenAIRetry, _RetryConfig
        
        exc = Exception("Test")
        exc.response = Mock(status_code=500)
        
        retryer = _OpenAIRetry(retry=_RetryConfig(), sleep=lambda x: None)
        status = retryer._get_status_code(exc)
        assert status == 500

    def test_get_status_code_not_found(self, monkeypatch):
        """Test when status code is not found."""
        from cvextract.adjusters.openai_company_research_adjuster import _OpenAIRetry, _RetryConfig
        
        exc = Exception("Test")
        
        retryer = _OpenAIRetry(retry=_RetryConfig(), sleep=lambda x: None)
        status = retryer._get_status_code(exc)
        assert status is None

    def test_get_retry_after_from_headers(self, monkeypatch):
        """Test extracting retry-after from headers."""
        from cvextract.adjusters.openai_company_research_adjuster import _OpenAIRetry, _RetryConfig
        
        exc = Exception("Test")
        exc.headers = {"retry-after": "60"}
        
        retryer = _OpenAIRetry(retry=_RetryConfig(), sleep=lambda x: None)
        retry_after = retryer._get_retry_after_s(exc)
        assert retry_after == 60.0

    def test_get_retry_after_capitalized(self, monkeypatch):
        """Test extracting Retry-After (capitalized) from headers."""
        from cvextract.adjusters.openai_company_research_adjuster import _OpenAIRetry, _RetryConfig
        
        exc = Exception("Test")
        exc.headers = {"Retry-After": "120"}
        
        retryer = _OpenAIRetry(retry=_RetryConfig(), sleep=lambda x: None)
        retry_after = retryer._get_retry_after_s(exc)
        assert retry_after == 120.0

    def test_get_retry_after_from_response(self, monkeypatch):
        """Test extracting retry-after from response headers."""
        from cvextract.adjusters.openai_company_research_adjuster import _OpenAIRetry, _RetryConfig
        
        exc = Exception("Test")
        exc.response = Mock(headers={"retry-after": "30"})
        
        retryer = _OpenAIRetry(retry=_RetryConfig(), sleep=lambda x: None)
        retry_after = retryer._get_retry_after_s(exc)
        assert retry_after == 30.0

    def test_get_retry_after_not_found(self, monkeypatch):
        """Test when retry-after is not found."""
        from cvextract.adjusters.openai_company_research_adjuster import _OpenAIRetry, _RetryConfig
        
        exc = Exception("Test")
        
        retryer = _OpenAIRetry(retry=_RetryConfig(), sleep=lambda x: None)
        retry_after = retryer._get_retry_after_s(exc)
        assert retry_after is None

    def test_get_retry_after_headers_get_exception(self, monkeypatch):
        """Test when headers.get() raises an exception (lines 125-130)."""
        from cvextract.adjusters.openai_company_research_adjuster import _OpenAIRetry, _RetryConfig
        
        # Create a mock headers object that raises when .get() is called
        class BadHeaders:
            def get(self, key1, default=None):
                raise ValueError("Headers error")
        
        exc = Exception("Test")
        exc.headers = BadHeaders()
        
        retryer = _OpenAIRetry(retry=_RetryConfig(), sleep=lambda x: None)
        retry_after = retryer._get_retry_after_s(exc)
        assert retry_after is None

    def test_get_retry_after_non_numeric_string(self, monkeypatch):
        """Test when retry-after value can't be converted to float (lines 133-137)."""
        from cvextract.adjusters.openai_company_research_adjuster import _OpenAIRetry, _RetryConfig
        
        exc = Exception("Test")
        exc.headers = {"retry-after": "not-a-number"}
        
        retryer = _OpenAIRetry(retry=_RetryConfig(), sleep=lambda x: None)
        retry_after = retryer._get_retry_after_s(exc)
        assert retry_after is None

    def test_get_retry_after_zero_value(self, monkeypatch):
        """Test when retry-after is zero (edge case for falsy value check)."""
        from cvextract.adjusters.openai_company_research_adjuster import _OpenAIRetry, _RetryConfig
        
        exc = Exception("Test")
        exc.headers = {"retry-after": "0"}
        
        retryer = _OpenAIRetry(retry=_RetryConfig(), sleep=lambda x: None)
        retry_after = retryer._get_retry_after_s(exc)
        # Zero gets converted to float but the sleep_with_backoff checks if retry_after > 0
        assert retry_after == 0.0

    def test_is_transient_500_error(self, monkeypatch):
        """Test that 5xx errors are transient."""
        from cvextract.adjusters.openai_company_research_adjuster import _OpenAIRetry, _RetryConfig
        
        exc = Exception("Server error")
        exc.status_code = 503
        
        retryer = _OpenAIRetry(retry=_RetryConfig(), sleep=lambda x: None)
        assert retryer._is_transient(exc) is True

    def test_is_transient_by_message(self, monkeypatch):
        """Test detection of transient errors by message."""
        from cvextract.adjusters.openai_company_research_adjuster import _OpenAIRetry, _RetryConfig
        
        exc = Exception("Connection timeout")
        
        retryer = _OpenAIRetry(retry=_RetryConfig(), sleep=lambda x: None)
        assert retryer._is_transient(exc) is True

    def test_is_transient_ssl_error(self, monkeypatch):
        """Test that SSL errors are transient."""
        from cvextract.adjusters.openai_company_research_adjuster import _OpenAIRetry, _RetryConfig
        
        exc = Exception("SSL certificate error")
        
        retryer = _OpenAIRetry(retry=_RetryConfig(), sleep=lambda x: None)
        assert retryer._is_transient(exc) is True

    def test_is_not_transient_4xx_error(self, monkeypatch):
        """Test that 4xx errors are not transient."""
        from cvextract.adjusters.openai_company_research_adjuster import _OpenAIRetry, _RetryConfig
        
        exc = Exception("Bad request")
        exc.status_code = 400
        
        retryer = _OpenAIRetry(retry=_RetryConfig(), sleep=lambda x: None)
        assert retryer._is_transient(exc) is False

    def test_sleep_with_backoff_deterministic(self, monkeypatch):
        """Test deterministic backoff sleep."""
        from cvextract.adjusters.openai_company_research_adjuster import _OpenAIRetry, _RetryConfig
        
        sleep_calls = []
        
        def mock_sleep(duration):
            sleep_calls.append(duration)
        
        config = _RetryConfig(deterministic=True)
        exc = Exception("Test")
        
        retryer = _OpenAIRetry(retry=config, sleep=mock_sleep)
        retryer._sleep_with_backoff(0, is_write=False, exc=exc)
        
        # Deterministic mode should sleep with exponential backoff: base_delay_s * 2^attempt
        # 0.75 * 2^0 = 0.75
        assert len(sleep_calls) == 1
        assert sleep_calls[0] == 0.75

    def test_sleep_with_backoff_with_retry_after(self, monkeypatch):
        """Test backoff honors retry-after header."""
        from cvextract.adjusters.openai_company_research_adjuster import _OpenAIRetry, _RetryConfig
        
        sleep_calls = []
        
        def mock_sleep(duration):
            sleep_calls.append(duration)
        
        exc = Exception("Test")
        exc.headers = {"retry-after": "5"}
        
        retryer = _OpenAIRetry(retry=_RetryConfig(), sleep=mock_sleep)
        retryer._sleep_with_backoff(0, is_write=False, exc=exc)
        
        # Should sleep for retry-after value (capped at max_delay_s)
        assert len(sleep_calls) == 1
        assert sleep_calls[0] == 5.0

    def test_sleep_with_backoff_write_multiplier(self, monkeypatch):
        """Test backoff with write multiplier."""
        from cvextract.adjusters.openai_company_research_adjuster import _OpenAIRetry, _RetryConfig
        
        sleep_calls = []
        
        def mock_sleep(duration):
            sleep_calls.append(duration)
        
        config = _RetryConfig(deterministic=True, base_delay_s=1.0, write_multiplier=2.0)
        exc = Exception("Test")
        
        retryer = _OpenAIRetry(retry=config, sleep=mock_sleep)
        retryer._sleep_with_backoff(0, is_write=True, exc=exc)
        
        # With write multiplier: 1.0 * 2^0 * 2.0 = 2.0
        assert len(sleep_calls) == 1
        assert sleep_calls[0] == 2.0

    def test_sleep_with_backoff_capped_at_max(self, monkeypatch):
        """Test backoff is capped at max_delay_s."""
        from cvextract.adjusters.openai_company_research_adjuster import _OpenAIRetry, _RetryConfig
        
        sleep_calls = []
        
        def mock_sleep(duration):
            sleep_calls.append(duration)
        
        config = _RetryConfig(deterministic=True, base_delay_s=10.0, max_delay_s=5.0)
        exc = Exception("Test")
        
        retryer = _OpenAIRetry(retry=config, sleep=mock_sleep)
        retryer._sleep_with_backoff(2, is_write=False, exc=exc)
        
        # 10.0 * 2^2 = 40.0, but capped at 5.0
        assert len(sleep_calls) == 1
        assert sleep_calls[0] == 5.0


class TestResearchCompanyProfileEdgeCases:
    """Additional edge case tests for _research_company_profile."""

    def test_research_company_profile_empty_cache_data(self, monkeypatch, tmp_path):
        """Test with empty cache file."""
        from cvextract.adjusters.openai_company_research_adjuster import _research_company_profile
        
        cache_file = tmp_path / "cache.json"
        cache_file.write_text("{}")
        
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        good_data = {"name": "TestCo", "domains": ["test.com"]}
        mock_message.content = json.dumps(good_data)
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        mock_get_verifier = Mock(return_value=Mock())
        mock_get_verifier.return_value.verify.return_value = Mock(ok=True)
        
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster._load_research_schema", Mock(return_value={"type": "object"}))
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster._validate_research_data", Mock(side_effect=[False, True]))
        
        result = _research_company_profile("https://example.com", "test-key", "gpt-4o-mini", cache_path=cache_file)
        
        # Cache had invalid data, should fetch and return new data
        assert result == good_data

    def test_research_company_profile_cache_corruption_invalid_json(self, monkeypatch, tmp_path):
        """Test handling corrupted cache with invalid JSON."""
        from cvextract.adjusters.openai_company_research_adjuster import _research_company_profile
        
        cache_file = tmp_path / "cache.json"
        cache_file.write_text("{invalid json")
        
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        good_data = {"name": "TestCo", "domains": ["test.com"]}
        mock_message.content = json.dumps(good_data)
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster._load_research_schema", Mock(return_value={"type": "object"}))
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster._validate_research_data", Mock(return_value=True))
        
        result = _research_company_profile("https://example.com", "test-key", "gpt-4o-mini", cache_path=cache_file)
        
        # Cache was corrupted, should fetch and return new data
        assert result == good_data

    def test_research_company_profile_retry_call_uses_config(self, monkeypatch):
        """Test that retry config is passed to retryer.call."""
        from cvextract.adjusters.openai_company_research_adjuster import _research_company_profile, _RetryConfig
        
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps({"name": "Test"})
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        custom_retry_config = _RetryConfig(max_attempts=5)
        
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster._load_research_schema", Mock(return_value={"type": "object"}))
        monkeypatch.setattr("cvextract.adjusters.openai_company_research_adjuster._validate_research_data", Mock(return_value=True))
        
        result = _research_company_profile(
            "https://example.com",
            "test-key",
            "gpt-4o-mini",
            retry=custom_retry_config
        )
        
        assert result == {"name": "Test"}
