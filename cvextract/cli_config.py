"""
CLI configuration data structures.

Defines ExecutionMode enum and UserConfig dataclass used across
the three-phase CLI architecture.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class ExecutionMode(Enum):
    """Execution modes that explicitly describe what operations to perform."""
    
    EXTRACT = "extract"
    EXTRACT_RENDER = "extract-render"
    EXTRACT_ADJUST = "extract-adjust"
    EXTRACT_ADJUST_RENDER = "extract-adjust-render"
    RENDER = "render"
    ADJUST = "adjust"
    ADJUST_RENDER = "adjust-render"
    
    @property
    def needs_extraction(self) -> bool:
        """Whether this mode requires extracting data from DOCX."""
        return self in (
            ExecutionMode.EXTRACT,
            ExecutionMode.EXTRACT_RENDER,
            ExecutionMode.EXTRACT_ADJUST,
            ExecutionMode.EXTRACT_ADJUST_RENDER,
        )
    
    @property
    def needs_adjustment(self) -> bool:
        """Whether this mode requires adjusting data for customer."""
        return self in (
            ExecutionMode.EXTRACT_ADJUST,
            ExecutionMode.EXTRACT_ADJUST_RENDER,
            ExecutionMode.ADJUST,
            ExecutionMode.ADJUST_RENDER,
        )
    
    @property
    def needs_rendering(self) -> bool:
        """Whether this mode requires rendering to DOCX."""
        return self in (
            ExecutionMode.EXTRACT_RENDER,
            ExecutionMode.EXTRACT_ADJUST_RENDER,
            ExecutionMode.RENDER,
            ExecutionMode.ADJUST_RENDER,
        )
    
    @property
    def should_compare(self) -> bool:
        """Whether this mode should run comparison verification (only if no adjustment)."""
        return self.needs_rendering and not self.needs_adjustment


@dataclass
class UserConfig:
    """Configuration gathered from user input."""
    
    mode: ExecutionMode
    source: Path
    template: Optional[Path]
    target_dir: Path
    
    # Adjustment settings
    adjust_url: Optional[str] = None
    openai_model: Optional[str] = None
    adjust_dry_run: bool = False
    
    # Execution settings
    strict: bool = False
    debug: bool = False
    log_file: Optional[str] = None
