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
from pathlib import Path
from typing import List, Optional
import os

from .logging_utils import LOG
from .extractors.docx_utils import dump_body_sample
from .pipeline_highlevel import process_single_docx, render_cv_data
from .verifiers import ExtractedDataVerifier, ComparisonVerifier


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


def extract_single(docx_file: Path, out_json: Path, debug: bool) -> tuple[bool, List[str], List[str]]:
    """Extract and verify a single DOCX. Returns (ok, errors, warnings)."""
    try:
        data = process_single_docx(docx_file, out=out_json)
        result = ExtractedDataVerifier().verify(data)
        return result.ok, result.errors, result.warnings
    except Exception as e:
        if debug:
            LOG.error(traceback.format_exc())
            dump_body_sample(docx_file, n=30)
        return False, [f"exception: {type(e).__name__}"], []


def render_and_verify(
    json_path: Path, 
    template_path: Path, 
    out_dir: Path, 
    debug: bool, 
    *, 
    skip_compare: bool = False, 
    roundtrip_dir: Optional[Path] = None
) -> tuple[bool, List[str], List[str], Optional[bool]]:
    """
    Render a single JSON to DOCX, extract round-trip JSON, and compare structures.
    Returns (ok, errors, warnings, compare_ok).
    compare_ok is None if comparison did not run (e.g., render error).
    """
    import json
    
    try:
        # Load CV data from JSON
        with json_path.open("r", encoding="utf-8") as f:
            cv_data = json.load(f)
        
        # Determine output path
        out_docx = out_dir / f"{json_path.stem}_NEW.docx"
        
        # Render using the new renderer interface
        render_cv_data(cv_data, template_path, out_docx)

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

        original_data = cv_data

        cmp = ComparisonVerifier().verify(original_data, target_data=roundtrip_data)
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


def get_status_icons(extract_ok: bool, has_warns: bool, apply_ok: Optional[bool], compare_ok: Optional[bool]) -> tuple[str, str, str]:
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


def categorize_result(extract_ok: bool, has_warns: bool, apply_ok: Optional[bool]) -> tuple[int, int, int]:
    """Categorize result into (fully_ok, partial_ok, failed) counts."""
    if not extract_ok:
        return 0, 0, 1
    if apply_ok is False or (apply_ok is None and has_warns):
        return 0, 1, 0
    if has_warns:
        return 0, 1, 0
    return 1, 0, 0
