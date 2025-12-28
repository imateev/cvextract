"""
CLI Phase 3: Execute pipeline.

Orchestrates the execution of all operations with explicit path decisions.
Subsystems receive explicit input/output paths.
"""

from __future__ import annotations

import traceback
from pathlib import Path
from typing import List, Optional

from .cli_config import ExecutionMode, UserConfig
from .cli_prepare import _collect_inputs
from .cli_step_extract import process_extraction
from .cli_step_adjust import process_adjustment
from .cli_step_render import process_rendering
from .logging_utils import LOG, fmt_issues
from .pipeline_helpers import (
    infer_source_root,
    safe_relpath,
    get_status_icons,
    categorize_result,
)


def execute_pipeline(config: UserConfig) -> int:
    """
    Phase 3: Execute the pipeline based on user configuration.
    
    All path decisions are made here explicitly. Subsystems receive
    explicit input/output paths.
    
    Returns exit code (0 = success, 1 = failure, 2 = strict mode warnings).
    """
    # Collect inputs
    try:
        inputs = _collect_inputs(config.source, config.mode, config.template)
    except Exception as e:
        LOG.error(str(e))
        if config.debug:
            LOG.error(traceback.format_exc())
        return 1

    if not inputs:
        LOG.error("No matching input files found.")
        return 1

    # Infer source root for preserving directory structure
    source_root = infer_source_root(inputs)
    
    # Create output directories based on mode
    json_dir = config.target_dir / "structured_data"
    documents_dir = config.target_dir / "documents"
    research_dir = config.target_dir / "research_data"
    verification_dir = config.target_dir / "verification_structured_data"
    
    if config.mode.needs_extraction or config.mode == ExecutionMode.ADJUST:
        json_dir.mkdir(parents=True, exist_ok=True)
    
    if config.mode.needs_rendering:
        documents_dir.mkdir(parents=True, exist_ok=True)
    
    if config.mode.needs_adjustment:
        research_dir.mkdir(parents=True, exist_ok=True)

    # Process each input file
    fully_ok = partial_ok = failed = 0
    had_warning = False

    for input_file in inputs:
        # Determine relative path for preserving directory structure
        rel_name = safe_relpath(input_file, source_root)
        rel_parent = input_file.parent.resolve().relative_to(source_root)
        
        # Initialize result tracking
        extract_ok = True
        extract_errs: List[str] = []
        extract_warns: List[str] = []
        apply_ok: Optional[bool] = None
        compare_ok: Optional[bool] = None
        apply_warns: List[str] = []
        
        # Step 1: Extract (if needed)
        if config.mode.needs_extraction:
            out_json = json_dir / rel_parent / f"{input_file.stem}.json"
            extract_ok, extract_errs, extract_warns, step_had_warning = process_extraction(
                input_file, out_json, rel_name, config
            )
            
            if step_had_warning:
                had_warning = True
            
            # If extraction failed and we need to render, skip rendering
            if not extract_ok and config.mode.needs_rendering:
                full, part, fail = categorize_result(extract_ok, bool(extract_warns), None)
                fully_ok += full
                partial_ok += part
                failed += fail
                continue
        else:
            # For non-extraction modes, use the input JSON directly
            if input_file.suffix.lower() != ".json":
                continue
            out_json = input_file
        
        # Step 2: Adjust (if needed)
        render_json = process_adjustment(
            input_file, out_json, documents_dir, research_dir, rel_parent, config
        )
        
        # Step 3: Render (if needed and not dry-run)
        apply_ok, render_errs, apply_warns, compare_ok, step_had_warning = process_rendering(
            input_file, render_json, documents_dir, verification_dir, rel_parent, config
        )
        
        if step_had_warning:
            had_warning = True
        
        if render_errs:
            extract_errs = render_errs
        
        # Log result
        combined_warns = (extract_warns or []) + (apply_warns or [])
        x_icon, a_icon, c_icon = get_status_icons(extract_ok, bool(combined_warns), apply_ok, compare_ok)
        LOG.info("%s%s%s %s | %s", x_icon, a_icon, c_icon, rel_name, 
                 fmt_issues(extract_errs, combined_warns))
        
        # Categorize result
        full, part, fail = categorize_result(extract_ok, bool(combined_warns), apply_ok)
        fully_ok += full
        partial_ok += part
        failed += fail
    
    # Log summary
    total = fully_ok + partial_ok + failed
    
    if config.mode.needs_extraction and config.mode.needs_rendering:
        LOG.info(
            "📊 Extract+Apply summary: %d fully successful, %d partially successful, %d failed (total %d). JSON: %s | DOCX: %s",
            fully_ok, partial_ok, failed, total, json_dir, documents_dir
        )
    elif config.mode.needs_extraction:
        LOG.info(
            "📊 Extract summary: %d fully successful, %d partially successful, %d failed (total %d). JSON in: %s",
            fully_ok, partial_ok, failed, total, json_dir
        )
    else:
        LOG.info(
            "📊 Apply summary: %d successful, %d failed (total %d). Output in: %s",
            fully_ok, failed, total, documents_dir
        )
    
    # Return exit code
    if config.strict and had_warning:
        LOG.error("Strict mode enabled: warnings treated as failure.")
        return 2
    
    if failed == 0 and partial_ok == 0:
        return 0
    
    return 1

