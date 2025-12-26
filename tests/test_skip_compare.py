import os
from pathlib import Path
import cvextract.pipeline as p


def test_render_and_verify_skips_compare(monkeypatch, tmp_path: Path):
    # Arrange: fake render returns a path; skipping compare means we won't call process_single_docx
    def fake_render(_json, _template, out_dir):
        return out_dir / "doc_NEW.docx"

    monkeypatch.setattr(p, "render_from_json", fake_render)

    # Set skip compare env and call helper
    monkeypatch.setenv("CVEXTRACT_SKIP_COMPARE", "1")

    json_file = tmp_path / "data.json"
    json_file.write_text("{}", encoding="utf-8")
    template = tmp_path / "template.docx"
    template.write_text("")
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    ok, errs, warns, compare_ok = p._render_and_verify(json_file, template, out_dir, debug=False, skip_compare=True)

    assert ok is True
    assert errs == []
    assert warns == []
    assert compare_ok is None
