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
from typing import List, Optional, Union
import os

from .logging_utils import LOG
from .extractors.docx_utils import dump_body_sample
from .extractors import CVExtractor
from .pipeline_highlevel import process_single_docx, render_cv_data
from .verifiers import get_verifier
from .run_input import RunInput


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


def extract_single(
    source: Union[Path, RunInput], 
    out_json: Path, 
    debug: bool,
    extractor: Optional[CVExtractor] = None
) -> tuple[bool, List[str], List[str]]:
    """
    Extract and verify a single file. Returns (ok, errors, warnings).
    
    Args:
        source: Path or RunInput to source file to extract
        out_json: Output JSON path
        debug: Enable debug logging
        extractor: Optional CVExtractor instance to use
    
    Returns:
        Tuple of (success, errors, warnings)
    """
    # Handle both Path and RunInput
    source_file = source.file_path if isinstance(source, RunInput) else source
    
    try:
        data = process_single_docx(source, out=out_json, extractor=extractor)
        verifier = get_verifier("private-internal-verifier")
        result = verifier.verify(data)
        return result.ok, result.errors, result.warnings
    except Exception as e:
        if debug:
            LOG.error(traceback.format_exc())
            dump_body_sample(source_file, n=30)
        return False, [f"exception: {type(e).__name__}"], []


def render_and_verify(
    json_path: Path, 
    template_path: Path, 
    output_docx: Path, 
    debug: bool, 
    *, 
    skip_compare: bool = False, 
    roundtrip_dir: Optional[Path] = None
) -> tuple[bool, List[str], List[str], Optional[bool]]:
    """
    Render a single JSON to DOCX, extract round-trip JSON, and compare structures.
    
    Args:
        json_path: Path to input JSON file
        template_path: Path to DOCX template
        output_docx: Explicit path where rendered DOCX should be saved
        debug: Enable debug logging
        skip_compare: Skip comparison verification
        roundtrip_dir: Optional directory for roundtrip JSON files
    
    Returns:
        Tuple of (ok, errors, warnings, compare_ok).
        compare_ok is None if comparison did not run (e.g., render error).
    """
    import json
    
    try:
        # Load CV data from JSON
        with json_path.open("r", encoding="utf-8") as f:
            cv_data = json.load(f)
        
        # Render using the new renderer interface (with explicit output path)
        render_cv_data(cv_data, template_path, output_docx)

        # Skip compare when explicitly requested by caller
        if skip_compare:
            return True, [], [], None

        # Round-trip extraction from rendered DOCX - use RunInput
        if roundtrip_dir:
            roundtrip_dir.mkdir(parents=True, exist_ok=True)
            roundtrip_json = roundtrip_dir / (output_docx.stem + ".json")
        else:
            roundtrip_json = output_docx.with_suffix(".json")
        roundtrip_input = RunInput.from_path(output_docx)
        roundtrip_data = process_single_docx(roundtrip_input, out=roundtrip_json)

        original_data = cv_data

        verifier = get_verifier("roundtrip-verifier")
        cmp = verifier.verify(original_data, target_data=roundtrip_data)
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
