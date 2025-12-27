"""
Batch pipeline runners - facade module.

This module re-exports the mode runner functions for backward compatibility.
The actual implementations are in separate mode-specific modules.
"""

from .pipeline_extract import run_extract_mode
from .pipeline_apply import run_apply_mode
from .pipeline_extract_apply import run_extract_apply_mode
from .pipeline_helpers import (
    infer_source_root,
    safe_relpath,
)

# Re-export for backward compatibility
__all__ = [
    "run_extract_mode",
    "run_apply_mode",
    "run_extract_apply_mode",
    "infer_source_root",
    "safe_relpath",
]
