"""
Step 3: Render/Verify stage execution.
"""

from __future__ import annotations

from .pipeline_helpers import render_and_verify
from .shared import StepName, UnitOfWork


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

    return render_and_verify(work)
