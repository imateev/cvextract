"""
High-level CV extraction pipeline.

Orchestrates body parsing and sidebar parsing to produce a complete,
structured representation of a CV.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .extractors import CVExtractor, DocxCVExtractor
from .renderers import get_renderer
from .shared import UnitOfWork

# ------------------------- High-level pipeline -------------------------


def extract_cv_structure(
    source_path: Path, extractor: Optional[CVExtractor] = None
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


def render_cv_data(work: UnitOfWork) -> UnitOfWork:
    """
    Render CV data to a DOCX file using the default renderer.

    This function uses the default renderer from the pluggable
    renderer architecture.

    Args:
        work: UnitOfWork containing render configuration and paths.

    Returns:
        UnitOfWork with rendered output populated
    """
    renderer = get_renderer("private-internal-renderer")
    if not renderer:
        raise ValueError("Default renderer 'private-internal-renderer' not found")
    return renderer.render(work)


def process_single_docx(
    source_path: Path,
    out: Optional[Path] = None,
    extractor: Optional[CVExtractor] = None,
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
