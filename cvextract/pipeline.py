"""
Batch pipeline helper utilities.

This module re-exports helper functions for backward compatibility.
The main pipeline execution has been consolidated into cli.py.
"""

from .pipeline_helpers import (
    categorize_result,
    extract_single,
    infer_source_root,
    render,
    safe_relpath,
)
from .shared import UnitOfWork, get_status_icons

# Re-export for backward compatibility
__all__ = [
    "infer_source_root",
    "safe_relpath",
    "extract_single",
    "UnitOfWork",
    "render",
    "get_status_icons",
    "categorize_result",
]
