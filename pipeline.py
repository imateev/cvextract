"""
pipeline.py

Batch-oriented orchestration layer for cvextract.

Core functions / modes
- extract:
  - Scans one .docx or a folder of .docx files and writes one JSON file per résumé.
- extract-apply:
  - Extracts JSON as above, then renders a new .docx for each input by applying a docxtpl template.
- apply:
  - Takes existing JSON files and renders new .docx files using a docxtpl template.
  
Responsibilities:
- Coordinate extraction and rendering across files or folders
- Apply validation and collect warnings/errors
- Enforce consistent logging behavior
- Produce stable exit codes for automation and CI

Logging guarantees:
- Exactly ONE log line is emitted per input file
- Two status icons are shown per file:
  - Extract: 🟢 success, ⚠️ success-with-warnings, ❌ failure
  - Apply:   ✅ success, ❌ failure, ➖ not attempted
- A summary line is printed at the end of each run
- Detailed stack traces are only printed in debug mode

This module contains no argument parsing and no low-level DOCX parsing.
"""

from __future__ import annotations

import os
import traceback
from pathlib import Path
from typing import List, Optional

from .logging_utils import LOG, fmt_issues
from .core import dump_body_sample, process_single_docx, render_from_json

# ------------------------- Helper -------------------------

def infer_source_root(inputs: List[Path]) -> Path:
    """
    Infer the root directory of the batch so we can preserve folder structure
    in output without passing source explicitly.
    - If a single file: use its parent as root.
    - If multiple files: use common path of their parent folders.
    """
    if not inputs:
        return Path(".")
    if len(inputs) == 1:
        return inputs[0].parent
    parents = [str(p.parent.resolve()) for p in inputs]
    return Path(os.path.commonpath(parents))

def safe_relpath(p: Path, root: Path) -> str:
    """Best-effort relative path for nicer logging."""
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return p.name
    
# ------------------------- Modes -------------------------

def run_extract_mode(inputs: List[Path], target_dir: Path, strict: bool, debug: bool) -> int:
    processed = 0
    extracted_ok = 0
    had_warning = False

    source_root = infer_source_root(inputs)
    json_dir = target_dir / "structured_data"
    json_dir.mkdir(parents=True, exist_ok=True)

    for docx_file in inputs:
        if docx_file.suffix.lower() != ".docx":
            continue

        processed += 1
        rel_name = safe_relpath(docx_file, source_root)

        extract_ok = False
        errs: List[str] = []
        warns: List[str] = []

        try:
            rel_parent = docx_file.parent.resolve().relative_to(source_root)
            out_json = json_dir / rel_parent / f"{docx_file.stem}.json"

            result, _data = process_single_docx(docx_file, out=out_json)
            extract_ok = result.ok
            errs = result.errors
            warns = result.warnings

            if extract_ok:
                extracted_ok += 1
            if warns:
                had_warning = True

        except Exception as e:
            extract_ok = False
            errs = [f"exception: {type(e).__name__}"]
            warns = []
            if debug:
                LOG.error(traceback.format_exc())
                dump_body_sample(docx_file, n=30)

        # Icons (extract-only mode => apply icon is ➖)
        x_icon = "❌"
        if extract_ok and warns:
            x_icon = "⚠️ "
        elif extract_ok:
            x_icon = "🟢"

        a_icon = "➖"
        LOG.info("%s%s %s | %s", x_icon, a_icon, rel_name, fmt_issues(errs, warns))

    LOG.info("🟢 Extracted %d of %d file(s) to JSON in: %s", extracted_ok, processed, json_dir)

    if strict and had_warning:
        LOG.error("Strict mode enabled: warnings treated as failure.")
        return 2
    return 0 if extracted_ok == processed else 1

