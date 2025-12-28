"""
CLI Phase 2: Prepare execution environment.

Validates inputs and prepares directories for execution.
No actual execution - just setup.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .cli_config import ExecutionMode, UserConfig
from .logging_utils import LOG


def _collect_inputs(src: Path, mode: ExecutionMode, template_path: Optional[Path]) -> List[Path]:
    """Collect input files based on source path and execution mode."""
    if src.is_file():
        return [src]

    if not src.is_dir():
        raise FileNotFoundError(f"Path not found or not a file/folder: {src}")

    # For extraction modes, collect DOCX files (excluding template)
    if mode.needs_extraction:
        return [
            p for p in src.rglob("*.docx")
            if p.is_file()
            and (template_path is None or p.resolve() != template_path.resolve())
        ]

    # For render-only modes, collect JSON files
    return [p for p in src.rglob("*.json") if p.is_file()]


def prepare_execution_environment(config: UserConfig) -> UserConfig:
    """
    Phase 2: Validate inputs and prepare execution environment.
    
    - Validates template exists and is .docx
    - Creates target directory
    - Collects input files
    - No execution yet
    
    Returns the same config (for chaining).
    """
    # Validate template (required for modes that need rendering)
    if config.mode.needs_rendering or config.mode.needs_extraction:
        if config.template is None:
            LOG.error("Template is required for this mode")
            raise ValueError("Template is required")
        
        if not config.template.is_file() or config.template.suffix.lower() != ".docx":
            LOG.error("Template not found or not a .docx: %s", config.template)
            raise ValueError(f"Invalid template: {config.template}")

    # Validate target directory
    config.target_dir.mkdir(parents=True, exist_ok=True)
    if not config.target_dir.is_dir():
        LOG.error("Target is not a directory: %s", config.target_dir)
        raise ValueError(f"Target is not a directory: {config.target_dir}")

    return config
