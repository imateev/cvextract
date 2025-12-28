"""
CLI Phase 1: Gather user requirements.

Parses command-line arguments and returns UserConfig dataclass.
No side effects - just parsing and conversion.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Optional

from .cli_config import UserConfig, ExtractStage, AdjustStage, ApplyStage


def _parse_stage_params(param_str: str) -> Dict[str, str]:
    """
    Parse stage parameter string into a dictionary.
    
    Format: key=value key2=value2 flag
    Example: "source=cv.docx output=data.json dry-run"
    
    Flags without values are stored with empty string value.
    """
    params = {}
    if not param_str:
        return params
    
    for part in param_str.split():
        if '=' in part:
            key, value = part.split('=', 1)
            key = key.strip()
            if not key:
                raise ValueError("Empty parameter key not allowed")
            params[key] = value.strip()
        else:
            # Flag without value (e.g., dry-run)
            flag = part.strip()
            if not flag:
                continue  # Skip empty strings
            params[flag] = ""
    
    return params


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
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Stage-based arguments
    parser.add_argument("--extract", nargs='*', metavar="PARAM",
                        help="Extract stage: Extract CV data from DOCX to JSON. "
                             "Parameters: source=<path> [output=<path>]")
    parser.add_argument("--adjust", nargs='*', metavar="PARAM",
                        help="Adjust stage: Adjust CV data for customer using AI. "
                             "Parameters: [data=<path>] customer-url=<url> [output=<path>] [openai-model=<model>] [dry-run]")
    parser.add_argument("--apply", nargs='*', metavar="PARAM",
                        help="Apply stage: Apply CV data to DOCX template. "
                             "Parameters: template=<path> [data=<path>] [output=<path>]")

    # Global arguments
    parser.add_argument("--target", required=True, help="Target output directory")
    parser.add_argument("--strict", action="store_true", 
                        help="Treat warnings as failure (non-zero exit code).")
    parser.add_argument("--debug", action="store_true", 
                        help="Verbose logs + stack traces on failure.")
    parser.add_argument("--log-file", 
                        help="Optional path to a log file. If set, all output is also written there.")
    
    args = parser.parse_args(argv)
    
    # Check that at least one stage is specified
    using_stages = any([args.extract is not None, args.adjust is not None, args.apply is not None])
    
    if not using_stages:
        raise ValueError("Must specify at least one stage flag (--extract, --adjust, or --apply)")
    
    # Parse stage-based interface
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
