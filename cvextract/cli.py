#!/usr/bin/env python3
"""
Command-line interface for cvextract.

Parses arguments, validates inputs, and dispatches to pipeline modes:
- extract
- extract-apply
- apply
"""

from __future__ import annotations

import argparse
import traceback
from pathlib import Path
from typing import List, Optional
import os

from .logging_utils import LOG, setup_logging
from .pipeline import run_apply_mode, run_extract_apply_mode, run_extract_mode

# ------------------------- CLI / main -------------------------

def collect_inputs(src: Path, mode: str, template_path: Path) -> List[Path]:
    if src.is_file():
        return [src]

    if not src.is_dir():
        raise FileNotFoundError(f"Path not found or not a file/folder: {src}")

    if mode in ("extract", "extract-apply"):
        return [
            p for p in src.rglob("*.docx")
            if p.is_file()
            and p.resolve() != template_path.resolve()
        ]

    return [p for p in src.rglob("*.json") if p.is_file()]

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract CV data to JSON and optionally apply a DOCX template.",
        epilog="""
Examples:
Examples:
  Extract DOCX files to JSON only:
    python -m cvextract.cli \
      --mode extract \
      --source cvs/ \
      --template template.docx \
      --target output/

  Extract DOCX files and apply a template:
    python -m cvextract.cli \
      --mode extract-apply \
      --source cvs/ \
      --template template.docx \
      --target output/

  Apply a template to existing JSON files:
    python -m cvextract.cli \
      --mode apply \
      --source extracted_json/ \
      --template template.docx \
      --target output/

  Run with file logging (log directory is created automatically):
    python -m cvextract.cli \
      --mode extract-apply \
      --source cvs/ \
      --template template.docx \
      --target output/ \
      --log-file logs/run-01/cvextract.log
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--mode", required=True, choices=["extract", "extract-apply", "apply"], help="Operation mode")
    parser.add_argument("--source", required=True, help="Input file or folder (.docx for extract*, .json for apply)")
    parser.add_argument("--template", required=True, help="Template .docx (single file)")
    parser.add_argument("--target", required=True, help="Target output directory")

    parser.add_argument("--strict", action="store_true", help="Treat warnings as failure (non-zero exit code).")
    parser.add_argument("--debug", action="store_true", help="Verbose logs + stack traces on failure.")
    parser.add_argument("--log-file", help="Optional path to a log file. If set, all output is also written there.",
                        )

    # Optional customer adjustment using OpenAI
    parser.add_argument("--adjust-for-customer", help="Optional URL to a customer page; when set, adjust JSON via OpenAI before rendering.")
    parser.add_argument("--openai-model", help="Optional OpenAI model to use (default from OPENAI_MODEL or 'gpt-4o-mini').")
    parser.add_argument("--adjust-dry-run", action="store_true", help="Perform adjustment and write .adjusted.json, but skip rendering.")
    return parser.parse_args(argv)

def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    if args.log_file:
        Path(args.log_file).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

    setup_logging(args.debug, log_file=args.log_file)

    mode: str = args.mode
    src = Path(args.source)
    template_path = Path(args.template)
    target_dir = Path(args.target)

    # Validate template
    if not template_path.is_file() or template_path.suffix.lower() != ".docx":
        LOG.error("Template not found or not a .docx: %s", template_path)
        return 1

    # Validate target
    target_dir.mkdir(parents=True, exist_ok=True)
    if not target_dir.is_dir():
        LOG.error("Target is not a directory: %s", target_dir)
        return 1

    # Collect inputs
    try:
        inputs = collect_inputs(src, mode, template_path)
    except Exception as e:
        LOG.error(str(e))
        if args.debug:
            LOG.error(traceback.format_exc())
        return 1

    if not inputs:
        LOG.error("No matching input files found.")
        return 1

    # Dispatch
    # Store optional adjust settings in environment for downstream pipeline
    if args.adjust_for_customer:
        os.environ["CVEXTRACT_ADJUST_URL"] = args.adjust_for_customer
    if args.openai_model:
        os.environ["OPENAI_MODEL"] = args.openai_model
    if args.adjust_dry_run:
        os.environ["CVEXTRACT_ADJUST_DRY_RUN"] = "1"

    if mode == "extract":
        return run_extract_mode(inputs, target_dir, strict=args.strict, debug=args.debug)
    if mode == "extract-apply":
        return run_extract_apply_mode(
            inputs, template_path, target_dir,
            strict=args.strict, debug=args.debug,
        )
    return run_apply_mode(
        inputs, template_path, target_dir,
        debug=args.debug,
    )

if __name__ == "__main__":
    raise SystemExit(main())
