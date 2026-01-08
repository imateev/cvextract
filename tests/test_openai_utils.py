"""Tests for shared OpenAI helper utilities."""

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import cvextract.adjusters.openai_utils as openai_utils


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
        "cvextract.adjusters.openai_utils.tempfile.gettempdir",
        return_value=str(tmp_path),
    ), patch(
        "cvextract.adjusters.openai_utils.files",
        return_value=_mock_files_resource(),
    ), patch(
        "cvextract.adjusters.openai_utils.as_file"
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
        "cvextract.adjusters.openai_utils.tempfile.gettempdir",
        return_value=str(tmp_path),
    ), patch(
        "cvextract.adjusters.openai_utils.files",
        return_value=_mock_files_resource(),
    ), patch(
        "cvextract.adjusters.openai_utils.as_file",
        fake_as_file,
    ):
        result = openai_utils.get_cached_resource_path("resource.json")

    cache_path = (tmp_path / "cvextract" / "resource.json")
    assert result == cache_path
    assert cache_path.read_text(encoding="utf-8") == "data"


def test_get_cached_resource_path_returns_none_when_resource_missing(tmp_path):
    """get_cached_resource_path returns None when resource path is missing."""
    missing_path = tmp_path / "missing.json"

    @contextmanager
    def fake_as_file(_resource):
        yield missing_path

    with patch(
        "cvextract.adjusters.openai_utils.tempfile.gettempdir",
        return_value=str(tmp_path),
    ), patch(
        "cvextract.adjusters.openai_utils.files",
        return_value=_mock_files_resource(),
    ), patch(
        "cvextract.adjusters.openai_utils.as_file",
        fake_as_file,
    ):
        result = openai_utils.get_cached_resource_path("resource.json")

    assert result is None


def test_get_cached_resource_path_returns_none_on_exception(tmp_path):
    """get_cached_resource_path returns None when resource lookup fails."""
    with patch(
        "cvextract.adjusters.openai_utils.files",
        side_effect=RuntimeError("boom"),
    ):
        result = openai_utils.get_cached_resource_path("resource.json")

    assert result is None
