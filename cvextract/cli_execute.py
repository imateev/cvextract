"""
CLI Phase 3: Execute pipeline.

Orchestrates the execution of all operations with explicit path decisions.
Subsystems receive explicit input/output paths.
"""

from __future__ import annotations

import time
import traceback
from dataclasses import replace
from pathlib import Path
from typing import List, Optional

from .cli_config import UserConfig
from .cli_prepare import _collect_inputs
from .logging_utils import LOG
from .adjusters import get_adjuster
from .pipeline_helpers import (
    extract_single,
    render_and_verify,
)
from .shared import StepName, StepStatus, UnitOfWork, emit_work_status


def execute_pipeline(config: UserConfig) -> int:
    """
    Phase 3: Execute the pipeline based on user configuration.
    
    All path decisions are made here explicitly. Subsystems receive
    explicit input/output paths.
    
    Processes a single input file (not multiple files).
    Preserves source directory structure in output paths by default.
    
    Returns exit code (0 = success, 1 = failure).
    """
    # Check if parallel mode is enabled
    if config.parallel:
        from .cli_parallel import execute_parallel_pipeline
        return execute_parallel_pipeline(config)
    
    # Determine input source
    if config.extract:
        source = config.extract.source
        is_extraction = True
    elif config.apply and config.apply.data:
        source = config.apply.data
        is_extraction = False
    elif config.adjust and config.adjust.data:
        source = config.adjust.data
        is_extraction = False
    else:
        LOG.error("No input source specified. Use source= in --extract, or data= in --apply when not chained with --extract")
        return 1
    
    # Collect inputs (now expects single file)
    try:
        template_path = config.apply.template if config.apply else None
        inputs = _collect_inputs(source, is_extraction, template_path)
    except Exception as e:
        LOG.error(str(e))
        if config.debug:
            LOG.error(traceback.format_exc())
        return 1

    if not inputs:
        LOG.error("No matching input files found.")
        return 1

    # Single file processing
    input_file = inputs[0]
    
    # Determine relative path for preserving directory structure
    # Prefer input_dir from config (set in parallel processing), otherwise calculate from source
    if config.input_dir:
        # In parallel mode, input_dir is explicitly set to the root scan directory
        source_base = config.input_dir.resolve()
    else:
        # In single-file mode, determine source base from source configuration
        source_base = source.parent.resolve() if source.is_file() else source.resolve()
    
    try:
        rel_path = input_file.parent.resolve().relative_to(source_base)
    except ValueError:
        # Fallback: use empty path if we can't determine relative path
        rel_path = Path(".")
    
    # Create output directories
    if config.extract or config.adjust:
        config.workspace.json_dir.mkdir(parents=True, exist_ok=True)
    
    if config.adjust:
        config.workspace.adjusted_json_dir.mkdir(parents=True, exist_ok=True)
    
    if config.apply:
        config.workspace.documents_dir.mkdir(parents=True, exist_ok=True)

    # Initialize result tracking
    work: Optional[UnitOfWork] = None
    extract_errs: List[str] = []
    apply_ok: Optional[bool] = None
    compare_ok: Optional[bool] = None
    apply_warns: List[str] = []
    
    # Step 1: Extract (if configured)
    work = UnitOfWork(
        config=config,
        initial_input=input_file,
        input=input_file,
        output=input_file,
    )
    if config.extract:
        # Determine output path
        output_path = config.extract.output or (
            config.workspace.json_dir / rel_path / f"{input_file.stem}.json"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        work = replace(work, output=output_path)
        work = extract_single(work)
        work = replace(work, input=work.output)

        if (
            (not work.has_no_errors(StepName.Extract))
            and work.step_statuses.get(StepName.Extract)
            and work.step_statuses[StepName.Extract].errors
            and work.step_statuses[StepName.Extract].errors[0].startswith("unknown extractor:")
        ):
            LOG.error("Unknown extractor: %s", config.extract.name)
            LOG.error("Use --list extractors to see available extractors")
            return 1
        
        # If extraction failed and we need to apply, exit early
        if (not work.has_no_errors(StepName.Extract)) and config.apply:
            LOG.info("%s", emit_work_status(work, StepName.Extract))
            return 1
    else:
        # No extraction, use input JSON directly
        work = replace(work, input=work.input, output=work.input)
    
    # Step 2: Adjust (if configured)
    if config.adjust and work.output:
        base_work = work
        try:
            adjust_work = UnitOfWork(
                config=config,
                initial_input=work.initial_input,
                input=work.output,
                output=config.adjust.output or (
                    config.workspace.adjusted_json_dir / rel_path / f"{input_file.stem}.json"
                ),
            )

            # Apply each adjuster in sequence
            for idx, adjuster_config in enumerate(config.adjust.adjusters):
                # Add delay between adjusters to avoid rate limiting
                # (10 seconds gives API time to recover between requests)
                if idx > 0:
                    LOG.debug("Waiting 3 seconds before applying next adjuster...")
                    time.sleep(3.0)
                
                LOG.info("Applying adjuster %d/%d: %s", 
                        idx + 1, len(config.adjust.adjusters), adjuster_config.name)
                
                # Get the adjuster instance
                adjuster = get_adjuster(
                    adjuster_config.name,
                    model=adjuster_config.openai_model or "gpt-4o-mini"
                )
                
                if not adjuster:
                    LOG.warning("Unknown adjuster '%s', skipping", adjuster_config.name)
                    continue
                
                # Prepare parameters for this adjuster
                adjuster_params = dict(adjuster_config.params)
                
                # Validate parameters
                try:
                    adjuster.validate_params(**adjuster_params)
                except ValueError as e:
                    LOG.error("Adjuster '%s' parameter validation failed: %s", adjuster_config.name, e)
                    raise

                adjust_work = adjuster.adjust(adjust_work, **adjuster_params)
                adjust_work = replace(adjust_work, input=adjust_work.output)
                work = adjust_work  # Update main work reference
        except Exception as e:
            # If adjust fails, proceed with original JSON
            if config.debug:
                LOG.error("Adjustment failed: %s", traceback.format_exc())
            work = base_work
    
    # Step 3: Apply/Render (if configured and not dry-run)
    if config.apply and not (config.adjust and config.adjust.dry_run):
        apply_ok, render_errs, apply_warns, compare_ok = render_and_verify(work)
        work.step_statuses[StepName.Render] = StepStatus(step=StepName.Render)
        if apply_ok is False and compare_ok is None:
            for err in render_errs:
                work.AddError(StepName.Render, err)
        if compare_ok is not None:
            work.step_statuses[StepName.Verify] = StepStatus(step=StepName.Verify)
            if compare_ok is False:
                for err in render_errs:
                    work.AddError(StepName.Verify, err)
            for warn in apply_warns:
                work.AddWarning(StepName.Verify, warn)
        
        extract_errs = render_errs
    
    extract_status = work.step_statuses.get(StepName.Extract) if work else None
    extract_warns = extract_status.warnings if extract_status else []
    extract_errs = extract_errs if apply_ok is not None else (extract_status.errors if extract_status else [])
    combined_warns = (extract_warns or []) + (apply_warns or [])
    config.last_warnings = combined_warns

    # Log result (unless suppressed for parallel mode)
    if not config.suppress_file_logging:
        LOG.info("%s", emit_work_status(work))
    
    # Log summary (unless suppressed for parallel mode)
    if not config.suppress_summary:
        if config.extract and config.apply:
            LOG.info(
                "📊 Extract+Apply complete. JSON: %s | DOCX: %s",
                config.workspace.json_dir, config.workspace.documents_dir
            )
        elif config.extract:
            LOG.info(
                "📊 Extract complete. JSON in: %s",
                config.workspace.json_dir
            )
        else:
            LOG.info(
                "📊 Apply complete. Output in: %s",
                config.workspace.documents_dir
            )
    
    # Return exit code
    extract_ok = not (extract_status.errors if extract_status else [])
    if (work and not extract_ok) or apply_ok is False:
        return 1
    
    return 0
