"""Apply mode: Render JSON data to DOCX files."""

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
    render_and_verify,
    get_status_icons,
)


def run_apply_mode(
    inputs: List[Path], 
    template_path: Path, 
    target_dir: Path, 
    debug: bool, 
    adjust_url: Optional[str] = None, 
    openai_model: Optional[str] = None
) -> int:
    """
    Render JSON data to DOCX files using a template.
    
    Args:
        inputs: List of JSON file paths to process
        template_path: Path to DOCX template file
        target_dir: Output directory for rendered DOCX files
        debug: Whether to enable debug output
        adjust_url: Optional URL for customer-specific adjustments
        openai_model: Optional OpenAI model for adjustments
        
    Returns:
        Exit code (0 = success, 1 = failures occurred)
    """
    source_root = infer_source_root(inputs)
    documents_dir = target_dir / "documents"
    research_dir = target_dir / "research_data"
    documents_dir.mkdir(parents=True, exist_ok=True)
    research_dir.mkdir(parents=True, exist_ok=True)

    fully_ok = failed = 0

    for json_file in inputs:
        if json_file.suffix.lower() != ".json":
            continue

        rel_name = safe_relpath(json_file, source_root)
        rel_parent = json_file.parent.resolve().relative_to(source_root)
        out_docx_dir = documents_dir / rel_parent
        out_docx_dir.mkdir(parents=True, exist_ok=True)
        verify_dir = (target_dir / "verification_structured_data" / rel_parent)

        render_json = json_file
        # Optional: adjust JSON prior to rendering
        adjust_url = adjust_url or os.environ.get("CVEXTRACT_ADJUST_URL")
        openai_model = openai_model or os.environ.get("OPENAI_MODEL")
        skip_compare = False
        dry_run = bool(os.environ.get("CVEXTRACT_ADJUST_DRY_RUN"))
        if adjust_url:
            try:
                with json_file.open("r", encoding="utf-8") as f:
                    original = json.load(f)
                # Pass cache_path for research results (company-specific, not CV-specific)
                research_cache_dir = research_dir / rel_parent
                research_cache_dir.mkdir(parents=True, exist_ok=True)
                research_cache = research_cache_dir / _url_to_cache_filename(adjust_url)
                adjusted = adjust_for_customer(original, adjust_url, model=openai_model, cache_path=research_cache)
                skip_compare = adjusted != original
                render_json = out_docx_dir / (json_file.stem + ".adjusted.json")
                with render_json.open("w", encoding="utf-8") as wf:
                    json.dump(adjusted, wf, ensure_ascii=False, indent=2)
            except Exception:
                render_json = json_file
                skip_compare = False
        # If dry-run is enabled with adjustment, skip rendering
        if dry_run and adjust_url:
            apply_ok = None
            errs = []
            apply_warns = []
            compare_ok = None
        else:
            apply_ok, errs, apply_warns, compare_ok = render_and_verify(
                render_json,
                template_path,
                out_docx_dir,
                debug,
                skip_compare=skip_compare,
                roundtrip_dir=verify_dir,
            )
        
        x_icon, a_icon, c_icon = get_status_icons(False, bool(apply_warns), apply_ok, compare_ok)
        LOG.info("%s%s%s %s | %s", x_icon, a_icon, c_icon, rel_name, fmt_issues(errs, apply_warns))

        if apply_ok:
            fully_ok += 1
        else:
            failed += 1

    total = fully_ok + failed
    LOG.info(
        "📊 Apply summary: %d successful, %d failed (total %d). Output in: %s",
        fully_ok, failed, total, documents_dir
    )

    return 0 if failed == 0 else 1
