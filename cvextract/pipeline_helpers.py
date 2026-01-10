"""
Helper functions for batch pipeline processing.

Provides utilities for:
- Source root inference
- Path handling
- Single file extraction and rendering
- Status formatting
- Result categorization
"""

from __future__ import annotations

import os
import traceback
from dataclasses import replace
from pathlib import Path
from typing import List, Optional

from .extractors import CVExtractor, DocxCVExtractor, get_extractor
from .extractors.docx_utils import dump_body_sample
from .logging_utils import LOG
from .renderers import get_renderer
from .shared import StepName, StepStatus, UnitOfWork


def infer_source_root(inputs: List[Path]) -> Path:
    """
    Infer the root directory of the batch so we can preserve folder structure
    in output without passing source explicitly.
    - If a single file: use its parent as root.
    - If multiple files: use common path of their parent folders.
    """
    if not inputs:
        return Path(".").resolve()
    if len(inputs) == 1:
        return inputs[0].parent.resolve()
    parents = [p.parent.resolve() for p in inputs]
    return Path(os.path.commonpath([str(p) for p in parents])).resolve()


def safe_relpath(p: Path, root: Path) -> str:
    """Best-effort relative path for nicer logging."""
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return p.name


def _resolve_extractor_names(work: UnitOfWork) -> List[str]:
    if not work.config.extract:
        return []
    raw_name = work.config.extract.name or ""
    names = [name.strip() for name in raw_name.split(",") if name.strip()]
    if not names:
        names = ["default_docx_cv_extractor"]
    if names == ["default_docx_cv_extractor"]:
        names.append("openai-extractor")
    return names


def extract_cv_data(
    work: UnitOfWork, extractor: Optional[CVExtractor] = None
) -> UnitOfWork:
    """
    Extract CV structure from a source file using the specified extractor.

    Args:
        work: UnitOfWork containing Extract step input/output paths.
        extractor: CVExtractor instance to use. If None, uses default DocxCVExtractor

    Returns:
        UnitOfWork with output JSON populated.
    """
    if extractor is None:
        extractor = DocxCVExtractor()
    return extractor.extract(work)


def render_cv_data(work: UnitOfWork) -> UnitOfWork:
    """
    Render CV data to a DOCX file using the default renderer.

    This function uses the default renderer from the pluggable
    renderer architecture.

    Args:
        work: UnitOfWork containing Render step input/output paths.

    Returns:
        UnitOfWork with rendered output populated
    """
    renderer = get_renderer("private-internal-renderer")
    if not renderer:
        raise ValueError("Default renderer 'private-internal-renderer' not found")
    return renderer.render(work)


def _resolve_source_base_for_render(work: UnitOfWork, input_path: Path) -> Path:
    if work.config.input_dir:
        return work.config.input_dir.resolve()

    source = None
    if work.config.extract:
        source = work.config.extract.source
    elif work.config.render and work.config.render.data:
        source = work.config.render.data
    elif work.config.adjust and work.config.adjust.data:
        source = work.config.adjust.data

    if source is not None:
        return source.parent.resolve() if source.is_file() else source.resolve()

    return input_path.parent.resolve()


def _resolve_parent(input_path, source_base):
    try:
        rel_path = input_path.parent.resolve().relative_to(source_base)
    except Exception:
        rel_path = Path(".")
    return rel_path


def _render_docx(work: UnitOfWork) -> UnitOfWork:
    if not work.config.render:
        work.add_error(StepName.Render, "render: missing render configuration")
        return work

    render_status = work.ensure_step_status(StepName.Render)
    if render_status.input is None:
        work.add_error(StepName.Render, "render: input JSON path is not set")
        return work

    input_path = (
        work.initial_input
        or work.get_step_input(StepName.Extract)
        or render_status.input
    )
    source_base = _resolve_source_base_for_render(work, input_path)
    rel_path = _resolve_parent(input_path, source_base)
    output_docx = prepare_output_path(work, input_path, rel_path)
    render_work = replace(work)
    render_work.set_step_paths(StepName.Render, output_path=output_docx)

    try:
        render_work = render_cv_data(render_work)
    except Exception as e:
        message = f"render: {type(e).__name__}"
        LOG.warning("%s", message)
        render_work.add_warning(StepName.Render, message)
        return render_work

    render_work.ensure_step_status(StepName.Render)
    return render_work


