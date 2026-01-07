"""
High-level CV extraction pipeline.

Orchestrates body parsing and sidebar parsing to produce a complete,
structured representation of a CV.
"""

from __future__ import annotations

from typing import Optional

from .extractors import CVExtractor, DocxCVExtractor
from .renderers import get_renderer
from .shared import UnitOfWork

# ------------------------- High-level pipeline -------------------------


def extract_cv_structure(
    work: UnitOfWork, extractor: Optional[CVExtractor] = None
) -> UnitOfWork:
    """
    Extract CV structure from a source file using the specified extractor.

    Args:
        work: UnitOfWork containing input/output paths.
        extractor: CVExtractor instance to use. If None, uses default DocxCVExtractor

    Returns:
        UnitOfWork with output JSON populated.
    """
    if extractor is None:
        extractor = DocxCVExtractor()
    return extractor.extract(work)


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
    work: UnitOfWork,
    extractor: Optional[CVExtractor] = None,
) -> UnitOfWork:
    """
    Extract CV structure and write to JSON at work.output.

    Args:
        work: UnitOfWork containing input/output paths.
        extractor: Optional CVExtractor instance to use.

    Returns:
        UnitOfWork with output JSON populated.
    """
    return extract_cv_structure(work, extractor)
