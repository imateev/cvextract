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
from .verifiers import get_verifier


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

    try:
        extractor: Optional[CVExtractor] = None
        if work.config.extract and work.config.extract.name:
            extractor = get_extractor(work.config.extract.name)
            if not extractor:
                work.add_error(
                    StepName.Extract, f"unknown extractor: {work.config.extract.name}"
                )
                extract_status = work.step_states.get(StepName.Extract)
                if extract_status:
                    extract_status.ConfiguredExecutorAvailable = False
                return work

        extract_work = extract_cv_data(work, extractor=extractor)
        extract_status = extract_work.step_states.get(StepName.Extract)
        output_path = extract_status.output if extract_status else None
        if output_path is None:
            extract_work.add_error(
                StepName.Extract, "extract: output JSON path is not set"
            )
            return extract_work
        if not output_path.exists():
            extract_work.add_error(
                StepName.Extract,
                f"extract: output JSON not found: {output_path}",
            )
            return extract_work
        return extract_work
    except Exception as e:
        if work.config.debug:
            LOG.error(traceback.format_exc())
            dump_body_sample(extract_status.input, n=30)
        work.add_error(StepName.Extract, f"exception: {type(e).__name__}")
        return work


def _roundtrip_compare(
    render_work: UnitOfWork,
    output_docx: Path,
    roundtrip_dir: Path,
    original_cv_path: Path,
) -> UnitOfWork:
    roundtrip_dir.mkdir(parents=True, exist_ok=True)
    roundtrip_json = roundtrip_dir / (output_docx.stem + ".json")
    roundtrip_work = UnitOfWork(
        config=render_work.config,
        initial_input=render_work.initial_input,
    )
    roundtrip_work.set_step_paths(
        StepName.Extract, input_path=output_docx, output_path=roundtrip_json
    )
    roundtrip_work = extract_cv_data(roundtrip_work)
    roundtrip_status = roundtrip_work.step_states.get(StepName.Extract)
    output_path = roundtrip_status.output if roundtrip_status else None
    if output_path is None or not output_path.exists():
        raise FileNotFoundError(
            f"roundtrip JSON not created: {output_path or roundtrip_json}"
        )
    verifier_name = "roundtrip-verifier"
    if render_work.config.render and render_work.config.render.verifier:
        verifier_name = render_work.config.render.verifier
    verifier = get_verifier(verifier_name)
    if not verifier:
        raise ValueError(f"unknown verifier: {verifier_name}")
    compare_work = replace(render_work, current_step=StepName.RoundtripComparer)
    compare_work.set_step_paths(
        StepName.RoundtripComparer,
        input_path=original_cv_path,
        output_path=roundtrip_json,
    )
    return verifier.verify(compare_work)


def _verify_roundtrip(
    render_work: UnitOfWork,
    original_cv_path: Path,
) -> UnitOfWork:
    output_docx = render_work.get_step_output(StepName.Render)
    if output_docx is None:
        return render_work

    input_path = (
        render_work.initial_input
        or render_work.get_step_input(StepName.Extract)
        or render_work.get_step_input(StepName.Render)
    )
    source_base = _resolve_source_base_for_render(render_work, input_path)
    rel_path = _resolve_parent(input_path, source_base)
    roundtrip_dir = render_work.config.workspace.verification_dir / rel_path
    try:
        _roundtrip_compare(
            render_work,
            output_docx,
            roundtrip_dir,
            original_cv_path,
        )
    except Exception as e:
        message = f"roundtrip comparer: {type(e).__name__}"
        LOG.warning("%s", message)
        render_work.add_error(StepName.RoundtripComparer, message)
        return render_work

    render_work.ensure_step_status(StepName.RoundtripComparer)
    return render_work


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
