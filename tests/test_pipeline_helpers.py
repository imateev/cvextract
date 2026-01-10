"""Tests for pipeline helper functions."""

import json
from pathlib import Path

import cvextract.pipeline_helpers as p
from cvextract.cli_config import ExtractStage, RenderStage, UserConfig
from cvextract.shared import (
    StepName,
    StepStatus,
    UnitOfWork,
    get_status_icons,
)
from cvextract.verifiers import get_verifier


def _make_work(tmp_path, data):
    path = tmp_path / "data.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    work = UnitOfWork(config=UserConfig(target_dir=tmp_path), initial_input=path)
    work.set_step_paths(StepName.Extract, input_path=path, output_path=path)
    work.current_step = StepName.Extract
    work.ensure_step_status(StepName.Extract)
    return work


def test_extract_single_success(monkeypatch, tmp_path: Path):
    """Test successful extraction and verification."""
    docx = tmp_path / "test.docx"
    output = tmp_path / "test.json"
    docx.write_text("docx")

    def fake_data():
        return {
            "identity": {
                "title": "T",
                "full_name": "F N",
                "first_name": "F",
                "last_name": "N",
            },
            "sidebar": {
                "languages": ["Python"],
                "tools": ["x"],
                "industries": ["x"],
                "spoken_languages": ["EN"],
                "academic_background": ["x"],
            },
            "experiences": [{"heading": "h", "description": "d", "bullets": ["b"]}],
        }

    def fake_process_with_data(work, extractor=None):
        output_path = work.get_step_output(StepName.Extract)
        output_path.write_text(json.dumps(fake_data()), encoding="utf-8")
        return work

    monkeypatch.setattr(p, "extract_cv_data", fake_process_with_data)

    work = UnitOfWork(
        config=UserConfig(target_dir=tmp_path, extract=ExtractStage(source=docx)),
        initial_input=docx,
    )
    work.set_step_paths(StepName.Extract, input_path=docx, output_path=output)
    result = p.extract_single(work)
    extract_status = result.step_states[StepName.Extract]
    assert extract_status.errors == []
    assert len(extract_status.warnings) == 0


