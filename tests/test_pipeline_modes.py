import pytest

from pathlib import Path
import cvextract.pipeline as p
from cvextract.shared import VerificationResult

def test_infer_source_root_single_file(tmp_path: Path):
    f = tmp_path / "a.docx"
    f.write_text("x")
    assert p.infer_source_root([f]) == tmp_path

def test_infer_source_root_multiple_files_common_parent(tmp_path: Path):
    d1 = tmp_path / "x"
    d2 = tmp_path / "y"
    d1.mkdir()
    d2.mkdir()
    f1 = d1 / "a.docx"
    f2 = d2 / "b.docx"
    f1.write_text("x")
    f2.write_text("y")

    root = p.infer_source_root([f1, f2])
    assert root == tmp_path

def test_run_extract_mode_success(monkeypatch, tmp_path: Path):
    # fake input docx
    docx = tmp_path / "a.docx"
    docx.write_text("x")

    def fake_process_single_docx(_docx_path, out):
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("{}", encoding="utf-8")
        return {
            "identity": {"title": "T", "full_name": "F N", "first_name": "F", "last_name": "N"},
            "sidebar": {
                "languages": ["Python"],
                "tools": ["x"],
                "industries": ["x"],
                "spoken_languages": ["English"],
                "academic_background": ["x"],
            },
            "overview": {},
            "experiences": [{"heading": "h", "description": "d", "bullets": ["b"]}],
        }

    monkeypatch.setattr(p, "process_single_docx", fake_process_single_docx)

    rc = p.run_extract_mode([docx], target_dir=tmp_path / "target", strict=False, debug=False)
    assert rc == 0

def test_run_extract_apply_mode_render_failure(monkeypatch, tmp_path: Path):
    docx = tmp_path / "a.docx"
    docx.write_text("x")

    def fake_process_single_docx(_docx_path, out):
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("{}", encoding="utf-8")
        return {
            "identity": {"title": "T", "full_name": "F N", "first_name": "F", "last_name": "N"},
            "sidebar": {
                "languages": ["Python"],
                "tools": ["x"],
                "industries": ["x"],
                "spoken_languages": ["English"],
                "academic_background": ["x"],
            },
            "overview": {},
            "experiences": [{"heading": "h", "description": "d", "bullets": ["b"]}],
        }

    def fake_render(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(p, "process_single_docx", fake_process_single_docx)
    monkeypatch.setattr(p, "render_from_json", fake_render)

    rc = p.run_extract_apply_mode([docx], template_path=tmp_path / "tpl.docx", target_dir=tmp_path / "target", strict=False, debug=False)
    assert rc != 0
