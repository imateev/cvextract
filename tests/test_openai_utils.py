"""Tests for shared OpenAI helper utilities."""

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import cvextract.openai_utils as openai_utils


def _mock_files_resource():
    resource = MagicMock()
    files_obj = MagicMock()
    files_obj.joinpath.return_value = resource
    return files_obj


def test_get_cached_resource_path_uses_existing_cache(tmp_path):
    """get_cached_resource_path returns cached file without reading resource."""
    cache_dir = tmp_path / "cvextract"
    cache_dir.mkdir()
    cache_path = cache_dir / "resource.json"
    cache_path.write_text("cached", encoding="utf-8")

    with patch(
        "cvextract.openai_utils.tempfile.gettempdir",
        return_value=str(tmp_path),
    ), patch(
        "cvextract.openai_utils.files",
        return_value=_mock_files_resource(),
    ), patch(
        "cvextract.openai_utils.as_file"
    ) as mock_as_file:
        result = openai_utils.get_cached_resource_path("resource.json")

    assert result == cache_path
    mock_as_file.assert_not_called()


def test_get_cached_resource_path_writes_cache_from_resource(tmp_path):
    """get_cached_resource_path writes cache when resource exists."""
    resource_path = tmp_path / "resource.json"
    resource_path.write_text("data", encoding="utf-8")

    @contextmanager
    def fake_as_file(_resource):
        yield resource_path

    with patch(
        "cvextract.openai_utils.tempfile.gettempdir",
        return_value=str(tmp_path),
    ), patch(
        "cvextract.openai_utils.files",
        return_value=_mock_files_resource(),
    ), patch(
        "cvextract.openai_utils.as_file",
        fake_as_file,
    ):
        result = openai_utils.get_cached_resource_path("resource.json")

    cache_path = tmp_path / "cvextract" / "resource.json"
    assert result == cache_path
    assert cache_path.read_text(encoding="utf-8") == "data"


def test_get_cached_resource_path_returns_none_when_resource_missing(tmp_path):
    """get_cached_resource_path returns None when resource path is missing."""
    missing_path = tmp_path / "missing.json"

    @contextmanager
    def fake_as_file(_resource):
        yield missing_path

    with patch(
        "cvextract.openai_utils.tempfile.gettempdir",
        return_value=str(tmp_path),
    ), patch(
        "cvextract.openai_utils.files",
        return_value=_mock_files_resource(),
    ), patch(
        "cvextract.openai_utils.as_file",
        fake_as_file,
    ):
        result = openai_utils.get_cached_resource_path("resource.json")

    assert result is None


def test_get_cached_resource_path_returns_none_on_exception(tmp_path):
    """get_cached_resource_path returns None when resource lookup fails."""
    with patch(
        "cvextract.openai_utils.files",
        side_effect=RuntimeError("boom"),
    ):
        result = openai_utils.get_cached_resource_path("resource.json")

    assert result is None


def test_normalize_provider_maps_known_values():
    """normalize_provider should map Azure/OpenAI variants."""
    assert openai_utils.normalize_provider(None) == "openai"
    assert openai_utils.normalize_provider("OpenAI") == "openai"
    assert openai_utils.normalize_provider("azure") == "azure"
    assert openai_utils.normalize_provider("azure-openai") == "azure"
    assert openai_utils.normalize_provider("foundry") == "azure"


def test_get_openai_client_openai_uses_passed_key():
    """get_openai_client should build OpenAI client with explicit key."""

    class DummyClient:
        def __init__(self, api_key):
            self.api_key = api_key

    client = openai_utils.get_openai_client(
        "openai", api_key="test-key", openai_cls=DummyClient
    )
    assert isinstance(client, DummyClient)
    assert client.api_key == "test-key"


def test_get_openai_client_azure_uses_passed_settings():
    """get_openai_client should build Azure client with explicit settings."""

    class DummyAzureClient:
        def __init__(self, api_key, azure_endpoint, api_version):
            self.api_key = api_key
            self.azure_endpoint = azure_endpoint
            self.api_version = api_version

    client = openai_utils.get_openai_client(
        "azure",
        api_key="azure-key",
        azure_endpoint="https://example.openai.azure.com",
        azure_api_version="2024-02-01",
        azure_openai_cls=DummyAzureClient,
    )
    assert isinstance(client, DummyAzureClient)
    assert client.api_key == "azure-key"
    assert client.azure_endpoint == "https://example.openai.azure.com"
    assert client.api_version == "2024-02-01"


def test_get_openai_client_azure_missing_settings_returns_none():
    """get_openai_client should return None when Azure settings are incomplete."""

    class DummyAzureClient:
        def __init__(self, api_key, azure_endpoint, api_version):
            self.api_key = api_key
            self.azure_endpoint = azure_endpoint
            self.api_version = api_version

    client = openai_utils.get_openai_client(
        "azure", api_key="azure-key", azure_openai_cls=DummyAzureClient
    )
    assert client is None
