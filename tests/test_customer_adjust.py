"""Tests for customer_adjust module."""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from cvextract.customer_adjust import (
    adjust_for_customer,
    _fetch_customer_page,
    _normalize_environment_list,
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
        
        data = {"identity": {"title": "Original"}}
        adjust_for_customer(data, "https://example.com", api_key="test-key")
        
        # Verify page text is capped in the payload
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        messages = call_kwargs["messages"]
        user_msg = messages[1]["content"]
        payload = json.loads(user_msg)
        assert len(payload["customer_page_excerpt"]) <= 30000
