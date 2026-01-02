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

from .extractors import DocxCVExtractor, CVExtractor
from .renderers import DocxCVRenderer
    
# ------------------------- High-level pipeline -------------------------

def extract_cv_structure(
    source_path: Path, 
    extractor: Optional[CVExtractor] = None
) -> Dict[str, Any]:
    """
    Extract CV structure from a source file using the specified extractor.
    
    Args:
        source_path: Path to the source file
        extractor: CVExtractor instance to use. If None, uses default DocxCVExtractor
    
    Returns:
        Dictionary containing extracted CV data
    """
    if extractor is None:
        extractor = DocxCVExtractor()
    return extractor.extract(source_path)

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

def process_single_docx(
    source_path: Path, 
    out: Optional[Path] = None,
    extractor: Optional[CVExtractor] = None
) -> Dict[str, Any]:
    """
    Extract CV structure and optionally write to JSON.
    
    Args:
        source_path: Path to the source file
        out: Optional output path for JSON file
        extractor: Optional CVExtractor instance to use
    
    Returns:
        Dictionary containing extracted CV data
    """
    data = extract_cv_structure(source_path, extractor)

    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    return data