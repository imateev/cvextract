"""
CV rendering interfaces and implementations.

This module provides pluggable and interchangeable CV renderers with a registry system.
"""

from .base import CVRenderer
from .docx_renderer import DocxCVRenderer
from .renderer_registry import (
    register_renderer,
    get_renderer,
    list_renderers,
)


# Register built-in renderers
register_renderer("private-internal-renderer", DocxCVRenderer)


__all__ = [
    "CVRenderer",
    "DocxCVRenderer",
    "register_renderer",
    "get_renderer",
    "list_renderers",
]
