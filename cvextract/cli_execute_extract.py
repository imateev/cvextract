"""
Step 1: Extract stage execution.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from .pipeline_helpers import extract_single
from .shared import StepName, UnitOfWork
from .verifiers import get_verifier


def execute(work: UnitOfWork) -> UnitOfWork:
    config = work.config
    if not config.extract:
        return work

    input_path = work.input
    if config.input_dir:
        source_base = config.input_dir.resolve()
    else:
        source_base = (
            config.extract.source.parent.resolve()
            if config.extract.source.is_file()
            else config.extract.source.resolve()
        )

    try:
        rel_path = input_path.parent.resolve().relative_to(source_base)
    except ValueError:
        rel_path = Path(".")

    output_path = config.extract.output or (
        config.workspace.json_dir / rel_path / f"{input_path.stem}.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    work = replace(work, output=output_path)
    work = extract_single(work)
    if not work.has_no_errors(StepName.Extract):
        return replace(work, input=work.output)

    skip_verify = bool(
        config.skip_all_verify
        or (config.extract and config.extract.skip_verify)
    )
    if skip_verify:
        return replace(work, input=work.output)

    if not work.output or not work.output.exists():
        work.add_error(
            StepName.Extract, "extract: output JSON not found for verification"
        )
        return replace(work, input=work.output)

    verifier_name = "private-internal-verifier"
    if config.extract and config.extract.verifier:
        verifier_name = config.extract.verifier
    verifier = get_verifier(verifier_name)
    if not verifier:
        work.add_error(StepName.Extract, f"unknown verifier: {verifier_name}")
        return replace(work, input=work.output)

    work.ensure_step_status(StepName.Extract)
    try:
        result = verifier.verify(work)
    except Exception as e:
        work.add_error(
            StepName.Extract, f"extract: verify failed ({type(e).__name__})"
        )
        return replace(work, input=work.output)
    for err in result.errors:
        work.add_error(StepName.Extract, err)
    for warn in result.warnings:
        work.add_warning(StepName.Extract, warn)

    return replace(work, input=work.output)