def run_extract_apply_mode(inputs: List[Path], template_path: Path, target_dir: Path, strict: bool, debug: bool) -> int:
    processed = 0
    extracted_ok = 0
    rendered_ok = 0
    had_warning = False

    source_root = infer_source_root(inputs)
    json_dir = target_dir / "structured_data"
    json_dir.mkdir(parents=True, exist_ok=True)

    documents_dir = target_dir / "documents"
    documents_dir.mkdir(parents=True, exist_ok=True)

    for docx_file in inputs:
        if docx_file.suffix.lower() != ".docx":
            continue

        processed += 1
        rel_name = safe_relpath(docx_file, source_root)

        extract_ok = False
        apply_ok: Optional[bool] = None  # None => not attempted
        errs: List[str] = []
        warns: List[str] = []

        try:
            rel_parent = docx_file.parent.resolve().relative_to(source_root)
            out_json = json_dir / rel_parent / f"{docx_file.stem}.json"

            result, _data = process_single_docx(docx_file, out=out_json)
            extract_ok = result.ok
            errs = result.errors[:]
            warns = result.warnings[:]

            if extract_ok:
                extracted_ok += 1
                if warns:
                    had_warning = True

                try:
                    out_docx_dir = documents_dir / rel_parent
                    out_docx_dir.mkdir(parents=True, exist_ok=True)
                    _out_docx = render_from_json(out_json, template_path, out_docx_dir)
                    apply_ok = True
                    rendered_ok += 1
                except Exception as e:
                    apply_ok = False
                    errs = errs + [f"render: {type(e).__name__}"]
                    if debug:
                        LOG.error(traceback.format_exc())
            else:
                # Extraction failed => render not attempted
                apply_ok = None
                if warns:
                    had_warning = True

        except Exception as e:
            extract_ok = False
            apply_ok = None
            errs = [f"exception: {type(e).__name__}"]
            warns = []
            if debug:
                LOG.error(traceback.format_exc())
                dump_body_sample(docx_file, n=30)

        # Extract icon rules
        x_icon = "❌"
        if extract_ok and warns:
            x_icon = "⚠️ "
        elif extract_ok:
            x_icon = "🟢"

        # Apply icon rules (✅ success, ❌ fail, ➖ not attempted)
        if apply_ok is None:
            a_icon = "➖"
        else:
            a_icon = "✅" if apply_ok else "❌"

        LOG.info("%s%s %s | %s", x_icon, a_icon, rel_name, fmt_issues(errs, warns))

    LOG.info(
        "🟢 Extracted %d of %d file(s) to JSON (%s) and rendered %d DOCX file(s) into: %s",
        extracted_ok,
        processed,
        json_dir,
        rendered_ok,
        documents_dir,
    )

    if strict and had_warning:
        LOG.error("Strict mode enabled: warnings treated as failure.")
        return 2
    return 0 if (extracted_ok == processed and rendered_ok == extracted_ok) else 1

def run_apply_mode(inputs: List[Path], template_path: Path, target_dir: Path, debug: bool) -> int:
    processed = 0
    rendered_ok = 0

    source_root = infer_source_root(inputs)
    documents_dir = target_dir / "documents"
    documents_dir.mkdir(parents=True, exist_ok=True)

    for json_file in inputs:
        if json_file.suffix.lower() != ".json":
            continue

        processed += 1
        rel_name = safe_relpath(json_file, source_root)

        apply_ok = False
        errs: List[str] = []
        warns: List[str] = []

        try:
            rel_parent = json_file.parent.resolve().relative_to(source_root)
            out_docx_dir = documents_dir / rel_parent
            out_docx_dir.mkdir(parents=True, exist_ok=True)

            _out_docx = render_from_json(json_file, template_path, target_dir=out_docx_dir)
            apply_ok = True
            rendered_ok += 1
        except Exception as e:
            apply_ok = False
            errs = [f"render: {type(e).__name__}"]
            if debug:
                LOG.error(traceback.format_exc())

        x_icon = "➖"
        a_icon = "✅" if apply_ok else "❌"
        LOG.info("%s%s %s | %s", x_icon, a_icon, rel_name, fmt_issues(errs, warns))

    LOG.info("🟢 Rendered %d of %d JSON file(s) into: %s", rendered_ok, processed, documents_dir)
    return 0 if rendered_ok == processed else 1
