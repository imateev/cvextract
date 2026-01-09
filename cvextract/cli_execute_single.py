"""
CLI Phase 3: Execute single-file pipeline.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from cvextract.pipeline_helpers import _resolve_parent, extract_cv_data

from .cli_config import UserConfig
from .cli_execute_adjust import execute as execute_adjust
from .cli_execute_extract import execute as execute_extract
from .cli_execute_render import execute as execute_render
from .logging_utils import LOG
from .shared import StepName, UnitOfWork, emit_summary, emit_work_status
from .verifiers import get_verifier


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
    )
    if config.extract:
        work.set_step_paths(StepName.Extract, input_path=source)
    else:
        if config.adjust:
            work.set_step_paths(StepName.Adjust, input_path=source)
        if config.render:
            work.set_step_paths(StepName.Render, input_path=source)

    # Step 1: Extract (if configured)
    if config.extract:
        work = execute_extract(work)

        extract_status = work.step_states.get(StepName.Extract)
        if extract_status and not extract_status.ConfiguredExecutorAvailable:
            LOG.error("Unknown extractor: %s", config.extract.name)
            LOG.error("Use --list extractors to see available extractors")
            return 1, work

        if not work.has_no_errors(StepName.Extract):
            if config.adjust or config.render:
                config = replace(config, adjust=None, render=None)
    else:
        # No extraction, use input JSON directly for downstream steps
        if config.adjust:
            work.set_step_paths(StepName.Adjust, input_path=source)
        if config.render:
            work.set_step_paths(StepName.Render, input_path=source)

    # Step 2: Adjust (if configured)
    if config.adjust:
        work = execute_adjust(work)

        if not work.has_no_errors(StepName.Adjust):
            if config.render:
                config = replace(config, render=None)

    # Step 3: Render (if configured and not dry-run)
    if config.render:
        work = execute_render(work)

        if config.should_compare:
            render_status = work.step_states.get(StepName.Render)
            roundtrip_work = UnitOfWork(
                config=work.config
            )
            rendered_json = "/tmp/out/rendered.json"
            roundtrip_work.set_step_paths(
                StepName.Extract, input_path=render_status.output, output_path=rendered_json
            )
            roundtrip_work = extract_cv_data(roundtrip_work)
            
            verifier_name = "roundtrip-verifier"
            if work.config.render and work.config.render.verifier:
                verifier_name = work.config.render.verifier
                verifier = get_verifier(verifier_name)
            if not verifier:
                raise ValueError(f"unknown verifier: {verifier_name}")
            render_status = roundtrip_work.step_states.get(StepName.Extract)
            roundtrip_work.set_step_paths(
                StepName.RoundtripComparer, input_path=render_status.output, output_path=None
            )
            work = verifier().verify(work)

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
