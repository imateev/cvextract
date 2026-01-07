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

        return adjust_work
    except Exception:
        if config.debug:
            LOG.error("Adjustment failed: %s", traceback.format_exc())
        return base_work
