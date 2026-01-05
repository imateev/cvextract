"""Tests for pipeline helper functions."""

from pathlib import Path
import cvextract.pipeline_helpers as p
from cvextract.run_input import RunInput
from cvextract.verifiers import get_verifier
from cvextract.verifiers.comparison_verifier import RoundtripVerifier
from cvextract.shared import VerificationResult


def test_extract_single_success(monkeypatch, tmp_path: Path):
    """Test successful extraction and verification."""
    docx = tmp_path / "test.docx"
    out_json = tmp_path / "test.json"
    
    def fake_process(_path, out, extractor=None):
        out.write_text("{}", encoding="utf-8")
        return {
            "identity": {"title": "T", "full_name": "F N", "first_name": "F", "last_name": "N"},
            "sidebar": {"languages": ["Python"], "tools": ["x"], "industries": ["x"], 
                       "spoken_languages": ["EN"], "academic_background": ["x"]},
            "experiences": [{"heading": "h", "description": "d", "bullets": ["b"]}],
        }
    
    monkeypatch.setattr(p, "process_single_docx", fake_process)
    
    ok, errs, warns, run_input = p.extract_single(docx, out_json, debug=False)
    assert ok is True
    assert errs == []
    assert len(warns) == 0
    # Verify RunInput is returned with extracted_json_path set
    assert isinstance(run_input, RunInput)
    assert run_input.extracted_json_path == out_json


def test_extract_single_with_warnings(monkeypatch, tmp_path: Path):
    """Test extraction with validation warnings."""
    docx = tmp_path / "test.docx"
    out_json = tmp_path / "test.json"
    
    def fake_process(_path, out, extractor=None):
        out.write_text("{}", encoding="utf-8")
        return {
            "identity": {"title": "T", "full_name": "F N", "first_name": "F", "last_name": "N"},
            "sidebar": {"languages": ["Python"], "tools": [], "industries": [], 
                       "spoken_languages": [], "academic_background": []},
            "experiences": [{"heading": "h", "description": "d", "bullets": ["b"]}],
        }
    
    monkeypatch.setattr(p, "process_single_docx", fake_process)
    
    ok, errs, warns, run_input = p.extract_single(docx, out_json, debug=False)
    assert ok is True
    assert errs == []
    assert len(warns) > 0
    assert any("missing sidebar" in w for w in warns)
    # Verify RunInput is returned with extracted_json_path set
    assert isinstance(run_input, RunInput)
    assert run_input.extracted_json_path == out_json


def test_extract_single_exception(monkeypatch, tmp_path: Path):
    """Test extraction with exception."""
    docx = tmp_path / "test.docx"
    out_json = tmp_path / "test.json"
    
    def fake_process(_path, out, extractor=None):
        raise RuntimeError("boom")
    
    monkeypatch.setattr(p, "process_single_docx", fake_process)
    
    ok, errs, warns, run_input = p.extract_single(docx, out_json, debug=False)
    assert ok is False
    assert len(errs) == 1
    assert "exception: RuntimeError" in errs[0]
    assert warns == []
    # Verify RunInput is returned even on error (but extracted_json_path is not set)
    assert isinstance(run_input, RunInput)
    assert run_input.extracted_json_path is None


def test_extract_single_with_run_input(monkeypatch, tmp_path: Path):
    """Test extraction when RunInput is passed instead of Path."""
    docx = tmp_path / "test.docx"
    out_json = tmp_path / "test.json"
    run_input = RunInput.from_path(docx)
    
    def fake_process(_path, out, extractor=None):
        out.write_text("{}", encoding="utf-8")
        return {
            "identity": {"title": "T", "full_name": "F N", "first_name": "F", "last_name": "N"},
            "sidebar": {"languages": ["Python"], "tools": ["x"], "industries": ["x"], 
                       "spoken_languages": ["EN"], "academic_background": ["x"]},
            "experiences": [{"heading": "h", "description": "d", "bullets": ["b"]}],
        }
    
    monkeypatch.setattr(p, "process_single_docx", fake_process)
    
    ok, errs, warns, updated_run_input = p.extract_single(run_input, out_json, debug=False)
    assert ok is True
    assert errs == []
    # Verify returned RunInput is different instance with extracted_json_path set
    assert updated_run_input is not run_input
    assert updated_run_input.file_path == docx
    assert updated_run_input.extracted_json_path == out_json


