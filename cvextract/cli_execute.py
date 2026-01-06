"""
CLI Phase 3: Execute pipeline.

Orchestrates the execution of all operations with explicit path decisions.
Subsystems receive explicit input/output paths.
"""

from __future__ import annotations

from dataclasses import replace
from typing import List

from .cli_config import UserConfig
from .logging_utils import LOG
from .cli_execute_adjust import execute as execute_adjust
from .cli_execute_extract import execute as execute_extract
from .cli_execute_render import execute as execute_render
from .shared import StepName, UnitOfWork, emit_summary, emit_work_status


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
    elif config.render and config.render.data:
        source = config.render.data
    elif config.adjust and config.adjust.data:
        source = config.adjust.data
    else:
        LOG.error("No input source specified. Use source= in --extract, or data= in --render when not chained with --extract")
        return 1
    
    work = UnitOfWork(
        config=config,
        initial_input=source,
        input=source,
        output=None,
    )
           
    # Create output directories
    if config.extract or config.adjust:
        config.workspace.json_dir.mkdir(parents=True, exist_ok=True)
    
    if config.adjust:
        config.workspace.adjusted_json_dir.mkdir(parents=True, exist_ok=True)
    
    if config.render:
        config.workspace.documents_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Extract (if configured)
    if config.extract:
        work = execute_extract(work)

        extract_status = work.step_statuses.get(StepName.Extract)
        if extract_status and not extract_status.ConfiguredExecutorAvailable:
            LOG.error("Unknown extractor: %s", config.extract.name)
            LOG.error("Use --list extractors to see available extractors")
            return 1
        
        LOG.info("%s", emit_work_status(work, StepName.Extract))
        # If extraction failed and we need to render, exit early
        if (not work.has_no_errors(StepName.Extract)) and config.render:
            return 1
    else:
        # No extraction, use input JSON directly
        work = replace(work, input=work.input, output=work.input)
    
    # Step 2: Adjust (if configured)
    if config.adjust and work.output:
        work = execute_adjust(work)
    
    # Step 3: Apply/Render (if configured and not dry-run)
    if config.render:
        work = execute_render(work)

    all_warnings: List[str] = []
    if work:
        for status in work.step_statuses.values():
            all_warnings.extend(status.warnings)
    config.last_warnings = all_warnings

    # Log result (unless suppressed for parallel mode)
    if not config.suppress_file_logging:
        LOG.info("%s", emit_work_status(work))
    
    # Log summary (unless suppressed for parallel mode)
    if not config.suppress_summary:
        LOG.info("%s", emit_summary(work))
    
    # Return exit code
    if work and not work.has_no_errors():
        return 1
    
    return 0
