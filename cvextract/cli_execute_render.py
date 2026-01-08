"""
Step 3: Render/Verify stage execution.
"""

from __future__ import annotations

from .pipeline_helpers import _verify_roundtrip, render
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

    render_work = render(work)
    render_status = render_work.step_statuses.get(StepName.Render)
    if render_status and not render_status.ok:
        return render_work

    skip_compare = not config.should_compare
    if config.extract and config.extract.name == "openai-extractor":
        skip_compare = True

    if skip_compare:
        return render_work

    original_cv_path = work.output
    if original_cv_path is None:
        render_work.add_error(
            StepName.RoundtripComparer, "render: input JSON path is not set"
        )
        return render_work

    return _verify_roundtrip(render_work, original_cv_path)