def test_render_and_verify_success(monkeypatch, tmp_path: Path):
    """Test successful render with roundtrip verification."""
    json_file = tmp_path / "test.json"
    json_file.write_text('{"a": 1}', encoding="utf-8")
    template = tmp_path / "template.docx"
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    out_docx = out_dir / "output.docx"
    
    # Create RunInput with extracted_json_path set
    run_input = RunInput(file_path=tmp_path / "source.docx", extracted_json_path=json_file)

    def fake_render(_cv_data, _template, output_path):
        return output_path

    def fake_process(_docx, out=None):
        if out:
            out.write_text('{"a": 1}', encoding="utf-8")
        return {"a": 1}

    def fake_compare(orig, target_data):
        return VerificationResult(ok=True, errors=[], warnings=[])

    # Mock the RoundtripVerifier instance method
    roundtrip_verifier = RoundtripVerifier()
    roundtrip_verifier.verify = fake_compare

    monkeypatch.setattr(p, "render_cv_data", fake_render)
    monkeypatch.setattr(p, "process_single_docx", fake_process)
    monkeypatch.setattr(p, "get_verifier", lambda x: roundtrip_verifier if x == "roundtrip-verifier" else None)

    ok, errs, warns, compare_ok, updated_run_input = p.render_and_verify(
        run_input, template, out_docx, debug=False
    )
    assert ok is True
    assert errs == []
    assert warns == []
    assert compare_ok is True
    # Verify RunInput is returned with rendered_docx_path set
    assert isinstance(updated_run_input, RunInput)
    assert updated_run_input.rendered_docx_path == out_docx
    assert updated_run_input.extracted_json_path == json_file


def test_render_and_verify_exception(monkeypatch, tmp_path: Path):
    """Test rendering exceptions surface as errors."""
    json_file = tmp_path / "test.json"
    json_file.write_text('{"a": 1}', encoding="utf-8")
    template = tmp_path / "template.docx"
    out_docx = tmp_path / "output.docx"
    
    # Create RunInput with extracted_json_path set
    run_input = RunInput(file_path=tmp_path / "source.docx", extracted_json_path=json_file)

    def fake_render(_cv_data, _template, _output_path):
        raise ValueError("render failed")

    monkeypatch.setattr(p, "render_cv_data", fake_render)

    ok, errs, warns, compare_ok, updated_run_input = p.render_and_verify(
        run_input, template, out_docx, debug=False
    )
    assert ok is False
    assert len(errs) == 1
    assert "render: ValueError" in errs[0]
    assert warns == []
    assert compare_ok is None
    # Verify original RunInput is returned on error
    assert updated_run_input is run_input
    assert updated_run_input.rendered_docx_path is None


def test_render_and_verify_diff(monkeypatch, tmp_path: Path):
    """Test roundtrip mismatch surfaces as error."""
    json_file = tmp_path / "test.json"
    json_file.write_text('{"a": 1}', encoding="utf-8")
    template = tmp_path / "template.docx"
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    out_docx = out_dir / "output.docx"
    
    # Create RunInput with extracted_json_path set
    run_input = RunInput(file_path=tmp_path / "source.docx", extracted_json_path=json_file)

    def fake_render(_cv_data, _template, output_path):
        return output_path

    def fake_process(_docx, out=None):
        return {"a": 2}

    def fake_compare(orig, target_data):
        return VerificationResult(ok=False, errors=["value mismatch"], warnings=[])

    # Mock the RoundtripVerifier instance method
    roundtrip_verifier = RoundtripVerifier()
    roundtrip_verifier.verify = fake_compare

    monkeypatch.setattr(p, "render_cv_data", fake_render)
    monkeypatch.setattr(p, "process_single_docx", fake_process)
    monkeypatch.setattr(p, "get_verifier", lambda x: roundtrip_verifier if x == "roundtrip-verifier" else None)

    ok, errs, warns, compare_ok, updated_run_input = p.render_and_verify(
        run_input, template, out_docx, debug=False
    )
    assert ok is False
    assert "value mismatch" in errs[0]
    assert warns == []
    assert compare_ok is False
    # Verify RunInput is returned with rendered_docx_path set even on comparison failure
    assert isinstance(updated_run_input, RunInput)
    assert updated_run_input.rendered_docx_path == out_docx


