"""
Step 2: Adjust stage execution.
"""

from __future__ import annotations

import time
import traceback
from dataclasses import replace
from pathlib import Path

from .adjusters import get_adjuster
from .logging_utils import LOG
from .shared import StepName, UnitOfWork
from .verifiers import get_verifier


def execute(work: UnitOfWork) -> UnitOfWork:
    config = work.config
    if not config.adjust or not work.output:
        return work

    base_work = work
    if not work.ensure_path_exists(
        StepName.Adjust,
        work.output,
        "adjust input JSON",
        must_be_file=True,
    ):
        return base_work
    try:
        base_input = work.initial_input or work.input
        if config.input_dir:
            source_base = config.input_dir.resolve()
        else:
            source = None
            if config.extract:
                source = config.extract.source
            elif config.adjust and config.adjust.data:
                source = config.adjust.data
            elif config.render and config.render.data:
                source = config.render.data
            if source is not None:
                source_base = (
                    source.parent.resolve() if source.is_file() else source.resolve()
                )
            else:
                source_base = base_input.parent.resolve()

        try:
            rel_path = base_input.parent.resolve().relative_to(source_base)
        except ValueError:
            rel_path = Path(".")

        output_path = config.adjust.output or (
            config.workspace.adjusted_json_dir / rel_path / f"{base_input.stem}.json"
        )
        adjust_work = UnitOfWork(
            config=config,
            initial_input=work.initial_input,
            input=work.output,
            output=output_path,
        )

        for idx, adjuster_config in enumerate(config.adjust.adjusters):
            if idx > 0:
                LOG.debug("Waiting 3 seconds before applying next adjuster...")
                time.sleep(3.0)

            LOG.info(
                "Applying adjuster %d/%d: %s",
                idx + 1,
                len(config.adjust.adjusters),
                adjuster_config.name,
            )

            adjuster = get_adjuster(
                adjuster_config.name,
                model=adjuster_config.openai_model or "gpt-4o-mini",
            )

            if not adjuster:
                LOG.warning("Unknown adjuster '%s', skipping", adjuster_config.name)
                continue

            adjuster_params = dict(adjuster_config.params)

            try:
                adjuster.validate_params(**adjuster_params)
            except ValueError as e:
                LOG.error(
                    "Adjuster '%s' parameter validation failed: %s",
                    adjuster_config.name,
                    e,
                )
                raise

            adjust_work = adjuster.adjust(adjust_work, **adjuster_params)
            adjust_work = replace(adjust_work, input=adjust_work.output)

        skip_verify = bool(
            config.skip_all_verify
            or (config.adjust and config.adjust.skip_verify)
        )
        if skip_verify:
            return adjust_work

        if not adjust_work.output or not adjust_work.output.exists():
            adjust_work.add_error(
                StepName.Adjust, "adjust: output JSON not found for verification"
            )
            return adjust_work

        verifier_name = "cv-schema-verifier"
        if config.adjust and config.adjust.verifier:
            verifier_name = config.adjust.verifier
        verifier = get_verifier(verifier_name)
        if not verifier:
            adjust_work.add_error(
                StepName.Adjust, f"unknown verifier: {verifier_name}"
            )
            return adjust_work

        adjust_work.ensure_step_status(StepName.Adjust)
        adjust_work.current_step = StepName.Adjust
        try:
            adjust_work = verifier.verify(adjust_work)
        except Exception as e:
            adjust_work.add_error(
                StepName.Adjust, f"adjust: verify failed ({type(e).__name__})"
            )
            return adjust_work

        return adjust_work
    except Exception:
        if config.debug:
            LOG.error("Adjustment failed: %s", traceback.format_exc())
        return base_work
