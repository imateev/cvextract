"""
CLI configuration data structures.

Defines stage configuration dataclasses and UserConfig used across
the three-phase CLI architecture.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ExtractStage:
    """Configuration for the extract stage."""

    source: Path  # Input file(s)
    name: str = (
        "default-docx-cv-extractor"  # Extractor name (default: default-docx-cv-extractor)
    )
    output: Optional[Path] = (
        None  # Output JSON (optional, defaults to target_dir/structured_data/)
    )
    verifier: Optional[str] = None  # Verifier name (optional)
    skip_verify: bool = False  # Skip verification for this stage


@dataclass
class AdjusterConfig:
    """Configuration for a single adjuster."""

    name: str  # Adjuster name (e.g., "openai-company-research")
    params: Dict[str, Any]  # Adjuster-specific parameters
    openai_model: Optional[str] = (
        None  # OpenAI model to use (for OpenAI-based adjusters)
    )


@dataclass
class AdjustStage:
    """Configuration for the adjust stage (supports multiple adjusters)."""

    adjusters: List[AdjusterConfig]  # List of adjusters to apply in order
    data: Optional[Path] = None  # Input JSON (optional if chained after extract)
    output: Optional[Path] = None  # Output JSON (optional, defaults based on source)
    verifier: Optional[str] = None  # Verifier name (optional)
    skip_verify: bool = False  # Skip verification for this stage


@dataclass
class RenderStage:
    """Configuration for the render stage."""

    template: Path  # Template DOCX file
    data: Optional[Path] = None  # Input JSON (optional if chained after extract/adjust)
    output: Optional[Path] = (
        None  # Output DOCX (optional, defaults to target_dir/documents/)
    )
    verifier: Optional[str] = None  # Verifier name (optional)
    skip_verify: bool = False  # Skip verification for this stage


@dataclass
class ParallelStage:
    """Configuration for the parallel processing stage."""

    source: Path  # Input directory to scan recursively
    n: int = 1  # Number of parallel workers (default=1)
    file_type: str = "*.docx"  # File pattern to match (default=*.docx)


@dataclass(frozen=True)
class UserConfig:
    """Configuration gathered from user input."""

    # Global output directory (required)
    target_dir: Path

    # Stage configurations (None if stage not requested)
    extract: Optional[ExtractStage] = None
    adjust: Optional[AdjustStage] = None
    render: Optional[RenderStage] = None
    parallel: Optional[ParallelStage] = None

    # Execution settings
    verbosity: str = "minimal"  # Output verbosity level: minimal, verbose, debug
    skip_all_verify: bool = False  # Skip all verification steps (global override)
    debug_external: bool = False  # Capture external provider logs (OpenAI, httpx, etc.)
    log_file: Optional[str] = None
    log_failed: Optional[Path] = None  # Optional file path to write failed files
    rerun_failed: Optional[Path] = None  # Optional file path to re-run failed files
    suppress_summary: bool = False  # Suppress summary logging (used in parallel mode)
    input_dir: Optional[Path] = (
        None  # Root input directory for relative path calculation (used in parallel processing)
    )
    suppress_file_logging: bool = (
        False  # Suppress individual file logging (used in parallel mode)
    )
    last_warnings: List[str] = field(
        default_factory=list
    )  # Warnings from the most recent run

    @property
    def workspace(self) -> "Workspace":
        """Directory layout derived from target_dir."""
        return Workspace(self.target_dir)

    @property
    def debug(self) -> bool:
        """True if verbosity is 'debug'."""
        return self.verbosity == "debug"

    @property
    def has_extract(self) -> bool:
        """Whether extract stage is configured."""
        return self.extract is not None

    @property
    def has_adjust(self) -> bool:
        """Whether adjust stage is configured."""
        return self.adjust is not None

    @property
    def has_render(self) -> bool:
        """Whether render stage is configured."""
        return self.render is not None

    @property
    def should_compare(self) -> bool:
        """Whether to run comparison verification."""
        # Only compare if rendering but not adjusting
        if not self.has_render or self.has_adjust:
            return False
        if self.skip_all_verify:
            return False
        if self.render and self.render.skip_verify:
            return False
        return True


@dataclass(frozen=True)
class Workspace:
    """Output directory layout for a run."""

    target_dir: Path

    @property
    def json_dir(self) -> Path:
        return self.target_dir / "structured_data"

    @property
    def adjusted_json_dir(self) -> Path:
        return self.target_dir / "adjusted_structured_data"

    @property
    def documents_dir(self) -> Path:
        return self.target_dir / "documents"

    @property
    def research_dir(self) -> Path:
        return self.target_dir / "research_data"

    @property
    def verification_dir(self) -> Path:
        return self.target_dir / "verification_structured_data"
