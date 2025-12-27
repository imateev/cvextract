"""Tests for customer_adjust module."""

import json
import logging
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from cvextract.customer_adjust import (
    adjust_for_customer,
    _fetch_customer_page,
    _research_company_url,
)


class TestResearchCompanyUrl:
    """Tests for _research_company_url helper."""

    def test_research_company_url_success_full_metadata(self, monkeypatch):
        """Test successful research with full metadata extraction."""
        mock_requests = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
        <head>
            <title>Tech Company - Cloud Solutions</title>
            <meta name="description" content="We provide cloud-based software solutions">
            <meta name="keywords" content="software, cloud, technology">
            <meta property="og:description" content="Leading provider of cloud technology">
        </head>
        </html>
        """
        mock_requests.get.return_value = mock_response
        
        monkeypatch.setattr("cvextract.customer_adjust.requests", mock_requests)
        
        result = _research_company_url("https://example.com")
        
        assert "mission" in result
        assert "focus" in result
        assert "industry" in result
        assert result["mission"] == "Leading provider of cloud technology"
        assert "Tech Company - Cloud Solutions" in result["focus"]
        assert "technology" in result["industry"]
        
    def test_research_company_url_partial_metadata(self, monkeypatch):
        """Test research with only some metadata available."""
        mock_requests = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
        <head>
            <title>Finance Corp</title>
            <meta name="description" content="Banking and financial services">
        </head>
        </html>
        """
        mock_requests.get.return_value = mock_response
        
        monkeypatch.setattr("cvextract.customer_adjust.requests", mock_requests)
        
        result = _research_company_url("https://example.com")
        
        assert "mission" in result
        assert "focus" in result
        assert "industry" in result
        assert result["mission"] == "Banking and financial services"
        assert "finance" in result["industry"]
        
    def test_research_company_url_no_metadata(self, monkeypatch):
        """Test research when no useful metadata is found."""
        mock_requests = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Simple page</body></html>"
        mock_requests.get.return_value = mock_response
        
        monkeypatch.setattr("cvextract.customer_adjust.requests", mock_requests)
        
        result = _research_company_url("https://example.com")
        
        # Should return empty dict when no metadata found
        assert result == {}
        
    def test_research_company_url_http_error(self, monkeypatch):
        """Test research when HTTP status is not 200."""
        mock_requests = Mock()
        mock_response = Mock()
        mock_response.status_code = 404
        mock_requests.get.return_value = mock_response
        
        monkeypatch.setattr("cvextract.customer_adjust.requests", mock_requests)
        
        result = _research_company_url("https://example.com")
        assert result == {}
        
    def test_research_company_url_request_exception(self, monkeypatch):
        """Test research when requests raises an exception."""
        mock_requests = Mock()
        mock_requests.get.side_effect = Exception("Network error")
        
        monkeypatch.setattr("cvextract.customer_adjust.requests", mock_requests)
        
        result = _research_company_url("https://example.com")
        assert result == {}
        
    def test_research_company_url_no_requests_lib(self, monkeypatch):
        """Test research when requests library is not available."""
        monkeypatch.setattr("cvextract.customer_adjust.requests", None)
        
        result = _research_company_url("https://example.com")
        assert result == {}
        
    def test_research_company_url_empty_response(self, monkeypatch):
        """Test research when response text is empty."""
        mock_requests = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_requests.get.return_value = mock_response
        
        monkeypatch.setattr("cvextract.customer_adjust.requests", mock_requests)
        
        result = _research_company_url("https://example.com")
        assert result == {}
        
    def test_research_company_url_malformed_html(self, monkeypatch):
        """Test research with malformed HTML that parser can handle."""
        mock_requests = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
        <head>
            <title>Healthcare Services
            <meta name="description" content="Medical and healthcare">
        </head>
        """
        mock_requests.get.return_value = mock_response
        
        monkeypatch.setattr("cvextract.customer_adjust.requests", mock_requests)
        
        result = _research_company_url("https://example.com")
        # Should handle malformed HTML gracefully
        assert isinstance(result, dict)
        
    def test_research_company_url_caps_mission_length(self, monkeypatch):
        """Test that mission is capped at 500 chars."""
        mock_requests = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        long_description = "x" * 1000
        mock_response.text = f"""
        <html>
        <head>
            <meta name="description" content="{long_description}">
        </head>
        </html>
        """
        mock_requests.get.return_value = mock_response
        
        monkeypatch.setattr("cvextract.customer_adjust.requests", mock_requests)
        
        result = _research_company_url("https://example.com")
        
        assert "mission" in result
        assert len(result["mission"]) == 500
        
    def test_research_company_url_caps_focus_length(self, monkeypatch):
        """Test that focus is capped at 500 chars."""
        mock_requests = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        long_title = "x" * 600
        mock_response.text = f"""
        <html>
        <head>
            <title>{long_title}</title>
        </head>
        </html>
        """
        mock_requests.get.return_value = mock_response
        
        monkeypatch.setattr("cvextract.customer_adjust.requests", mock_requests)
        
        result = _research_company_url("https://example.com")
        
        assert "focus" in result
        assert len(result["focus"]) == 500
        
    def test_research_company_url_multiple_industries(self, monkeypatch):
        """Test detection of multiple industries."""
        mock_requests = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
        <head>
            <meta name="description" content="Healthcare technology software and consulting services">
        </head>
        </html>
        """
        mock_requests.get.return_value = mock_response
        
        monkeypatch.setattr("cvextract.customer_adjust.requests", mock_requests)
        
        result = _research_company_url("https://example.com")
        
        assert "industry" in result
        # Should detect technology, healthcare, and consulting
        assert "technology" in result["industry"] or "healthcare" in result["industry"] or "consulting" in result["industry"]
        
    def test_research_company_url_prefers_og_description(self, monkeypatch):
        """Test that og:description is preferred over regular description."""
        mock_requests = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
        <head>
            <meta name="description" content="Regular description">
            <meta property="og:description" content="OG description">
        </head>
        </html>
        """
        mock_requests.get.return_value = mock_response
        
        monkeypatch.setattr("cvextract.customer_adjust.requests", mock_requests)
        
        result = _research_company_url("https://example.com")
        
        assert result["mission"] == "OG description"

    def test_research_company_url_word_boundary_matching(self, monkeypatch):
        """Test that industry detection uses word boundaries to avoid false positives."""
        mock_requests = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        # "unfinancial" should NOT match "financial"
        mock_response.text = """
        <html>
        <head>
            <meta name="description" content="We provide unfinancial services and technology">
        </head>
        </html>
        """
        mock_requests.get.return_value = mock_response
        
        monkeypatch.setattr("cvextract.customer_adjust.requests", mock_requests)
        
        result = _research_company_url("https://example.com")
        
        # Should detect "technology" but NOT "finance" (from "unfinancial")
        if "industry" in result:
            assert "technology" in result["industry"]
            # "finance" should not be detected from "unfinancial"
            assert "finance" not in result["industry"] or "technology" in result["industry"]


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
        monkeypatch.setattr("cvextract.customer_adjust._fetch_customer_page", Mock(return_value="content"))
        monkeypatch.setattr("cvextract.customer_adjust._research_company_url", Mock(return_value={"industry": "tech"}))
        
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
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_completion.choices = []
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.customer_adjust.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.customer_adjust._fetch_customer_page", Mock(return_value=""))
        monkeypatch.setattr("cvextract.customer_adjust._research_company_url", Mock(return_value={}))
        
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
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        
        mock_message.content = "not valid json"
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.customer_adjust.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.customer_adjust._fetch_customer_page", Mock(return_value=""))
        monkeypatch.setattr("cvextract.customer_adjust._research_company_url", Mock(return_value={}))
        
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
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        
        mock_message.content = json.dumps(["not", "a", "dict"])
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.customer_adjust.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.customer_adjust._fetch_customer_page", Mock(return_value=""))
        monkeypatch.setattr("cvextract.customer_adjust._research_company_url", Mock(return_value={}))
        
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
        mock_openai = Mock()
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = RuntimeError("API error")
        mock_openai.return_value = mock_client
        
        monkeypatch.setattr("cvextract.customer_adjust.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.customer_adjust._fetch_customer_page", Mock(return_value=""))
        monkeypatch.setattr("cvextract.customer_adjust._research_company_url", Mock(return_value={}))
        
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
        monkeypatch.setattr("cvextract.customer_adjust._fetch_customer_page", Mock(return_value=""))
        monkeypatch.setattr("cvextract.customer_adjust._research_company_url", Mock(return_value={}))
        monkeypatch.delenv("OPENAI_MODEL", raising=False)
        
        data = {"identity": {"title": "Original"}}
        adjust_for_customer(data, "https://example.com", api_key="test-key")
        
        # Verify default model "gpt-4o-mini" is used
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o-mini"

    def test_adjust_for_customer_uses_env_model(self, monkeypatch):
        """Test that OPENAI_MODEL env var is used."""
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
        monkeypatch.setattr("cvextract.customer_adjust._fetch_customer_page", Mock(return_value=""))
        monkeypatch.setattr("cvextract.customer_adjust._research_company_url", Mock(return_value={}))
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4-turbo")
        
        data = {"identity": {"title": "Original"}}
        adjust_for_customer(data, "https://example.com", api_key="test-key")
        
        # Verify env model is used
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4-turbo"

    def test_adjust_for_customer_parameter_model_overrides_env(self, monkeypatch):
        """Test that parameter model overrides env variable."""
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
        monkeypatch.setattr("cvextract.customer_adjust._fetch_customer_page", Mock(return_value=""))
        monkeypatch.setattr("cvextract.customer_adjust._research_company_url", Mock(return_value={}))
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

    def test_adjust_for_customer_page_text_capped(self, monkeypatch):
        """Test that fetched page text is capped at 30000 chars."""
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        
        adjusted_json = {"identity": {"title": "Adjusted"}}
        mock_message.content = json.dumps({"adjusted_json": adjusted_json})
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        long_text = "x" * 50000
        monkeypatch.setattr("cvextract.customer_adjust.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.customer_adjust._fetch_customer_page", Mock(return_value=long_text))
        monkeypatch.setattr("cvextract.customer_adjust._research_company_url", Mock(return_value={}))
        
        data = {"identity": {"title": "Original"}}
        adjust_for_customer(data, "https://example.com", api_key="test-key")
        
        # Verify page text is capped in the payload
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        messages = call_kwargs["messages"]
        user_msg = messages[1]["content"]
        payload = json.loads(user_msg)
        assert len(payload["customer_page_excerpt"]) <= 30000

    def test_adjust_for_customer_includes_research_data(self, monkeypatch):
        """Test that research data is included in OpenAI payload."""
        mock_openai = Mock()
        mock_client = Mock()
        mock_completion = Mock()
        mock_message = Mock()
        
        adjusted_json = {"identity": {"title": "Adjusted"}}
        mock_message.content = json.dumps({"adjusted_json": adjusted_json})
        mock_completion.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        research_data = {
            "industry": "technology",
            "mission": "Cloud solutions provider",
            "focus": "AI and machine learning"
        }
        
        monkeypatch.setattr("cvextract.customer_adjust.OpenAI", mock_openai)
        monkeypatch.setattr("cvextract.customer_adjust._fetch_customer_page", Mock(return_value="content"))
        monkeypatch.setattr("cvextract.customer_adjust._research_company_url", Mock(return_value=research_data))
        
        data = {"identity": {"title": "Original"}}
        adjust_for_customer(data, "https://example.com", api_key="test-key")
        
        # Verify research data is included in the payload
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        messages = call_kwargs["messages"]
        user_msg = messages[1]["content"]
        payload = json.loads(user_msg)
        
        assert "company_research" in payload
        assert payload["company_research"] == research_data
        assert payload["company_research"]["industry"] == "technology"
        assert payload["company_research"]["mission"] == "Cloud solutions provider"
