"""
CLI Phase 3: Execute single-file pipeline.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from .cli_config import UserConfig
from .cli_execute_adjust import execute as execute_adjust
from .cli_execute_extract import execute as execute_extract
from .cli_execute_render import execute as execute_render
from .logging_utils import LOG
from .shared import StepName, UnitOfWork, emit_summary, emit_work_status


def _resolve_input_source(config: UserConfig) -> Path | None:
    if config.extract:
        return config.extract.source
    if config.render and config.render.data:
        return config.render.data
    if config.adjust and config.adjust.data:
        return config.adjust.data
    return None


def execute_single(config: UserConfig) -> tuple[int, UnitOfWork | None]:
    source = _resolve_input_source(config)
    if source is None:
        LOG.error(
            "No input source specified. Use source= in --extract, or data= in --render when not chained with --extract"
        )
        return 1, None

    work = UnitOfWork(
        config=config,
        initial_input=source,
        input=source,
        output=None,
    )

    # Step 1: Extract (if configured)
    if config.extract:
        work = execute_extract(work)

        extract_status = work.step_statuses.get(StepName.Extract)
        if extract_status and not extract_status.ConfiguredExecutorAvailable:
            LOG.error("Unknown extractor: %s", config.extract.name)
            LOG.error("Use --list extractors to see available extractors")
            return 1, work

        # If extraction failed and we need to render, exit early
        if (not work.has_no_errors(StepName.Extract)) and config.render:
            return 1, work
    else:
        # No extraction, use input JSON directly
        work = replace(work, input=work.input, output=work.input)

    # Step 2: Adjust (if configured)
    if config.adjust and work.output:
        work = execute_adjust(work)

    # Step 3: Render (if configured and not dry-run)
    if config.render:
        work = execute_render(work)

    # Log result (unless suppressed for parallel mode)
    if not config.suppress_file_logging:
        LOG.info("%s", emit_work_status(work))

    # Log summary (unless suppressed for parallel mode)
    if not config.suppress_summary:
        LOG.info("%s", emit_summary(work))

    # Return exit code
    if not work.has_no_errors():
        return 1, work

    return 0, work
