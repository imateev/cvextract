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

import traceback
from dataclasses import replace
from pathlib import Path
from typing import List, Optional
import os

from .logging_utils import LOG
from .extractors.docx_utils import dump_body_sample
from .extractors import CVExtractor, get_extractor
from .shared import StepName, StepStatus, UnitOfWork
from .pipeline_highlevel import process_single_docx, render_cv_data
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


def extract_single(work: UnitOfWork) -> UnitOfWork:
    """
    Extract and verify a single file. Returns a UnitOfWork copy with results.
    
    Args:
        work: UnitOfWork describing the extraction inputs
    
    Returns:
        UnitOfWork copy with extract StepStatus populated
    """
    statuses = dict(work.step_statuses)
    statuses[StepName.Extract] = StepStatus(step=StepName.Extract)
    work = replace(work, step_statuses=statuses)
    try:
        extractor: Optional[CVExtractor] = None
        if work.config.extract and work.config.extract.name:
            extractor = get_extractor(work.config.extract.name)
            if not extractor:
                work.AddError(StepName.Extract, f"unknown extractor: {work.config.extract.name}")
                extract_status = work.step_statuses.get(StepName.Extract)
                if extract_status:
                    extract_status.ConfiguredExecutorAvailable = False
                return work

        data = process_single_docx(work.input, out=work.output, extractor=extractor)
        verifier = get_verifier("private-internal-verifier")
        result = verifier.verify(data)
        for err in result.errors:
            work.AddError(StepName.Extract, err)
        for warn in result.warnings:
            work.AddWarning(StepName.Extract, warn)
        return work
    except Exception as e:
        if work.config.debug:
            LOG.error(traceback.format_exc())
            dump_body_sample(work.input, n=30)
        work.AddError(StepName.Extract, f"exception: {type(e).__name__}")
        return work


def render_and_verify(work: UnitOfWork) -> tuple[bool, List[str], List[str], Optional[bool]]:
    """
    Render a single JSON to DOCX, extract round-trip JSON, and compare structures.
    
    Args:
        work: UnitOfWork with config, output JSON path, and initial input path
    
    Returns:
        Tuple of (ok, errors, warnings, compare_ok).
        compare_ok is None if comparison did not run (e.g., render error).
    """
    import json
    
    if not work.config.apply:
        return False, ["render: missing apply configuration"], [], None

    json_path = work.output
    template_path = work.config.apply.template
    input_path = work.initial_input or work.input
    debug = work.config.debug
    skip_compare = not work.config.should_compare
    if work.config.extract and work.config.extract.name == "openai-extractor":
        skip_compare = True

    if work.config.input_dir:
        source_base = work.config.input_dir.resolve()
    else:
        source = None
        if work.config.extract:
            source = work.config.extract.source
        elif work.config.apply and work.config.apply.data:
            source = work.config.apply.data
        elif work.config.adjust and work.config.adjust.data:
            source = work.config.adjust.data
        if source is not None:
            source_base = source.parent.resolve() if source.is_file() else source.resolve()
        else:
            source_base = input_path.parent.resolve()

    try:
        rel_path = input_path.parent.resolve().relative_to(source_base)
    except Exception:
        rel_path = Path(".")

    output_docx = work.config.apply.output or (
        work.config.workspace.documents_dir / rel_path / f"{input_path.stem}_NEW.docx"
    )
    output_docx.parent.mkdir(parents=True, exist_ok=True)
    roundtrip_dir = work.config.workspace.verification_dir / rel_path

    try:
        # Load CV data from JSON
        with json_path.open("r", encoding="utf-8") as f:
            cv_data = json.load(f)
        
        # Render using the new renderer interface (with explicit output path)
        render_cv_data(cv_data, template_path, output_docx)

        # Skip compare when explicitly requested by caller
        if skip_compare:
            return True, [], [], None

        # Round-trip extraction from rendered DOCX
        roundtrip_dir.mkdir(parents=True, exist_ok=True)
        roundtrip_json = roundtrip_dir / (output_docx.stem + ".json")
        roundtrip_data = process_single_docx(output_docx, out=roundtrip_json)

        original_data = cv_data

        verifier = get_verifier("roundtrip-verifier")
        cmp = verifier.verify(original_data, target_data=roundtrip_data)
        if cmp.ok:
            return True, [], cmp.warnings, True
        return False, cmp.errors, cmp.warnings, False
    except Exception as e:
        if debug:
            LOG.error(traceback.format_exc())
        return False, [f"render: {type(e).__name__}"], [], None


def categorize_result(extract_ok: bool, has_warns: bool, apply_ok: Optional[bool]) -> tuple[int, int, int]:
    """Categorize result into (fully_ok, partial_ok, failed) counts."""
    if not extract_ok:
        return 0, 0, 1
    if apply_ok is False or (apply_ok is None and has_warns):
        return 0, 1, 0
    if has_warns:
        return 0, 1, 0
    return 1, 0, 0
