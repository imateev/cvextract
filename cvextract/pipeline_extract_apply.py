"""Extract+Apply mode: Extract from DOCX and render to new DOCX in one pass."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional

from .logging_utils import LOG, fmt_issues
from .ml_adjustment import adjust_for_customer, _url_to_cache_filename
from .pipeline_helpers import (
    infer_source_root,
    safe_relpath,
    extract_single,
    render_and_verify,
    get_status_icons,
    categorize_result,
)


def run_extract_apply_mode(
    inputs: List[Path], 
    template_path: Path, 
    target_dir: Path, 
    strict: bool, 
    debug: bool, 
    adjust_url: Optional[str] = None, 
    openai_model: Optional[str] = None
) -> int:
    """
    Extract structured data from DOCX files and render to new DOCX files.
    
    Args:
        inputs: List of DOCX file paths to process
        template_path: Path to DOCX template file
        target_dir: Output directory for JSON and DOCX files
        strict: Whether to enforce strict validation (warnings = failure)
        debug: Whether to enable debug output
        adjust_url: Optional URL for customer-specific adjustments
        openai_model: Optional OpenAI model for adjustments
        
    Returns:
        Exit code (0 = success, 1 = failures, 2 = strict mode warnings)
    """
    source_root = infer_source_root(inputs)
    json_dir = target_dir / "structured_data"
    documents_dir = target_dir / "documents"
    research_dir = target_dir / "research_data"
    json_dir.mkdir(parents=True, exist_ok=True)
    documents_dir.mkdir(parents=True, exist_ok=True)
    research_dir.mkdir(parents=True, exist_ok=True)

    fully_ok = partial_ok = failed = 0
    had_warning = False

    for docx_file in inputs:
        if docx_file.suffix.lower() != ".docx":
            continue

        rel_name = safe_relpath(docx_file, source_root)
        rel_parent = docx_file.parent.resolve().relative_to(source_root)
        out_json = json_dir / rel_parent / f"{docx_file.stem}.json"
        out_json.parent.mkdir(parents=True, exist_ok=True)

        # Extract
        extract_ok, errs, warns = extract_single(docx_file, out_json, debug)
        if warns:
            had_warning = True

        # Render (only if extraction succeeded)
        apply_ok = None
        compare_ok: Optional[bool] = None
        apply_warns: List[str] = []
        if extract_ok:
            out_docx_dir = documents_dir / rel_parent
            out_docx_dir.mkdir(parents=True, exist_ok=True)
            verify_dir = (target_dir / "verification_structured_data" / rel_parent)
            render_json = out_json
            # Optional: adjust JSON for customer before rendering
            adjust_url = adjust_url or os.environ.get("CVEXTRACT_ADJUST_URL")
            openai_model = openai_model or os.environ.get("OPENAI_MODEL")
            skip_compare = False
            dry_run = bool(os.environ.get("CVEXTRACT_ADJUST_DRY_RUN"))
            if adjust_url:
                try:
                    with out_json.open("r", encoding="utf-8") as f:
                        original = json.load(f)
                    # Pass cache_path for research results (company-specific, not CV-specific)
                    research_cache_dir = research_dir / rel_parent
                    research_cache_dir.mkdir(parents=True, exist_ok=True)
                    research_cache = research_cache_dir / _url_to_cache_filename(adjust_url)
                    adjusted = adjust_for_customer(original, adjust_url, model=openai_model, cache_path=research_cache)
                    # Skip compare only if adjustment produced a different JSON
                    skip_compare = adjusted != original
                    render_json = out_json.with_name(out_json.stem + ".adjusted.json")
                    render_json.parent.mkdir(parents=True, exist_ok=True)
                    with render_json.open("w", encoding="utf-8") as wf:
                        json.dump(adjusted, wf, ensure_ascii=False, indent=2)
                except Exception:
                    # If adjust fails, proceed with original JSON
                    render_json = out_json
                    skip_compare = False
            # If dry-run is enabled with adjustment, skip rendering
            if dry_run and adjust_url:
                apply_ok = None
                compare_ok = None
                render_errs = []
            else:
                apply_ok, render_errs, apply_warns, compare_ok = render_and_verify(
                    render_json,
                    template_path,
                    out_docx_dir,
                    debug,
                    skip_compare=skip_compare,
                    roundtrip_dir=verify_dir,
                )
            errs = render_errs
            if apply_warns:
                had_warning = True

        combined_warns = (warns or []) + (apply_warns or [])

        x_icon, a_icon, c_icon = get_status_icons(extract_ok, bool(combined_warns), apply_ok, compare_ok)
        LOG.info("%s%s%s %s | %s", x_icon, a_icon, c_icon, rel_name, fmt_issues(errs, combined_warns))

        full, part, fail = categorize_result(extract_ok, bool(combined_warns), apply_ok)
        fully_ok += full
        partial_ok += part
        failed += fail

    total = fully_ok + partial_ok + failed
    LOG.info(
        "📊 Extract+Apply summary: %d fully successful, %d partially successful, %d failed (total %d). JSON: %s | DOCX: %s",
        fully_ok, partial_ok, failed, total, json_dir, documents_dir
    )

    if strict and had_warning:
        LOG.error("Strict mode enabled: warnings treated as failure.")
        return 2
    return 0 if (failed == 0 and partial_ok == 0) else 1
