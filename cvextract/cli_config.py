"""
CLI configuration data structures.

Defines stage configuration dataclasses and UserConfig used across
the three-phase CLI architecture.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


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
class ParallelStage:
    """Configuration for the parallel processing stage."""
    input: Path  # Input directory to scan recursively
    n: int = 1  # Number of parallel workers (default=1)


@dataclass
class UserConfig:
    """Configuration gathered from user input."""
    
    # Global output directory (required)
    target_dir: Path
    
    # Stage configurations (None if stage not requested)
    extract: Optional[ExtractStage] = None
    adjust: Optional[AdjustStage] = None
    apply: Optional[ApplyStage] = None
    parallel: Optional[ParallelStage] = None
    
    # Execution settings
    strict: bool = False
    debug: bool = False
    log_file: Optional[str] = None
    suppress_summary: bool = False  # Suppress summary logging (used in parallel mode)
    
    @property
    def has_extract(self) -> bool:
        """Whether extract stage is configured."""
        return self.extract is not None
    
    @property
    def has_adjust(self) -> bool:
        """Whether adjust stage is configured."""
        return self.adjust is not None
    
    @property
    def has_apply(self) -> bool:
        """Whether apply stage is configured."""
        return self.apply is not None
    
    @property
    def should_compare(self) -> bool:
        """Whether to run comparison verification."""
        # Only compare if applying but not adjusting
        return self.has_apply and not self.has_adjust
