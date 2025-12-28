"""
CLI Phase 1: Gather user requirements.

Parses command-line arguments and returns UserConfig dataclass.
No side effects - just parsing and conversion.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Optional

from .cli_config import ExecutionMode, UserConfig


def _map_legacy_mode_to_execution_mode(mode: str, has_adjustment: bool, adjust_dry_run: bool) -> ExecutionMode:
    """
    Map legacy CLI mode strings to new ExecutionMode enum.
    
    Legacy modes:
    - extract: Just extract data to JSON
    - extract-apply: Extract and render (optionally with adjustment)
    - apply: Render from JSON (optionally with adjustment)
    """
    if mode == "extract":
        return ExecutionMode.EXTRACT
    
    if mode == "extract-apply":
        if has_adjustment:
            if adjust_dry_run:
                return ExecutionMode.EXTRACT_ADJUST
            return ExecutionMode.EXTRACT_ADJUST_RENDER
        return ExecutionMode.EXTRACT_RENDER
    
    # mode == "apply"
    if has_adjustment:
        if adjust_dry_run:
            return ExecutionMode.ADJUST
        return ExecutionMode.ADJUST_RENDER
    return ExecutionMode.RENDER


def gather_user_requirements(argv: Optional[List[str]] = None) -> UserConfig:
    """
    Phase 1: Parse command-line arguments and return user configuration.
    
    No side effects - just parsing and conversion to UserConfig.
    """
    parser = argparse.ArgumentParser(
        description="Extract CV data to JSON and optionally apply a DOCX template.",
        epilog="""
Examples:
  Extract DOCX files to JSON only:
    python -m cvextract.cli \\
      --mode extract \\
      --source cvs/ \\
      --template template.docx \\
      --target output/

  Extract DOCX files and apply a template:
    python -m cvextract.cli \\
      --mode extract-apply \\
      --source cvs/ \\
      --template template.docx \\
      --target output/

  Apply a template to existing JSON files:
    python -m cvextract.cli \\
      --mode apply \\
      --source extracted_json/ \\
      --template template.docx \\
      --target output/

  Run with file logging (log directory is created automatically):
    python -m cvextract.cli \\
      --mode extract-apply \\
      --source cvs/ \\
      --template template.docx \\
      --target output/ \\
      --log-file logs/run-01/cvextract.log
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--mode", required=True, choices=["extract", "extract-apply", "apply"], 
                        help="Operation mode")
    parser.add_argument("--source", required=True, 
                        help="Input file or folder (.docx for extract*, .json for apply)")
    parser.add_argument("--template", required=True, help="Template .docx (single file)")
    parser.add_argument("--target", required=True, help="Target output directory")

    parser.add_argument("--strict", action="store_true", 
                        help="Treat warnings as failure (non-zero exit code).")
    parser.add_argument("--debug", action="store_true", 
                        help="Verbose logs + stack traces on failure.")
    parser.add_argument("--log-file", 
                        help="Optional path to a log file. If set, all output is also written there.")

    # Optional customer adjustment using OpenAI
    parser.add_argument("--adjust-for-customer", 
                        help="Optional URL to a customer page; when set, adjust JSON via OpenAI before rendering.")
    parser.add_argument("--openai-model", 
                        help="Optional OpenAI model to use (default from OPENAI_MODEL or 'gpt-4o-mini').")
    parser.add_argument("--adjust-dry-run", action="store_true", 
                        help="Perform adjustment and write .adjusted.json, but skip rendering.")
    
    args = parser.parse_args(argv)
    
    # Map legacy mode to ExecutionMode
    execution_mode = _map_legacy_mode_to_execution_mode(
        args.mode,
        has_adjustment=bool(args.adjust_for_customer),
        adjust_dry_run=args.adjust_dry_run
    )
    
    return UserConfig(
        mode=execution_mode,
        source=Path(args.source),
        template=Path(args.template) if args.template else None,
        target_dir=Path(args.target),
        adjust_url=args.adjust_for_customer,
        openai_model=args.openai_model,
        adjust_dry_run=args.adjust_dry_run,
        strict=args.strict,
        debug=args.debug,
        log_file=args.log_file,
    )
