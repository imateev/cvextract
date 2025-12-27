"""
CV extraction interfaces and implementations.

This module provides pluggable and interchangeable CV extractors.
"""

from .base import CVExtractor
from .docx_extractor import DocxCVExtractor
from .sidebar_parser import extract_all_header_paragraphs, split_identity_and_sidebar
from .body_parser import parse_cv_from_docx_body

__all__ = [
    "CVExtractor",
    "DocxCVExtractor",
    "extract_all_header_paragraphs",
    "split_identity_and_sidebar",
    "parse_cv_from_docx_body",
]
