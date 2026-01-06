"""
Step 3: Render/Verify stage execution.
"""

from __future__ import annotations

from .pipeline_helpers import render_and_verify
from .shared import StepName, StepStatus, UnitOfWork


def execute(work: UnitOfWork) -> UnitOfWork:
    config = work.config
    if not config.render or (config.adjust and config.adjust.dry_run):
        return work

    if not work.ensure_path_exists(
        StepName.Render,
        work.output,
        "render input JSON",
        must_be_file=True,
    ):
        return work
    if not work.ensure_path_exists(
        StepName.Render,
        config.render.template,
        "render template",
        must_be_file=True,
    ):
        return work

    apply_ok, render_errs, apply_warns, compare_ok = render_and_verify(work)
    work.step_statuses[StepName.Render] = StepStatus(step=StepName.Render)
    if apply_ok is False and compare_ok is None:
        for err in render_errs:
            work.add_error(StepName.Render, err)
    if compare_ok is not None:
        work.step_statuses[StepName.Verify] = StepStatus(step=StepName.Verify)
        if compare_ok is False:
            for err in render_errs:
                work.add_error(StepName.Verify, err)
        for warn in apply_warns:
            work.add_warning(StepName.Verify, warn)

    return work
