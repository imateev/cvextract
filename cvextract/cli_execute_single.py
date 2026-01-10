"""
CLI Phase 3: Execute single-file pipeline.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from cvextract.pipeline_helpers import extract_cv_data

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


def roundtrip_verify(work: UnitOfWork) -> UnitOfWork:
    render_status = work.step_states.get(StepName.Render)
    extract_status = work.step_states.get(StepName.Extract)
    if not render_status or render_status.errors or render_status.output is None:
        return work
    if (
        not extract_status
        or extract_status.output is None
        or not extract_status.output.exists()
    ):
        work.add_error(
            StepName.VerifyRender,
            "roundtrip: extract output unavailable for comparison",
        )
        return work

    roundtrip_dir = work.config.workspace.verification_dir
    roundtrip_dir.mkdir(parents=True, exist_ok=True)
    roundtrip_json = roundtrip_dir / f"{render_status.output.stem}.json"

    roundtrip_work = UnitOfWork(
        config=work.config,
        initial_input=work.initial_input,
    )
    roundtrip_work.set_step_paths(
        StepName.Extract,
        input_path=render_status.output,
        output_path=roundtrip_json,
    )
    try:
        roundtrip_work = extract_cv_data(roundtrip_work)
    except Exception as e:
        work.add_error(
            StepName.VerifyRender,
            f"roundtrip: extract failed ({type(e).__name__})",
        )
        return work

    roundtrip_output = roundtrip_work.get_step_output(StepName.Extract)
    if not roundtrip_output or not roundtrip_output.exists():
        work.add_error(
            StepName.VerifyRender,
            f"roundtrip: output JSON not created: {roundtrip_output or roundtrip_json}",
        )
        return work

    verifier_name = "roundtrip-verifier"
    if work.config.render and work.config.render.verifier:
        verifier_name = work.config.render.verifier
    verifier = get_verifier(verifier_name)
    if not verifier:
        raise ValueError(f"unknown verifier: {verifier_name}")

    work.set_step_paths(
        StepName.VerifyRender,
        input_path=roundtrip_output
    )
    work.current_step = StepName.VerifyRender
    return verifier.verify(work)


def extract_verify(work: UnitOfWork) -> UnitOfWork:
    config = work.config
    if not config.extract:
        return work

    skip_verify = bool(
        config.skip_all_verify or (config.extract and config.extract.skip_verify)
    )
    if skip_verify:
        return work

    output_path = work.get_step_output(StepName.Extract)
    if not output_path or not output_path.exists():
        work.add_error(
            StepName.VerifyExtract, "extract: output JSON not found for verification"
        )
        return work

    verifier_name = "default-extract-verifier"
    if config.extract and config.extract.verifier:
        verifier_name = config.extract.verifier
    verifier = get_verifier(verifier_name)
    if not verifier:
        work.add_error(StepName.VerifyExtract, f"unknown verifier: {verifier_name}")
        return work

    work.set_step_paths(StepName.VerifyExtract, output_path=output_path)
    work.ensure_step_status(StepName.VerifyExtract)
    work.current_step = StepName.VerifyExtract
    try:
        work = verifier.verify(work)
    except Exception as e:
        work.add_error(
            StepName.VerifyExtract, f"extract: verify failed ({type(e).__name__})"
        )
        return work

    return work


def adjust_verify(work: UnitOfWork) -> UnitOfWork:
    config = work.config
    if not config.adjust:
        return work

    skip_verify = bool(
        config.skip_all_verify or (config.adjust and config.adjust.skip_verify)
    )
    if skip_verify:
        return work

    output_path = work.get_step_output(StepName.Adjust)
    if not output_path or not output_path.exists():
        work.add_error(
            StepName.VerifyAdjust, "adjust: output JSON not found for verification"
        )
        return work

    verifier_name = "cv-schema-verifier"
    if config.adjust and config.adjust.verifier:
        verifier_name = config.adjust.verifier
    verifier = get_verifier(verifier_name)
    if not verifier:
        work.add_error(StepName.VerifyAdjust, f"unknown verifier: {verifier_name}")
        return work

    work.set_step_paths(StepName.VerifyAdjust, output_path=output_path)
    work.ensure_step_status(StepName.VerifyAdjust)
    work.current_step = StepName.VerifyAdjust
    try:
        work = verifier.verify(work)
    except Exception as e:
        work.add_error(StepName.VerifyAdjust, f"adjust: verify failed ({type(e).__name__})")
        return work

    return work


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

    # Step 1: Extract (if configured)
    if config.extract:
        work.set_step_paths(StepName.Extract, input_path=source)
        work = execute_extract(work)

        extract_status = work.step_states.get(StepName.Extract)
        if extract_status and not extract_status.ConfiguredExecutorAvailable:
            LOG.error("Unknown extractor: %s", config.extract.name)
            LOG.error("Use --list extractors to see available extractors")
            return 1, work

        if work.has_no_errors(StepName.Extract):
            work = extract_verify(work)

        if not work.has_no_errors(StepName.Extract) or not work.has_no_errors(
            StepName.VerifyExtract
        ):
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

        if work.has_no_errors(StepName.Adjust):
            work = adjust_verify(work)

        if not work.has_no_errors(StepName.Adjust) or not work.has_no_errors(
            StepName.VerifyAdjust
        ):
            if config.render:
                config = replace(config, render=None)

    # Step 3: Render (if configured)
    if config.render:
        work = execute_render(work)

        if config.should_compare and not (
            config.extract and config.extract.name == "openai-extractor"
        ):
            work = roundtrip_verify(work)

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
