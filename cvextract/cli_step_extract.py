"""
CLI execution step: Extract data from DOCX files.

Handles the extraction phase of the pipeline, converting DOCX files
to structured JSON data.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from .cli_config import UserConfig
from .logging_utils import LOG, fmt_issues
from .pipeline_helpers import (
    extract_single,
    get_status_icons,
    categorize_result,
)


def process_extraction(
    input_file: Path,
    out_json: Path,
    rel_name: str,
    config: UserConfig,
) -> Tuple[bool, List[str], List[str], bool]:
    """
    Extract data from a DOCX file to JSON.
    
    Args:
        input_file: Path to input DOCX file
        out_json: Path where JSON should be saved
        rel_name: Relative name for logging
        config: User configuration
    
    Returns:
        Tuple of (extract_ok, extract_errs, extract_warns, had_warning)
    """
    # Skip non-DOCX files
    if input_file.suffix.lower() != ".docx":
        return False, [], [], False
    
    # Create output directory
    out_json.parent.mkdir(parents=True, exist_ok=True)
    
    # Extract data
    extract_ok, extract_errs, extract_warns = extract_single(input_file, out_json, config.debug)
    had_warning = bool(extract_warns)
    
    # If extraction failed and we need to render, log and return early
    if not extract_ok and config.mode.needs_rendering:
        x_icon, a_icon, c_icon = get_status_icons(extract_ok, had_warning, None, None)
        LOG.info("%s%s%s %s | %s", x_icon, a_icon, c_icon, rel_name, 
                 fmt_issues(extract_errs, extract_warns))
    
    return extract_ok, extract_errs, extract_warns, had_warning