def test_extract_single_exception(monkeypatch, tmp_path: Path):
    """Test extraction with exception."""
    docx = tmp_path / "test.docx"
    output = tmp_path / "test.json"
    docx.write_text("docx")

    def fake_process(_work, extractor=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(p, "extract_cv_data", fake_process)

    work = UnitOfWork(
        config=UserConfig(target_dir=tmp_path, extract=ExtractStage(source=docx)),
        initial_input=docx,
    )
    work.set_step_paths(StepName.Extract, input_path=docx, output_path=output)
    result = p.extract_single(work)
    extract_status = result.step_states[StepName.Extract]
    assert len(extract_status.errors) == 1
    assert "exception: RuntimeError" in extract_status.errors[0]
    assert extract_status.warnings == []


def test_extract_single_does_not_create_verify_status(monkeypatch, tmp_path: Path):
    """extract_single should not create verification status entries."""
    docx = tmp_path / "test.docx"
    output = tmp_path / "test.json"
    docx.write_text("docx")

    def fake_process(work, extractor=None):
        output_path = work.get_step_output(StepName.Extract)
        output_path.write_text('{"identity": {}}', encoding="utf-8")
        return work

    monkeypatch.setattr(p, "extract_cv_data", fake_process)

    work = UnitOfWork(
        config=UserConfig(
            target_dir=tmp_path,
            extract=ExtractStage(source=docx),
        ),
        initial_input=docx,
    )
    work.set_step_paths(StepName.Extract, input_path=docx, output_path=output)
    result = p.extract_single(work)
    extract_status = result.step_states[StepName.Extract]
    assert extract_status.errors == []
    assert extract_status.warnings == []
    assert StepName.VerifyExtract not in result.step_states


def test_render_exception_adds_warning(monkeypatch, tmp_path: Path):
    """Test rendering exceptions surface as warnings."""
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
    work = UnitOfWork(config=config, initial_input=json_file)
    work.set_step_paths(StepName.Render, input_path=json_file, output_path=json_file)
    result = p.render(work)
    render_status = result.step_states[StepName.Render]
    assert render_status.errors == []
    assert len(render_status.warnings) == 1
    assert "render: ValueError" in render_status.warnings[0]
    assert StepName.VerifyRender not in result.step_states


def test_get_status_icons_extract_success_no_warnings():
    """Test icons for successful extraction without warnings."""
    work = UnitOfWork(config=UserConfig(target_dir=Path(".")))
    work.step_states[StepName.Extract] = StepStatus(step=StepName.Extract)
    icons = get_status_icons(work)
    assert icons[StepName.Extract] == "🟢"
    assert icons[StepName.Render] == "➖"
    assert icons[StepName.VerifyRender] == "➖"


def test_get_status_icons_extract_success_with_warnings():
    """Test icons for successful extraction with warnings."""
    work = UnitOfWork(config=UserConfig(target_dir=Path(".")))
    work.step_states[StepName.Extract] = StepStatus(
        step=StepName.Extract,
        warnings=["warning"],
    )
    icons = get_status_icons(work)
    assert icons[StepName.Extract] == "❎"
    assert icons[StepName.Render] == "➖"
    assert icons[StepName.VerifyRender] == "➖"


def test_get_status_icons_extract_failed():
    """Test icons for failed extraction."""
    work = UnitOfWork(config=UserConfig(target_dir=Path(".")))
    work.step_states[StepName.Extract] = StepStatus(
        step=StepName.Extract,
        errors=["error"],
    )
    icons = get_status_icons(work)
    assert icons[StepName.Extract] == "❌"
    assert icons[StepName.Render] == "➖"
    assert icons[StepName.VerifyRender] == "➖"


def test_get_status_icons_apply_success():
    """Test icons for successful apply."""
    work = UnitOfWork(config=UserConfig(target_dir=Path(".")))
    work.step_states[StepName.Extract] = StepStatus(step=StepName.Extract)
    work.step_states[StepName.Render] = StepStatus(step=StepName.Render)
    work.step_states[StepName.VerifyRender] = StepStatus(
        step=StepName.VerifyRender
    )
    icons = get_status_icons(work)
    assert icons[StepName.Extract] == "🟢"
    assert icons[StepName.Render] == "✅"
    assert icons[StepName.VerifyRender] == "✅"


def test_get_status_icons_apply_failed():
    """Test icons for failed apply."""
    work = UnitOfWork(config=UserConfig(target_dir=Path(".")))
    work.step_states[StepName.Extract] = StepStatus(step=StepName.Extract)
    work.step_states[StepName.Render] = StepStatus(
        step=StepName.Render,
        errors=["render failed"],
    )
    work.step_states[StepName.VerifyRender] = StepStatus(
        step=StepName.VerifyRender,
        errors=["compare failed"],
    )
    icons = get_status_icons(work)
    assert icons[StepName.Extract] == "🟢"
    assert icons[StepName.Render] == "❌"
    assert icons[StepName.VerifyRender] == "❌"


def test_categorize_result_extract_failed():
    """Test categorization when extraction fails."""
    full, part, fail = p.categorize_result(
        extract_ok=False, has_warns=False, apply_ok=None
    )
    assert full == 0
    assert part == 0
    assert fail == 1


def test_categorize_result_extract_success_no_warnings_no_apply():
    """Test categorization for successful extraction without apply."""
    full, part, fail = p.categorize_result(
        extract_ok=True, has_warns=False, apply_ok=None
    )
    assert full == 1
    assert part == 0
    assert fail == 0


def test_categorize_result_extract_success_with_warnings():
    """Test categorization for extraction with warnings."""
    full, part, fail = p.categorize_result(
        extract_ok=True, has_warns=True, apply_ok=None
    )
    assert full == 0
    assert part == 1
    assert fail == 0


def test_categorize_result_apply_failed():
    """Test categorization when apply fails."""
    full, part, fail = p.categorize_result(
        extract_ok=True, has_warns=False, apply_ok=False
    )
    assert full == 0
    assert part == 1
    assert fail == 0


def test_categorize_result_fully_successful():
    """Test categorization for fully successful run."""
    full, part, fail = p.categorize_result(
        extract_ok=True, has_warns=False, apply_ok=True
    )
    assert full == 1
    assert part == 0
    assert fail == 0


def test_verify_extracted_data_missing_identity(tmp_path):
    """Test verification with missing identity fields."""
    data = {
        "identity": {"title": "", "full_name": "", "first_name": "", "last_name": ""},
        "sidebar": {"languages": ["EN"]},
        "experiences": [{"heading": "h", "description": "d"}],
    }
    verifier = get_verifier("default-extract-verifier")
    work = _make_work(tmp_path, data)
    result = verifier.verify(work)
    status = result.step_states[StepName.Extract]
    assert "identity" in status.errors


def test_verify_extracted_data_empty_sidebar(tmp_path):
    """Test verification with empty sidebar."""
    data = {
        "identity": {
            "title": "T",
            "full_name": "F N",
            "first_name": "F",
            "last_name": "N",
        },
        "sidebar": {},
        "experiences": [{"heading": "h", "description": "d"}],
    }
    verifier = get_verifier("default-extract-verifier")
    work = _make_work(tmp_path, data)
    result = verifier.verify(work)
    status = result.step_states[StepName.Extract]
    assert "sidebar" in status.errors


def test_verify_extracted_data_no_experiences(tmp_path):
    """Test verification with no experiences."""
    data = {
        "identity": {
            "title": "T",
            "full_name": "F N",
            "first_name": "F",
            "last_name": "N",
        },
        "sidebar": {"languages": ["EN"]},
        "experiences": [],
    }
    verifier = get_verifier("default-extract-verifier")
    work = _make_work(tmp_path, data)
    result = verifier.verify(work)
    status = result.step_states[StepName.Extract]
    assert "experiences_empty" in status.errors


def test_verify_extracted_data_invalid_environment(tmp_path):
    """Test verification with invalid environment format."""
    data = {
        "identity": {
            "title": "T",
            "full_name": "F N",
            "first_name": "F",
            "last_name": "N",
        },
        "sidebar": {
            "languages": ["EN"],
            "tools": ["x"],
            "industries": ["x"],
            "spoken_languages": ["EN"],
            "academic_background": ["x"],
        },
        "experiences": [
            {
                "heading": "h",
                "description": "d",
                "bullets": ["b"],
                "environment": "not-a-list",
            }
        ],
    }
    verifier = get_verifier("default-extract-verifier")
    work = _make_work(tmp_path, data)
    result = verifier.verify(work)
    status = result.step_states[StepName.Extract]
    assert any("invalid environment format" in w for w in status.warnings)
