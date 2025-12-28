"""
CLI execution step: Render JSON data to DOCX.

Handles the rendering phase where JSON data is applied to a DOCX
template to generate the final document.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from .cli_config import UserConfig
from .pipeline_helpers import render_and_verify


def process_rendering(
    input_file: Path,
    render_json: Path,
    documents_dir: Path,
    verification_dir: Path,
    rel_parent: Path,
    config: UserConfig,
) -> Tuple[Optional[bool], List[str], List[str], Optional[bool], bool]:
    """
    Render JSON data to DOCX using a template.
    
    Args:
        input_file: Original input file (for naming)
        render_json: Path to JSON file to render
        documents_dir: Base documents directory
        verification_dir: Base verification directory
        rel_parent: Relative parent directory
        config: User configuration
    
    Returns:
        Tuple of (apply_ok, render_errs, apply_warns, compare_ok, had_warning)
    """
    # If rendering not needed or dry-run mode, return early
    if not config.mode.needs_rendering or config.adjust_dry_run:
        return None, [], [], None, False
    
    # Create output directory
    out_docx_dir = documents_dir / rel_parent
    out_docx_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine explicit output path for rendered DOCX
    output_docx = out_docx_dir / f"{input_file.stem}_NEW.docx"
    
    # Determine verification directory
    verify_dir = verification_dir / rel_parent
    
    # Render and verify
    apply_ok, render_errs, apply_warns, compare_ok = render_and_verify(
        json_path=render_json,
        template_path=config.template,
        output_docx=output_docx,  # Explicit path
        debug=config.debug,
        skip_compare=not config.mode.should_compare,
        roundtrip_dir=verify_dir,
    )
    
    had_warning = bool(apply_warns)
    
    return apply_ok, render_errs, apply_warns, compare_ok, had_warning
