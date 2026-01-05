"""
Batch pipeline helper utilities.

This module re-exports helper functions for backward compatibility.
The main pipeline execution has been consolidated into cli.py.
"""

from .pipeline_helpers import (
    infer_source_root,
    safe_relpath,
    extract_single,
    UnitOfWork,
    render_and_verify,
    get_status_icons,
    categorize_result,
)

# Re-export for backward compatibility
__all__ = [
    "infer_source_root",
    "safe_relpath",
    "extract_single",
    "UnitOfWork",
    "render_and_verify",
    "get_status_icons",
    "categorize_result",
]
