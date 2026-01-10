"""
CV extraction interfaces and implementations.

This module provides pluggable and interchangeable CV extractors with a registry system.
"""

from .base import CVExtractor
from .docx_extractor import DocxCVExtractor
from .openai_extractor import OpenAICVExtractor
from .extractor_registry import (
    register_extractor,
    get_extractor,
    list_extractors,
)


# Register built-in extractors
register_extractor("default_docx_cv_extractor", DocxCVExtractor)
register_extractor("openai-extractor", OpenAICVExtractor)


__all__ = [
    "CVExtractor",
    "DocxCVExtractor",
    "OpenAICVExtractor",
    "register_extractor",
    "get_extractor",
    "list_extractors",
]
