"""
Batch pipeline runners.

Implements the CLI modes (extract / apply / extract+apply) over a list of input
files, keeps folder structure in the output, and logs a one-line result per file
plus a final summary.
"""

from __future__ import annotations

import os
import traceback
from pathlib import Path
from typing import List, Optional

from .logging_utils import LOG, fmt_issues
from .docx_utils import dump_body_sample
from .pipeline_highlevel import process_single_docx
from .render import render_from_json
from .shared import VerificationResult

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

def verify_extracted_data(data: dict) -> VerificationResult:
    """
    Verify extracted CV data for completeness and validity.
    Returns issues without logging (so we can keep one log line per file).
    """
    from typing import Dict, List
    errs: List[str] = []
    warns: List[str] = []

    identity = data.get("identity", {}) or {}
    if not identity.get("title") or not identity.get("full_name") or not identity.get("first_name") or not identity.get("last_name"):
        errs.append("identity")

    sidebar = data.get("sidebar", {}) or {}
    if not any(sidebar.get(section) for section in sidebar):
        errs.append("sidebar")

    expected_sidebar = ["languages", "tools", "industries", "spoken_languages", "academic_background"]
    missing_sidebar = [s for s in expected_sidebar if not sidebar.get(s)]
    if missing_sidebar:
        warns.append("missing sidebar: " + ", ".join(missing_sidebar))

    experiences = data.get("experiences", []) or []
    if not experiences:
        errs.append("experiences_empty")

    has_any_bullets = False
    has_any_environment = False
    issue_set = set()
    for exp in experiences:
        heading = (exp.get("heading") or "").strip()
        desc = (exp.get("description") or "").strip()
        bullets = exp.get("bullets") or []
        env = exp.get("environment")
        if not heading:
            issue_set.add("missing heading")
        if not desc:
            issue_set.add("missing description")
        if bullets:
            has_any_bullets = True
        if env:
            has_any_environment = True
        if env is not None and not isinstance(env, list):
            warns.append("invalid environment format")

    if not has_any_bullets and not has_any_environment:
        warns.append("no bullets or environment in any experience")

    if issue_set:
        warns.append("incomplete: " + "; ".join(sorted(issue_set)))

    ok = not errs
    return VerificationResult(ok=ok, errors=errs, warnings=warns)

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

def _render_single(json_path: Path, template_path: Path, out_dir: Path, debug: bool) -> tuple[bool, List[str]]:
    """Render a single JSON to DOCX. Returns (ok, errors)."""
    try:
        render_from_json(json_path, template_path, out_dir)
        return True, []
    except Exception as e:
        if debug:
            LOG.error(traceback.format_exc())
        return False, [f"render: {type(e).__name__}"]

def _get_status_icons(extract_ok: bool, has_warns: bool, apply_ok: Optional[bool]) -> tuple[str, str]:
    """Generate status icons for extract and apply steps."""
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
    
    return x_icon, a_icon

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
        
        x_icon, a_icon = _get_status_icons(extract_ok, bool(warns), None)
        LOG.info("%s%s %s | %s", x_icon, a_icon, rel_name, fmt_issues(errs, warns))

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

def run_extract_apply_mode(inputs: List[Path], template_path: Path, target_dir: Path, strict: bool, debug: bool) -> int:
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
        if extract_ok:
            out_docx_dir = documents_dir / rel_parent
            out_docx_dir.mkdir(parents=True, exist_ok=True)
            apply_ok, render_errs = _render_single(out_json, template_path, out_docx_dir, debug)
            errs = render_errs

        x_icon, a_icon = _get_status_icons(extract_ok, bool(warns), apply_ok)
        LOG.info("%s%s %s | %s", x_icon, a_icon, rel_name, fmt_issues(errs, warns))

        full, part, fail = _categorize_result(extract_ok, bool(warns), apply_ok)
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

def run_apply_mode(inputs: List[Path], template_path: Path, target_dir: Path, debug: bool) -> int:
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

        apply_ok, errs = _render_single(json_file, template_path, out_docx_dir, debug)
        
        x_icon, a_icon = _get_status_icons(False, False, apply_ok)
        LOG.info("%s%s %s | %s", x_icon, a_icon, rel_name, fmt_issues(errs, []))

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
