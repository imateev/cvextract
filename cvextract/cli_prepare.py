"""
CLI Phase 2: Prepare execution environment.

Validates inputs and prepares directories for execution.
No actual execution - just setup.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .cli_config import UserConfig
from .logging_utils import LOG


def _collect_inputs(src: Path, is_extraction: bool, template_path: Optional[Path]) -> List[Path]:
    """
    Validate and collect single input file.
    
    This function now only accepts single files, not directories.
    Directories are rejected with a clear error message.
    """
    if not src.exists():
        raise FileNotFoundError(f"Path not found: {src}")
    
    if src.is_dir():
        raise ValueError(
            f"Directories are not supported. Please provide a single file path.\n"
            f"Provided: {src}\n"
            f"Expected: A single {'DOCX' if is_extraction else 'JSON'} file path."
        )
    
    if not src.is_file():
        raise FileNotFoundError(f"Path is not a file: {src}")
    
    return [src]


def prepare_execution_environment(config: UserConfig) -> UserConfig:
    """
    Phase 2: Validate inputs and prepare execution environment.
    
    - Validates template exists and is .docx
    - Creates target directory
    - Collects input files
    - No execution yet
    
    Returns the same config (for chaining).
    """
    # Validate template if apply stage is configured
    if config.apply:
        if not config.apply.template.is_file() or config.apply.template.suffix.lower() != ".docx":
            LOG.error("Template not found or not a .docx: %s", config.apply.template)
            raise ValueError(f"Invalid template: {config.apply.template}")

    # Validate target directory
    config.target_dir.mkdir(parents=True, exist_ok=True)
    if not config.target_dir.is_dir():
        LOG.error("Target is not a directory: %s", config.target_dir)
        raise ValueError(f"Target is not a directory: {config.target_dir}")

    return config
