"""
High-level CV extraction pipeline.

Orchestrates body parsing and sidebar parsing to produce a complete,
structured representation of a CV.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .extractors import DocxCVExtractor
from .renderers import DocxCVRenderer
    
# ------------------------- High-level pipeline -------------------------

def extract_cv_structure(docx_path: Path) -> Dict[str, Any]:
    """
    Extract CV structure from a DOCX file using the default extractor.
    
    This function maintains backward compatibility while using the new
    pluggable extractor architecture.
    """
    extractor = DocxCVExtractor()
    return extractor.extract(docx_path)

def render_cv_data(cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
    """
    Render CV data to a DOCX file using the default renderer.
    
    This function maintains backward compatibility while using the new
    pluggable renderer architecture.
    
    Args:
        cv_data: Dictionary containing CV data conforming to cv_schema.json
        template_path: Path to the template file
        output_path: Path where the rendered output should be saved
    
    Returns:
        Path to the rendered output file
    """
    renderer = DocxCVRenderer()
    return renderer.render(cv_data, template_path, output_path)

def process_single_docx(docx_path: Path, out: Optional[Path] = None) -> Dict[str, Any]:
    """Extract CV structure and optionally write to JSON. Returns extracted data dict."""
    data = extract_cv_structure(docx_path)

    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    return data