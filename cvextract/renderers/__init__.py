"""
CV rendering interfaces and implementations.

This module provides pluggable and interchangeable CV renderers.
"""

from .base import CVRenderer
from .docx_renderer import DocxCVRenderer

__all__ = [
    "CVRenderer",
    "DocxCVRenderer",
]
