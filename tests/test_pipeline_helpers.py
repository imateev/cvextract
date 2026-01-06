"""Tests for pipeline helper functions."""

from pathlib import Path
import cvextract.pipeline_helpers as p
from cvextract.cli_config import UserConfig, ExtractStage, RenderStage
from cvextract.shared import StepName, StepStatus, UnitOfWork, get_status_icons
from cvextract.verifiers import get_verifier
from cvextract.verifiers.comparison_verifier import RoundtripVerifier
from cvextract.shared import VerificationResult


def test_extract_single_success(monkeypatch, tmp_path: Path):
    """Test successful extraction and verification."""
    docx = tmp_path / "test.docx"
    output = tmp_path / "test.json"
    docx.write_text("docx")
    
    def fake_process(_path, out, extractor=None):
        out.write_text("{}", encoding="utf-8")
        return {
            "identity": {"title": "T", "full_name": "F N", "first_name": "F", "last_name": "N"},
            "sidebar": {"languages": ["Python"], "tools": ["x"], "industries": ["x"], 
                       "spoken_languages": ["EN"], "academic_background": ["x"]},
            "experiences": [{"heading": "h", "description": "d", "bullets": ["b"]}],
        }
    
    monkeypatch.setattr(p, "process_single_docx", fake_process)
    
    work = UnitOfWork(
        config=UserConfig(target_dir=tmp_path, extract=ExtractStage(source=docx)),
        input=docx,
        output=output,
    )
    result = p.extract_single(work)
    extract_status = result.step_statuses[StepName.Extract]
    assert extract_status.errors == []
    assert len(extract_status.warnings) == 0


def test_extract_single_with_warnings(monkeypatch, tmp_path: Path):
    """Test extraction with validation warnings."""
    docx = tmp_path / "test.docx"
    output = tmp_path / "test.json"
    docx.write_text("docx")
    
    def fake_process(_path, out, extractor=None):
        out.write_text("{}", encoding="utf-8")
        return {
            "identity": {"title": "T", "full_name": "F N", "first_name": "F", "last_name": "N"},
            "sidebar": {"languages": ["Python"], "tools": [], "industries": [], 
                       "spoken_languages": [], "academic_background": []},
            "experiences": [{"heading": "h", "description": "d", "bullets": ["b"]}],
        }
    
    monkeypatch.setattr(p, "process_single_docx", fake_process)
    
    work = UnitOfWork(
        config=UserConfig(target_dir=tmp_path, extract=ExtractStage(source=docx)),
        input=docx,
        output=output,
    )
    result = p.extract_single(work)
    extract_status = result.step_statuses[StepName.Extract]
    assert extract_status.errors == []
    assert len(extract_status.warnings) > 0
    assert any("missing sidebar" in w for w in extract_status.warnings)


def test_extract_single_exception(monkeypatch, tmp_path: Path):
    """Test extraction with exception."""
    docx = tmp_path / "test.docx"
    output = tmp_path / "test.json"
    docx.write_text("docx")
    
    def fake_process(_path, out, extractor=None):
        raise RuntimeError("boom")
    
    monkeypatch.setattr(p, "process_single_docx", fake_process)
    
    work = UnitOfWork(
        config=UserConfig(target_dir=tmp_path, extract=ExtractStage(source=docx)),
        input=docx,
        output=output,
    )
    result = p.extract_single(work)
    extract_status = result.step_statuses[StepName.Extract]
    assert len(extract_status.errors) == 1
    assert "exception: RuntimeError" in extract_status.errors[0]
    assert extract_status.warnings == []


def test_render_and_verify_success(monkeypatch, tmp_path: Path):
    """Test successful render with roundtrip verification."""
    json_file = tmp_path / "test.json"
    json_file.write_text('{"a": 1}', encoding="utf-8")
    template = tmp_path / "template.docx"
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    def fake_render(work):
        return work

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

    config = UserConfig(
        target_dir=out_dir,
        render=RenderStage(template=template, data=json_file),
    )
    work = UnitOfWork(config=config, input=json_file, output=json_file, initial_input=json_file)
    ok, errs, warns, compare_ok = p.render_and_verify(work)
    assert ok is True
    assert errs == []
    assert warns == []
    assert compare_ok is True


