"""Extract mode: Extract structured data from DOCX files."""

from __future__ import annotations

from pathlib import Path
from typing import List

from .logging_utils import LOG, fmt_issues
from .pipeline_helpers import (
    infer_source_root,
    safe_relpath,
    extract_single,
    get_status_icons,
    categorize_result,
)


def run_extract_mode(inputs: List[Path], target_dir: Path, strict: bool, debug: bool) -> int:
    """
    Extract structured data from DOCX files.
    
    Args:
        inputs: List of DOCX file paths to process
        target_dir: Output directory for JSON files
        strict: Whether to enforce strict validation
        debug: Whether to enable debug output
        
    Returns:
        Exit code (0 = success, 1 = failures occurred)
    """
    source_root = infer_source_root(inputs)
    json_dir = target_dir / "structured_data"
    json_dir.mkdir(parents=True, exist_ok=True)

    fully_ok = partial_ok = failed = 0

    for docx_file in inputs:
        if docx_file.suffix.lower() != ".docx":
            continue

        rel_name = safe_relpath(docx_file, source_root)
        rel_parent = docx_file.parent.resolve().relative_to(source_root)
        out_json = json_dir / rel_parent / f"{docx_file.stem}.json"
        out_json.parent.mkdir(parents=True, exist_ok=True)

        extract_ok, errs, warns = extract_single(docx_file, out_json, debug)
        
        x_icon, a_icon, c_icon = get_status_icons(extract_ok, bool(warns), None, None)
        LOG.info("%s%s%s %s | %s", x_icon, a_icon, c_icon, rel_name, fmt_issues(errs, warns))

        full, part, fail = categorize_result(extract_ok, bool(warns), None)
        fully_ok += full
        partial_ok += part
        failed += fail

    total = fully_ok + partial_ok + failed
    LOG.info(
        "📊 Extract summary: %d fully successful, %d partially successful, %d failed (total %d). JSON in: %s", 
        fully_ok, partial_ok, failed, total, json_dir
    )

    return 0 if failed == 0 else 1
