"""
DOCX rendering utilities.

Render a DOCX file from structured JSON data using a docxtpl template,
after sanitizing content for XML safety.
"""

from __future__ import annotations

import json
from pathlib import Path

from .shared import (
    sanitize_for_xml_in_obj,
)

from docxtpl import DocxTemplate

# ------------------------- Rendering -------------------------

def render_from_json(json_path: Path, template_path: Path, target_dir: Path) -> Path:
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    data = sanitize_for_xml_in_obj(data)

    tpl = DocxTemplate(str(template_path))
    tpl.render(data, autoescape=True)

    out_docx = target_dir / f"{json_path.stem}_NEW.docx"
    tpl.save(str(out_docx))
    return out_docx