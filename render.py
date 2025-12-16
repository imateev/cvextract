"""
DOCX rendering and XML-safety utilities.

This module is responsible for rendering structured CV data into a DOCX file
using `docxtpl`. It focuses on making extracted data safe for insertion into
Word (XML-based) templates by normalizing text and removing characters that are
invalid under the XML 1.0 specification.

Responsibilities
----------------
- Load extracted CV data from JSON
- Sanitize all strings for XML / DOCX compatibility
- Render data into a DOCX template using `docxtpl`
- Write the rendered document to disk

Text Normalization & XML Safety
-------------------------------
DOCX files are XML documents and are sensitive to:
- non-breaking spaces (NBSP)
- soft hyphens
- invalid Unicode code points
- inconsistent newline encodings

To prevent template rendering failures and corrupted output, this module
provides internal helpers that:
- normalize whitespace and hyphenation
- strip characters disallowed by XML 1.0
- recursively sanitize nested data structures

All normalization helpers are intentionally private; they encode project-
specific rules and are not part of the public API.

Public API
----------
- render_from_json(json_path: Path, template_path: Path, target_dir: Path) -> Path
    Render a DOCX file from structured JSON data and a docxtpl template.

Design Notes
------------
- Sanitization happens before rendering to avoid runtime XML errors.
- Validation and extraction are handled elsewhere; this module assumes
  structurally correct input data.
- Rendering is deterministic and side-effect free except for writing the
  output file.

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