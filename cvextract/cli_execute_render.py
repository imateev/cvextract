"""
Step 3: Render/Verify stage execution.
"""

from __future__ import annotations

from .pipeline_helpers import render
from .shared import StepName, UnitOfWork


def execute(work: UnitOfWork) -> UnitOfWork:
    config = work.config
    if not config.render:
        return work

    input_path = (
        work.get_step_output(StepName.Adjust)
        or work.get_step_output(StepName.Extract)
        or (config.render.data if config.render else None)
    )
    if input_path is None:
        return work
    work.set_step_paths(StepName.Render, input_path=input_path)

    if not work.ensure_path_exists(
        StepName.Render,
        input_path,
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

    return render(work)
