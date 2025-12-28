"""
CLI configuration data structures.

Defines stage configuration dataclasses and UserConfig used across
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
class ExtractStage:
    """Configuration for the extract stage."""
    source: Path  # Input DOCX file(s)
    output: Optional[Path] = None  # Output JSON (optional, defaults to target_dir/structured_data/)


@dataclass
class AdjustStage:
    """Configuration for the adjust stage."""
    data: Optional[Path] = None  # Input JSON (optional if chained after extract)
    output: Optional[Path] = None  # Output JSON (optional, defaults based on source)
    customer_url: Optional[str] = None  # URL for customer research
    openai_model: Optional[str] = None  # OpenAI model to use
    dry_run: bool = False  # If True, only adjust without rendering


@dataclass
class ApplyStage:
    """Configuration for the apply/render stage."""
    template: Path  # Template DOCX file
    data: Optional[Path] = None  # Input JSON (optional if chained after extract/adjust)
    output: Optional[Path] = None  # Output DOCX (optional, defaults to target_dir/documents/)


@dataclass
class UserConfig:
    """Configuration gathered from user input."""
    
    # Stage configurations (None if stage not requested)
    extract: Optional[ExtractStage] = None
    adjust: Optional[AdjustStage] = None
    apply: Optional[ApplyStage] = None
    
    # Global output directory
    target_dir: Optional[Path] = None
    
    # Execution settings
    strict: bool = False
    debug: bool = False
    log_file: Optional[str] = None
    
    # Legacy mode support (for backward compatibility)
    mode: Optional[ExecutionMode] = None
    source: Optional[Path] = None
    template: Optional[Path] = None
    adjust_url: Optional[str] = None
    openai_model: Optional[str] = None
    adjust_dry_run: bool = False
    
    @property
    def has_extract(self) -> bool:
        """Whether extract stage is configured."""
        return self.extract is not None or (self.mode and self.mode.needs_extraction)
    
    @property
    def has_adjust(self) -> bool:
        """Whether adjust stage is configured."""
        return self.adjust is not None or (self.mode and self.mode.needs_adjustment)
    
    @property
    def has_apply(self) -> bool:
        """Whether apply stage is configured."""
        return self.apply is not None or (self.mode and self.mode.needs_rendering)
    
    @property
    def should_compare(self) -> bool:
        """Whether to run comparison verification."""
        # Only compare if applying but not adjusting
        return self.has_apply and not self.has_adjust