def test_render_and_verify_no_json_path(monkeypatch, tmp_path: Path):
    """Test render_and_verify with no JSON path in RunInput."""
    template = tmp_path / "template.docx"
    out_docx = tmp_path / "output.docx"
    
    # Create RunInput without any JSON paths
    run_input = RunInput.from_path(tmp_path / "source.docx")
    
    ok, errs, warns, compare_ok, updated_run_input = p.render_and_verify(
        run_input, template, out_docx, debug=False
    )
    assert ok is False
    assert "No JSON path available" in errs[0]
    assert compare_ok is None
    # Verify original RunInput is returned
    assert updated_run_input is run_input


def test_get_status_icons_extract_success_no_warnings():
    """Test icons for successful extraction without warnings."""
    x_icon, a_icon, c_icon = p.get_status_icons(extract_ok=True, has_warns=False, apply_ok=None, compare_ok=None)
    assert x_icon == "🟢"
    assert a_icon == "➖"
    assert c_icon == "➖"


def test_get_status_icons_extract_success_with_warnings():
    """Test icons for successful extraction with warnings."""
    x_icon, a_icon, c_icon = p.get_status_icons(extract_ok=True, has_warns=True, apply_ok=None, compare_ok=None)
    assert x_icon == "⚠️ "
    assert a_icon == "➖"
    assert c_icon == "➖"


def test_get_status_icons_extract_failed():
    """Test icons for failed extraction."""
    x_icon, a_icon, c_icon = p.get_status_icons(extract_ok=False, has_warns=False, apply_ok=None, compare_ok=None)
    assert x_icon == "❌"
    assert a_icon == "➖"
    assert c_icon == "➖"


def test_get_status_icons_apply_success():
    """Test icons for successful apply."""
    x_icon, a_icon, c_icon = p.get_status_icons(extract_ok=True, has_warns=False, apply_ok=True, compare_ok=True)
    assert x_icon == "🟢"
    assert a_icon == "✅"
    assert c_icon == "✅"


def test_get_status_icons_apply_failed():
    """Test icons for failed apply."""
    x_icon, a_icon, c_icon = p.get_status_icons(extract_ok=True, has_warns=False, apply_ok=False, compare_ok=False)
    assert x_icon == "🟢"
    assert a_icon == "❌"
    assert c_icon == "⚠️ "


def test_categorize_result_extract_failed():
    """Test categorization when extraction fails."""
    full, part, fail = p.categorize_result(extract_ok=False, has_warns=False, apply_ok=None)
    assert full == 0
    assert part == 0
    assert fail == 1


def test_categorize_result_extract_success_no_warnings_no_apply():
    """Test categorization for successful extraction without apply."""
    full, part, fail = p.categorize_result(extract_ok=True, has_warns=False, apply_ok=None)
    assert full == 1
    assert part == 0
    assert fail == 0


def test_categorize_result_extract_success_with_warnings():
    """Test categorization for extraction with warnings."""
    full, part, fail = p.categorize_result(extract_ok=True, has_warns=True, apply_ok=None)
    assert full == 0
    assert part == 1
    assert fail == 0


def test_categorize_result_apply_failed():
    """Test categorization when apply fails."""
    full, part, fail = p.categorize_result(extract_ok=True, has_warns=False, apply_ok=False)
    assert full == 0
    assert part == 1
    assert fail == 0


def test_categorize_result_fully_successful():
    """Test categorization for fully successful run."""
    full, part, fail = p.categorize_result(extract_ok=True, has_warns=False, apply_ok=True)
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
    verifier = get_verifier("private-internal-verifier")
    result = verifier.verify(data)
    assert result.ok is False
    assert "identity" in result.errors


def test_verify_extracted_data_empty_sidebar():
    """Test verification with empty sidebar."""
    data = {
        "identity": {"title": "T", "full_name": "F N", "first_name": "F", "last_name": "N"},
        "sidebar": {},
        "experiences": [{"heading": "h", "description": "d"}],
    }
    verifier = get_verifier("private-internal-verifier")
    result = verifier.verify(data)
    assert result.ok is False
    assert "sidebar" in result.errors


def test_verify_extracted_data_no_experiences():
    """Test verification with no experiences."""
    data = {
        "identity": {"title": "T", "full_name": "F N", "first_name": "F", "last_name": "N"},
        "sidebar": {"languages": ["EN"]},
        "experiences": [],
    }
    verifier = get_verifier("private-internal-verifier")
    result = verifier.verify(data)
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
    verifier = get_verifier("private-internal-verifier")
    result = verifier.verify(data)
    assert result.ok is True
    assert any("invalid environment format" in w for w in result.warnings)
