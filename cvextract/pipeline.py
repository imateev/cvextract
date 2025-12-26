"""
Batch pipeline runners.

Implements the CLI modes (extract / apply / extract+apply) over a list of input
files, keeps folder structure in the output, and logs a one-line result per file
plus a final summary.
"""

from __future__ import annotations

import json
import os
import traceback
from pathlib import Path
from typing import List, Optional
import os

from .logging_utils import LOG, fmt_issues
from .docx_utils import dump_body_sample
from .pipeline_highlevel import process_single_docx
from .render import render_from_json
from .shared import VerificationResult
from .verification import verify_extracted_data, compare_data_structures
from .customer_adjust import adjust_for_customer

# ------------------------- Helper -------------------------

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

# ------------------------- Processing Helpers -------------------------

def _extract_single(docx_file: Path, out_json: Path, debug: bool) -> tuple[bool, List[str], List[str]]:
    """Extract and verify a single DOCX. Returns (ok, errors, warnings)."""
    try:
        data = process_single_docx(docx_file, out=out_json)
        result = verify_extracted_data(data)
        return result.ok, result.errors, result.warnings
    except Exception as e:
        if debug:
            LOG.error(traceback.format_exc())
            dump_body_sample(docx_file, n=30)
        return False, [f"exception: {type(e).__name__}"], []

def _render_and_verify(json_path: Path, template_path: Path, out_dir: Path, debug: bool, *, skip_compare: bool = False, roundtrip_dir: Optional[Path] = None) -> tuple[bool, List[str], List[str], Optional[bool]]:
    """
    Render a single JSON to DOCX, extract round-trip JSON, and compare structures.
    Returns (ok, errors, warnings, compare_ok).
    compare_ok is None if comparison did not run (e.g., render error).
    """
    try:
        out_docx = render_from_json(json_path, template_path, out_dir)

        # Skip compare when explicitly requested by caller
        if skip_compare:
            return True, [], [], None

        # Round-trip extraction from rendered DOCX
        if roundtrip_dir:
            roundtrip_dir.mkdir(parents=True, exist_ok=True)
            roundtrip_json = roundtrip_dir / (out_docx.stem + ".json")
        else:
            roundtrip_json = out_docx.with_suffix(".json")
        roundtrip_data = process_single_docx(out_docx, out=roundtrip_json)

        with json_path.open("r", encoding="utf-8") as f:
            original_data = json.load(f)

        cmp = compare_data_structures(original_data, roundtrip_data)
        if not debug and roundtrip_dir is None:
            try:
                roundtrip_json.unlink(missing_ok=True)
            except Exception:
                pass

        if cmp.ok:
            return True, [], cmp.warnings, True
        return False, cmp.errors, cmp.warnings, False
    except Exception as e:
        if debug:
            LOG.error(traceback.format_exc())
        return False, [f"render: {type(e).__name__}"], [], None

def _get_status_icons(extract_ok: bool, has_warns: bool, apply_ok: Optional[bool], compare_ok: Optional[bool]) -> tuple[str, str, str]:
    """Generate status icons for extract, apply, and roundtrip compare steps."""
    if extract_ok and has_warns:
        x_icon = "⚠️ "
    elif extract_ok:
        x_icon = "🟢"
    else:
        x_icon = "❌"
    
    if apply_ok is None:
        a_icon = "➖"
    else:
        a_icon = "✅" if apply_ok else "❌"

    if compare_ok is None:
        c_icon = "➖"
    else:
        c_icon = "✅" if compare_ok else "⚠️ "

    return x_icon, a_icon, c_icon

def _categorize_result(extract_ok: bool, has_warns: bool, apply_ok: Optional[bool]) -> tuple[int, int, int]:
    """Categorize result into (fully_ok, partial_ok, failed) counts."""
    if not extract_ok:
        return 0, 0, 1
    if apply_ok is False or (apply_ok is None and has_warns):
        return 0, 1, 0
    if has_warns:
        return 0, 1, 0
    return 1, 0, 0
    
# ------------------------- Modes -------------------------

def run_extract_mode(inputs: List[Path], target_dir: Path, strict: bool, debug: bool) -> int:
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

        extract_ok, errs, warns = _extract_single(docx_file, out_json, debug)
        
        x_icon, a_icon, c_icon = _get_status_icons(extract_ok, bool(warns), None, None)
        LOG.info("%s%s%s %s | %s", x_icon, a_icon, c_icon, rel_name, fmt_issues(errs, warns))

        full, part, fail = _categorize_result(extract_ok, bool(warns), None)
        fully_ok += full
        partial_ok += part
        failed += fail

    total = fully_ok + partial_ok + failed
    LOG.info(
        "📊 Extract summary: %d fully successful, %d partially successful, %d failed (total %d). JSON in: %s", 
        fully_ok, partial_ok, failed, total, json_dir
    )

    return 0 if failed == 0 else 1

def run_extract_apply_mode(inputs: List[Path], template_path: Path, target_dir: Path, strict: bool, debug: bool, adjust_url: Optional[str] = None, openai_model: Optional[str] = None) -> int:
    source_root = infer_source_root(inputs)
    json_dir = target_dir / "structured_data"
    documents_dir = target_dir / "documents"
    json_dir.mkdir(parents=True, exist_ok=True)
    documents_dir.mkdir(parents=True, exist_ok=True)

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
        extract_ok, errs, warns = _extract_single(docx_file, out_json, debug)
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
                    adjusted = adjust_for_customer(original, adjust_url, model=openai_model)
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
                apply_ok, render_errs, apply_warns, compare_ok = _render_and_verify(
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

        x_icon, a_icon, c_icon = _get_status_icons(extract_ok, bool(combined_warns), apply_ok, compare_ok)
        LOG.info("%s%s%s %s | %s", x_icon, a_icon, c_icon, rel_name, fmt_issues(errs, combined_warns))

        full, part, fail = _categorize_result(extract_ok, bool(combined_warns), apply_ok)
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

def run_apply_mode(inputs: List[Path], template_path: Path, target_dir: Path, debug: bool, adjust_url: Optional[str] = None, openai_model: Optional[str] = None) -> int:
    source_root = infer_source_root(inputs)
    documents_dir = target_dir / "documents"
    documents_dir.mkdir(parents=True, exist_ok=True)

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
                adjusted = adjust_for_customer(original, adjust_url, model=openai_model)
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
            apply_ok, errs, apply_warns, compare_ok = _render_and_verify(
                render_json,
                template_path,
                out_docx_dir,
                debug,
                skip_compare=skip_compare,
                roundtrip_dir=verify_dir,
            )
        
        x_icon, a_icon, c_icon = _get_status_icons(False, bool(apply_warns), apply_ok, compare_ok)
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
