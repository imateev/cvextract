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


def _resolve_output_path(output_str: str, target_dir: Path) -> Path:
    """
    Resolve output path relative to target directory.
    
    - Absolute paths are used as-is
    - Relative paths are resolved relative to target_dir
    
    Examples:
        _resolve_output_path("/abs/path.json", Path("/target")) -> Path("/abs/path.json")
        _resolve_output_path("data.json", Path("/target")) -> Path("/target/data.json")
        _resolve_output_path("subdir/data.json", Path("/target")) -> Path("/target/subdir/data.json")
    """
    output_path = Path(output_str)
    if output_path.is_absolute():
        return output_path
    else:
        return target_dir / output_path


def _parse_stage_params(param_list: List[str]) -> Dict[str, str]:
    """
    Parse stage parameter list into a dictionary.
    
    Each element in param_list is either:
    - key=value (parameter with value, value can contain spaces)
    - flag (parameter without value)
    
    Examples:
    - ["source=cv.docx", "output=data.json", "dry-run"]
    - ["source=/path with spaces/file.docx", "output=data.json"]
    
    Flags without values are stored with empty string value.
    """
    params = {}
    if not param_list:
        return params
    
    for part in param_list:
        part = part.strip()
        if not part:
            continue  # Skip empty strings
            
        if '=' in part:
            key, value = part.split('=', 1)
            key = key.strip()
            if not key:
                raise ValueError("Empty parameter key not allowed")
            params[key] = value  # Keep value as-is, don't strip (preserves spaces)
        else:
            # Flag without value (e.g., dry-run)
            params[part] = ""
    
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
        params = _parse_stage_params(args.extract if args.extract else [])
        if 'source' not in params:
            raise ValueError("--extract requires 'source' parameter")
        
        extract_stage = ExtractStage(
            source=Path(params['source']),
            output=_resolve_output_path(params['output'], Path(args.target)) if 'output' in params else None,
        )
    
    if args.adjust is not None:
        params = _parse_stage_params(args.adjust if args.adjust else [])
        
        adjust_stage = AdjustStage(
            data=Path(params['data']) if 'data' in params else None,
            output=_resolve_output_path(params['output'], Path(args.target)) if 'output' in params else None,
            customer_url=params.get('customer-url'),
            openai_model=params.get('openai-model'),
            dry_run='dry-run' in params,
        )
    
    if args.apply is not None:
        params = _parse_stage_params(args.apply if args.apply else [])
        if 'template' not in params:
            raise ValueError("--apply requires 'template' parameter")
        
        apply_stage = ApplyStage(
            template=Path(params['template']),
            data=Path(params['data']) if 'data' in params else None,
            output=_resolve_output_path(params['output'], Path(args.target)) if 'output' in params else None,
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
