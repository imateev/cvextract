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


def _collect_inputs(
    src: Path, is_extraction: bool, template_path: Optional[Path]
) -> List[Path]:
    """
    Validate and collect single input file.

    This function now only accepts single files, not directories.
    Directories are rejected with a clear error message.
    Also validates file type matches the operation (JSON for render, any for extraction).
    """
    if not src.exists():
        raise FileNotFoundError(f"Path not found: {src}")

    if src.is_dir():
        raise ValueError(
            f"Directories are not supported. Please provide a single file path.\n"
            f"Provided: {src}\n"
            f"Expected: A single file path."
        )

    if not src.is_file():
        raise FileNotFoundError(f"Path is not a file: {src}")

    # Validate file type for render/adjust (must be JSON)
    if not is_extraction and src.suffix.lower() != ".json":
        raise ValueError(
            f"Input file must be a JSON file for render/adjust. Got: {src}"
        )

    # For extraction, let the extractor handle file type validation
    # (different extractors support different file types)

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
    # Validate template if render stage is configured
    if config.render:
        if (
            not config.render.template.is_file()
            or config.render.template.suffix.lower() != ".docx"
        ):
            LOG.error("Template not found or not a .docx: %s", config.render.template)
            raise ValueError(f"Invalid template: {config.render.template}")

    if not config.parallel and not config.rerun_failed:
        if config.extract:
            source = config.extract.source
            is_extraction = True
        elif config.render and config.render.data:
            source = config.render.data
            is_extraction = False
        elif config.adjust and config.adjust.data:
            source = config.adjust.data
            is_extraction = False
        else:
            raise ValueError(
                "No input source specified. Use source= in --extract, or data= in --render when not chained with --extract"
            )
        _collect_inputs(source, is_extraction, None)

    # Validate target directory
    config.target_dir.mkdir(parents=True, exist_ok=True)
    if not config.target_dir.is_dir():
        LOG.error("Target is not a directory: %s", config.target_dir)
        raise ValueError(f"Target is not a directory: {config.target_dir}")

    # Create output directories for configured stages
    if config.extract or config.adjust:
        config.workspace.json_dir.mkdir(parents=True, exist_ok=True)
    if config.adjust:
        config.workspace.adjusted_json_dir.mkdir(parents=True, exist_ok=True)
    if config.render:
        config.workspace.documents_dir.mkdir(parents=True, exist_ok=True)

    return config
