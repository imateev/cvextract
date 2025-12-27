import pytest

import json
from pathlib import Path
import cvextract.render as r
import cvextract.pipeline_highlevel as ph

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

def test_render_cv_data_with_external_data(monkeypatch, tmp_path: Path):
    """Test that render_cv_data accepts data as a parameter."""
    template_path = tmp_path / "tpl.docx"
    # Create a dummy template file
    template_path.write_text("dummy")
    
    output_path = tmp_path / "out" / "result.docx"
    
    cv_data = {
        "identity": {
            "title": "Engineer",
            "full_name": "Test User",
            "first_name": "Test",
            "last_name": "User"
        },
        "sidebar": {
            "languages": ["Python"],
            "tools": ["Docker"],
            "industries": ["Tech"],
            "spoken_languages": ["English"],
            "academic_background": ["BS CS"]
        },
        "overview": "Test overview",
        "experiences": []
    }
    
    # Mock the DocxTemplate in the renderer
    from cvextract.renderers import docx_renderer
    monkeypatch.setattr(docx_renderer, "DocxTemplate", DummyTpl)
    
    result = ph.render_cv_data(cv_data, template_path, output_path)
    assert result == output_path

def test_render_cv_data_with_external_template(monkeypatch, tmp_path: Path):
    """Test that render_cv_data accepts template path as a parameter."""
    # Create a custom template path
    custom_template = tmp_path / "templates" / "custom.docx"
    custom_template.parent.mkdir(parents=True, exist_ok=True)
    # Create a dummy template file
    custom_template.write_text("dummy")
    
    output_path = tmp_path / "out" / "result.docx"
    
    cv_data = {
        "identity": {"title": "", "full_name": "", "first_name": "", "last_name": ""},
        "sidebar": {},
        "overview": "",
        "experiences": []
    }
    
    # Mock the DocxTemplate in the renderer
    from cvextract.renderers import docx_renderer
    
    class TrackingTpl(DummyTpl):
        def __init__(self, path: str):
            super().__init__(path)
            self.template_path = path
    
    monkeypatch.setattr(docx_renderer, "DocxTemplate", TrackingTpl)
    
    result = ph.render_cv_data(cv_data, custom_template, output_path)
    assert result == output_path

