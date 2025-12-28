"""
CLI Phase 1: Gather user requirements.

Parses command-line arguments and returns UserConfig dataclass.
No side effects - just parsing and conversion.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Optional

from .cli_config import ExecutionMode, UserConfig, ExtractStage, AdjustStage, ApplyStage


def _parse_stage_params(param_str: str) -> Dict[str, str]:
    """
    Parse stage parameter string into a dictionary.
    
    Format: key=value key2=value2
    Example: "source=cv.docx output=data.json"
    """
    params = {}
    if not param_str:
        return params
    
    for part in param_str.split():
        if '=' in part:
            key, value = part.split('=', 1)
            params[key.strip()] = value.strip()
    
    return params


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
    
    Supports both legacy mode-based and new stage-based interfaces.
    No side effects - just parsing and conversion to UserConfig.
    """
    parser = argparse.ArgumentParser(
        description="Extract CV data to JSON and optionally apply a DOCX template.",
        epilog="""
Examples (NEW STAGE-BASED INTERFACE):
  Extract DOCX files to JSON only:
    python -m cvextract.cli \\
      --extract source=cvs/ \\
      --target output/

  Extract and apply a template:
    python -m cvextract.cli \\
      --extract source=cvs/ \\
      --apply template=template.docx \\
      --target output/

  Extract, adjust, and apply:
    python -m cvextract.cli \\
      --extract source=cvs/ \\
      --adjust customer-url=https://example.com \\
      --apply template=template.docx \\
      --target output/

  Apply a template to existing JSON files:
    python -m cvextract.cli \\
      --apply template=template.docx data=extracted_json/ \\
      --target output/

Examples (LEGACY MODE-BASED INTERFACE - DEPRECATED):
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
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # New stage-based arguments
    parser.add_argument("--extract", nargs='*', metavar="PARAM",
                        help="Extract stage: Extract CV data from DOCX to JSON. "
                             "Parameters: source=<path> [output=<path>]")
    parser.add_argument("--adjust", nargs='*', metavar="PARAM",
                        help="Adjust stage: Adjust CV data for customer using AI. "
                             "Parameters: [data=<path>] customer-url=<url> [output=<path>] [openai-model=<model>] [dry-run]")
    parser.add_argument("--apply", nargs='*', metavar="PARAM",
                        help="Apply stage: Apply CV data to DOCX template. "
                             "Parameters: template=<path> [data=<path>] [output=<path>]")

    # Legacy mode-based arguments (deprecated but maintained for compatibility)
    parser.add_argument("--mode", choices=["extract", "extract-apply", "apply"], 
                        help="[DEPRECATED] Operation mode - use stage flags instead")
    parser.add_argument("--source", 
                        help="[DEPRECATED] Input file or folder - use stage parameters instead")
    parser.add_argument("--template", 
                        help="[DEPRECATED] Template .docx - use --apply template=<path> instead")

    # Global arguments
    parser.add_argument("--target", required=True, help="Target output directory")
    parser.add_argument("--strict", action="store_true", 
                        help="Treat warnings as failure (non-zero exit code).")
    parser.add_argument("--debug", action="store_true", 
                        help="Verbose logs + stack traces on failure.")
    parser.add_argument("--log-file", 
                        help="Optional path to a log file. If set, all output is also written there.")

    # Legacy adjustment arguments (deprecated)
    parser.add_argument("--adjust-for-customer", 
                        help="[DEPRECATED] Use --adjust customer-url=<url> instead")
    parser.add_argument("--openai-model", 
                        help="[DEPRECATED] Use --adjust openai-model=<model> instead")
    parser.add_argument("--adjust-dry-run", action="store_true", 
                        help="[DEPRECATED] Use --adjust dry-run instead")
    
    args = parser.parse_args(argv)
    
    # Determine if using legacy or new interface
    using_legacy = args.mode is not None
    using_stages = any([args.extract is not None, args.adjust is not None, args.apply is not None])
    
    if using_legacy and using_stages:
        raise ValueError("Cannot mix legacy --mode with new stage flags (--extract, --adjust, --apply)")
    
    if not using_legacy and not using_stages:
        raise ValueError("Must specify either --mode (legacy) or stage flags (--extract, --adjust, --apply)")
    
    # Parse legacy mode-based interface
    if using_legacy:
        execution_mode = _map_legacy_mode_to_execution_mode(
            args.mode,
            has_adjustment=bool(args.adjust_for_customer),
            adjust_dry_run=args.adjust_dry_run
        )
        
        return UserConfig(
            mode=execution_mode,
            source=Path(args.source) if args.source else None,
            template=Path(args.template) if args.template else None,
            target_dir=Path(args.target),
            adjust_url=args.adjust_for_customer,
            openai_model=args.openai_model,
            adjust_dry_run=args.adjust_dry_run,
            strict=args.strict,
            debug=args.debug,
            log_file=args.log_file,
        )
    
    # Parse new stage-based interface
    extract_stage = None
    adjust_stage = None
    apply_stage = None
    
    if args.extract is not None:
        params = _parse_stage_params(' '.join(args.extract) if args.extract else '')
        if 'source' not in params:
            raise ValueError("--extract requires 'source' parameter")
        
        extract_stage = ExtractStage(
            source=Path(params['source']),
            output=Path(params['output']) if 'output' in params else None,
        )
    
    if args.adjust is not None:
        params = _parse_stage_params(' '.join(args.adjust) if args.adjust else '')
        
        adjust_stage = AdjustStage(
            data=Path(params['data']) if 'data' in params else None,
            output=Path(params['output']) if 'output' in params else None,
            customer_url=params.get('customer-url'),
            openai_model=params.get('openai-model'),
            dry_run='dry-run' in params,
        )
    
    if args.apply is not None:
        params = _parse_stage_params(' '.join(args.apply) if args.apply else '')
        if 'template' not in params:
            raise ValueError("--apply requires 'template' parameter")
        
        apply_stage = ApplyStage(
            template=Path(params['template']),
            data=Path(params['data']) if 'data' in params else None,
            output=Path(params['output']) if 'output' in params else None,
        )
    
    return UserConfig(
        extract=extract_stage,
        adjust=adjust_stage,
        apply=apply_stage,
        target_dir=Path(args.target),
        strict=args.strict,
        debug=args.debug,
        log_file=args.log_file,
    )