def test_render_and_verify_exception(monkeypatch, tmp_path: Path):
    """Test rendering exceptions surface as errors."""
    json_file = tmp_path / "test.json"
    json_file.write_text('{"a": 1}', encoding="utf-8")
    template = tmp_path / "template.docx"
    out_dir = tmp_path / "out"

    def fake_render(_work):
        raise ValueError("render failed")

    monkeypatch.setattr(p, "render_cv_data", fake_render)

    config = UserConfig(
        target_dir=out_dir,
        render=RenderStage(template=template, data=json_file),
    )
    work = UnitOfWork(config=config, input=json_file, output=json_file, initial_input=json_file)
    ok, errs, warns, compare_ok = p.render_and_verify(work)
    assert ok is False
    assert len(errs) == 1
    assert "render: ValueError" in errs[0]
    assert warns == []
    assert compare_ok is None


def test_render_and_verify_diff(monkeypatch, tmp_path: Path):
    """Test roundtrip mismatch surfaces as error."""
    json_file = tmp_path / "test.json"
    json_file.write_text('{"a": 1}', encoding="utf-8")
    template = tmp_path / "template.docx"
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    def fake_render(work):
        return work

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

    config = UserConfig(
        target_dir=out_dir,
        render=RenderStage(template=template, data=json_file),
    )
    work = UnitOfWork(config=config, input=json_file, output=json_file, initial_input=json_file)
    ok, errs, warns, compare_ok = p.render_and_verify(work)
    assert ok is False
    assert "value mismatch" in errs[0]
    assert warns == []
    assert compare_ok is False


def test_get_status_icons_extract_success_no_warnings():
    """Test icons for successful extraction without warnings."""
    work = UnitOfWork(
        config=UserConfig(target_dir=Path(".")),
        input=Path("input.json"),
        output=Path("output.json"),
    )
    work.step_statuses[StepName.Extract] = StepStatus(step=StepName.Extract)
    icons = get_status_icons(work)
    assert icons[StepName.Extract] == "🟢"
    assert icons[StepName.Render] == "➖"
    assert icons[StepName.Verify] == "➖"


def test_get_status_icons_extract_success_with_warnings():
    """Test icons for successful extraction with warnings."""
    work = UnitOfWork(
        config=UserConfig(target_dir=Path(".")),
        input=Path("input.json"),
        output=Path("output.json"),
    )
    work.step_statuses[StepName.Extract] = StepStatus(
        step=StepName.Extract,
        warnings=["warning"],
    )
    icons = get_status_icons(work)
    assert icons[StepName.Extract] == "⚠️ "
    assert icons[StepName.Render] == "➖"
    assert icons[StepName.Verify] == "➖"


def test_get_status_icons_extract_failed():
    """Test icons for failed extraction."""
    work = UnitOfWork(
        config=UserConfig(target_dir=Path(".")),
        input=Path("input.json"),
        output=Path("output.json"),
    )
    work.step_statuses[StepName.Extract] = StepStatus(
        step=StepName.Extract,
        errors=["error"],
    )
    icons = get_status_icons(work)
    assert icons[StepName.Extract] == "❌"
    assert icons[StepName.Render] == "➖"
    assert icons[StepName.Verify] == "➖"


def test_get_status_icons_apply_success():
    """Test icons for successful apply."""
    work = UnitOfWork(
        config=UserConfig(target_dir=Path(".")),
        input=Path("input.json"),
        output=Path("output.json"),
    )
    work.step_statuses[StepName.Extract] = StepStatus(step=StepName.Extract)
    work.step_statuses[StepName.Render] = StepStatus(step=StepName.Render)
    work.step_statuses[StepName.Verify] = StepStatus(step=StepName.Verify)
    icons = get_status_icons(work)
    assert icons[StepName.Extract] == "🟢"
    assert icons[StepName.Render] == "✅"
    assert icons[StepName.Verify] == "✅"


def test_get_status_icons_apply_failed():
    """Test icons for failed apply."""
    work = UnitOfWork(
        config=UserConfig(target_dir=Path(".")),
        input=Path("input.json"),
        output=Path("output.json"),
    )
    work.step_statuses[StepName.Extract] = StepStatus(step=StepName.Extract)
    work.step_statuses[StepName.Render] = StepStatus(
        step=StepName.Render,
        errors=["render failed"],
    )
    work.step_statuses[StepName.Verify] = StepStatus(
        step=StepName.Verify,
        errors=["compare failed"],
    )
    icons = get_status_icons(work)
    assert icons[StepName.Extract] == "🟢"
    assert icons[StepName.Render] == "❌"
    assert icons[StepName.Verify] == "⚠️ "


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
