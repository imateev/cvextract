"""Tests for pipeline helper functions."""

import pytest
from pathlib import Path
from unittest.mock import Mock
import cvextract.pipeline as p


def test_extract_single_success(monkeypatch, tmp_path: Path):
    """Test successful extraction and verification."""
    docx = tmp_path / "test.docx"
    out_json = tmp_path / "test.json"
    
    def fake_process(_path, out):
        out.write_text("{}", encoding="utf-8")
        return {
            "identity": {"title": "T", "full_name": "F N", "first_name": "F", "last_name": "N"},
            "sidebar": {"languages": ["Python"], "tools": ["x"], "industries": ["x"], 
                       "spoken_languages": ["EN"], "academic_background": ["x"]},
            "experiences": [{"heading": "h", "description": "d", "bullets": ["b"]}],
        }
    
    monkeypatch.setattr(p, "process_single_docx", fake_process)
    
    ok, errs, warns = p._extract_single(docx, out_json, debug=False)
    assert ok is True
    assert errs == []
    assert len(warns) == 0


def test_extract_single_with_warnings(monkeypatch, tmp_path: Path):
    """Test extraction with validation warnings."""
    docx = tmp_path / "test.docx"
    out_json = tmp_path / "test.json"
    
    def fake_process(_path, out):
        out.write_text("{}", encoding="utf-8")
        return {
            "identity": {"title": "T", "full_name": "F N", "first_name": "F", "last_name": "N"},
            "sidebar": {"languages": ["Python"], "tools": [], "industries": [], 
                       "spoken_languages": [], "academic_background": []},
            "experiences": [{"heading": "h", "description": "d", "bullets": ["b"]}],
        }
    
    monkeypatch.setattr(p, "process_single_docx", fake_process)
    
    ok, errs, warns = p._extract_single(docx, out_json, debug=False)
    assert ok is True
    assert errs == []
    assert len(warns) > 0
    assert any("missing sidebar" in w for w in warns)


def test_extract_single_exception(monkeypatch, tmp_path: Path):
    """Test extraction with exception."""
    docx = tmp_path / "test.docx"
    out_json = tmp_path / "test.json"
    
    def fake_process(_path, out):
        raise RuntimeError("boom")
    
    monkeypatch.setattr(p, "process_single_docx", fake_process)
    
    ok, errs, warns = p._extract_single(docx, out_json, debug=False)
    assert ok is False
    assert len(errs) == 1
    assert "exception: RuntimeError" in errs[0]
    assert warns == []


def test_render_single_success(monkeypatch, tmp_path: Path):
    """Test successful rendering."""
    json_file = tmp_path / "test.json"
    json_file.write_text("{}", encoding="utf-8")
    template = tmp_path / "template.docx"
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    
    def fake_render(_json, _template, _out):
        pass
    
    monkeypatch.setattr(p, "render_from_json", fake_render)
    
    ok, errs = p._render_single(json_file, template, out_dir, debug=False)
    assert ok is True
    assert errs == []


def test_render_single_exception(monkeypatch, tmp_path: Path):
    """Test rendering with exception."""
    json_file = tmp_path / "test.json"
    template = tmp_path / "template.docx"
    out_dir = tmp_path / "out"
    
    def fake_render(_json, _template, _out):
        raise ValueError("render failed")
    
    monkeypatch.setattr(p, "render_from_json", fake_render)
    
    ok, errs = p._render_single(json_file, template, out_dir, debug=False)
    assert ok is False
    assert len(errs) == 1
    assert "render: ValueError" in errs[0]


def test_get_status_icons_extract_success_no_warnings():
    """Test icons for successful extraction without warnings."""
    x_icon, a_icon = p._get_status_icons(extract_ok=True, has_warns=False, apply_ok=None)
    assert x_icon == "🟢"
    assert a_icon == "➖"


def test_get_status_icons_extract_success_with_warnings():
    """Test icons for successful extraction with warnings."""
    x_icon, a_icon = p._get_status_icons(extract_ok=True, has_warns=True, apply_ok=None)
    assert x_icon == "⚠️ "
    assert a_icon == "➖"


