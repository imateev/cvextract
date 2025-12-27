"""
CV extraction interfaces and implementations.

This module provides pluggable and interchangeable CV extractors.
"""

from .base import CVExtractor
from .docx_extractor import DocxCVExtractor

__all__ = [
    "CVExtractor",
    "DocxCVExtractor",
]
