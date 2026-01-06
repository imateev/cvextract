"""
Step 1: Extract stage execution.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from .pipeline_helpers import extract_single
from .shared import UnitOfWork


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
    return replace(work, input=work.output)