def test_get_status_icons_extract_failed():
    """Test icons for failed extraction."""
    x_icon, a_icon = p._get_status_icons(extract_ok=False, has_warns=False, apply_ok=None)
    assert x_icon == "❌"
    assert a_icon == "➖"


def test_get_status_icons_apply_success():
    """Test icons for successful apply."""
    x_icon, a_icon = p._get_status_icons(extract_ok=True, has_warns=False, apply_ok=True)
    assert x_icon == "🟢"
    assert a_icon == "✅"


def test_get_status_icons_apply_failed():
    """Test icons for failed apply."""
    x_icon, a_icon = p._get_status_icons(extract_ok=True, has_warns=False, apply_ok=False)
    assert x_icon == "🟢"
    assert a_icon == "❌"


def test_categorize_result_extract_failed():
    """Test categorization when extraction fails."""
    full, part, fail = p._categorize_result(extract_ok=False, has_warns=False, apply_ok=None)
    assert full == 0
    assert part == 0
    assert fail == 1


def test_categorize_result_extract_success_no_warnings_no_apply():
    """Test categorization for successful extraction without apply."""
    full, part, fail = p._categorize_result(extract_ok=True, has_warns=False, apply_ok=None)
    assert full == 1
    assert part == 0
    assert fail == 0


def test_categorize_result_extract_success_with_warnings():
    """Test categorization for extraction with warnings."""
    full, part, fail = p._categorize_result(extract_ok=True, has_warns=True, apply_ok=None)
    assert full == 0
    assert part == 1
    assert fail == 0


def test_categorize_result_apply_failed():
    """Test categorization when apply fails."""
    full, part, fail = p._categorize_result(extract_ok=True, has_warns=False, apply_ok=False)
    assert full == 0
    assert part == 1
    assert fail == 0


def test_categorize_result_fully_successful():
    """Test categorization for fully successful run."""
    full, part, fail = p._categorize_result(extract_ok=True, has_warns=False, apply_ok=True)
    assert full == 1
    assert part == 0
    assert fail == 0


def test_verify_extracted_data_missing_identity():
    """Test verification with missing identity fields."""
    data = {
        "identity": {"title": "", "full_name": "", "first_name": "", "last_name": ""},
        "sidebar": {"languages": ["EN"]},
        "experiences": [{"heading": "h", "description": "d"}],
    }
    result = p.verify_extracted_data(data)
    assert result.ok is False
    assert "identity" in result.errors


def test_verify_extracted_data_empty_sidebar():
    """Test verification with empty sidebar."""
    data = {
        "identity": {"title": "T", "full_name": "F N", "first_name": "F", "last_name": "N"},
        "sidebar": {},
        "experiences": [{"heading": "h", "description": "d"}],
    }
    result = p.verify_extracted_data(data)
    assert result.ok is False
    assert "sidebar" in result.errors


def test_verify_extracted_data_no_experiences():
    """Test verification with no experiences."""
    data = {
        "identity": {"title": "T", "full_name": "F N", "first_name": "F", "last_name": "N"},
        "sidebar": {"languages": ["EN"]},
        "experiences": [],
    }
    result = p.verify_extracted_data(data)
    assert result.ok is False
    assert "experiences_empty" in result.errors


def test_verify_extracted_data_invalid_environment():
    """Test verification with invalid environment format."""
    data = {
        "identity": {"title": "T", "full_name": "F N", "first_name": "F", "last_name": "N"},
        "sidebar": {"languages": ["EN"], "tools": ["x"], "industries": ["x"], 
                   "spoken_languages": ["EN"], "academic_background": ["x"]},
        "experiences": [{"heading": "h", "description": "d", "bullets": ["b"], "environment": "not-a-list"}],
    }
    result = p.verify_extracted_data(data)
    assert result.ok is True
    assert any("invalid environment format" in w for w in result.warnings)
