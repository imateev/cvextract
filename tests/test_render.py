import pytest

import json
from pathlib import Path
import cvextract.render as r

class DummyTpl:
    def __init__(self, _path: str):
        self.render_called_with = None
        self.saved_to = None

    def render(self, data, autoescape=False):
        self.render_called_with = (data, autoescape)

    def save(self, path: str):
        self.saved_to = path

def test_render_from_json_sanitizes_and_saves(monkeypatch, tmp_path: Path):
    json_path = tmp_path / "a.json"
    template_path = tmp_path / "tpl.docx"
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    json_path.write_text(json.dumps({"x": "A\u00A0B high\u00ADquality"}), encoding="utf-8")

    monkeypatch.setattr(r, "DocxTemplate", DummyTpl)

    out_docx = r.render_from_json(json_path, template_path, out_dir)
    assert out_docx.name == "a_NEW.docx"