def extract_single(work: UnitOfWork) -> UnitOfWork:
    """
    Extract a single file. Returns a UnitOfWork copy with results.

    Args:
        work: UnitOfWork describing the extraction inputs

    Returns:
        UnitOfWork copy with extract StepStatus populated
    """
    statuses = dict(work.step_states)
    previous_status = statuses.get(StepName.Extract)
    extract_status = StepStatus(step=StepName.Extract)
    if previous_status:
        extract_status.input = previous_status.input
        extract_status.output = previous_status.output
    statuses[StepName.Extract] = extract_status
    work = replace(work, step_states=statuses)
    extract_status = work.step_states[StepName.Extract]
    if extract_status.input is None:
        work.add_error(StepName.Extract, "extract: input file path is not set")
        return work
    if not work.ensure_path_exists(
        StepName.Extract, extract_status.input, "input file", must_be_file=True
    ):
        return work
    if extract_status.output is None:
        work.add_error(StepName.Extract, "extract: output JSON path is not set")
        return work

    extractor_names = _resolve_extractor_names(work)
    base_input = extract_status.input
    base_output = extract_status.output
    last_errors: List[str] = []
    last_work = work
    had_extractor = False

    for extractor_name in extractor_names:
        attempt_status = StepStatus(step=StepName.Extract)
        attempt_status.input = base_input
        attempt_status.output = base_output
        attempt_states = dict(work.step_states)
        attempt_states[StepName.Extract] = attempt_status
        attempt_work = replace(work, step_states=attempt_states)

        extractor = get_extractor(extractor_name)
        if not extractor:
            last_errors.append(f"unknown extractor: {extractor_name}")
            last_work = attempt_work
            continue
        had_extractor = True

        try:
            extract_work = extract_cv_data(attempt_work, extractor=extractor)
            attempt_result_status = extract_work.step_states.get(StepName.Extract)
            output_path = (
                attempt_result_status.output if attempt_result_status else None
            )
            if output_path is None:
                extract_work.add_error(
                    StepName.Extract, "extract: output JSON path is not set"
                )
            elif not output_path.exists():
                extract_work.add_error(
                    StepName.Extract,
                    f"extract: output JSON not found: {output_path}",
                )
        except Exception as e:
            extract_work = attempt_work
            if work.config.debug:
                LOG.error(traceback.format_exc())
                dump_body_sample(attempt_status.input, n=30)
            extract_work.add_error(StepName.Extract, f"exception: {type(e).__name__}")

        if extract_work.has_no_errors(StepName.Extract):
            return extract_work

        result_status = extract_work.step_states.get(StepName.Extract)
        if result_status:
            last_errors.extend(result_status.errors)
        last_work = extract_work

    if last_errors:
        final_status = last_work.ensure_step_status(StepName.Extract)
        final_status.errors = last_errors
        if not had_extractor:
            final_status.ConfiguredExecutorAvailable = False
    return last_work


def render(work: UnitOfWork) -> UnitOfWork:
    """
    Render a single JSON to DOCX.

    Args:
        work: UnitOfWork with render configuration and input/output paths

    Returns:
        UnitOfWork with Render status populated.
    """
    return _render_docx(work)


def prepare_output_path(work: UnitOfWork, input_path: Path, rel_path: Path) -> Path:
    if work.config.render and work.config.render.output:
        output_docx = work.config.render.output
    else:
        output_docx = (
            work.config.workspace.documents_dir
            / rel_path
            / f"{input_path.stem}_NEW.docx"
        )
    output_docx.parent.mkdir(parents=True, exist_ok=True)
    return output_docx


def categorize_result(
    extract_ok: bool, has_warns: bool, apply_ok: Optional[bool]
) -> tuple[int, int, int]:
    """Categorize result into (fully_ok, partial_ok, failed) counts."""
    if not extract_ok:
        return 0, 0, 1
    if apply_ok is False or (apply_ok is None and has_warns):
        return 0, 1, 0
    if has_warns:
        return 0, 1, 0
    return 1, 0, 0
