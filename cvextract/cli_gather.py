"""
CLI Phase 1: Gather user requirements.

Parses command-line arguments and returns UserConfig dataclass.
No side effects - just parsing and conversion.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Optional


def _handle_list_command(list_type: str) -> None:
    """
    Handle --list command to display available components.
    
    Args:
        list_type: Type of components to list ('adjusters', 'renderers', or 'extractors')
    """
    if list_type == 'adjusters':
        from .adjusters import list_adjusters
        adjusters = list_adjusters()
        print("\nAvailable Adjusters:")
        print("=" * 60)
        for adj in adjusters:
            print(f"  {adj['name']}")
            print(f"    {adj['description']}")
        print()
    elif list_type == 'renderers':
        from .renderers import DocxCVRenderer
        print("\nAvailable Renderers:")
        print("=" * 60)
        print("  docx")
        print("    Renders CV data to DOCX format using docxtpl templates")
        print()
    elif list_type == 'extractors':
        from .extractors import DocxCVExtractor
        print("\nAvailable Extractors:")
        print("=" * 60)
        print("  docx")
        print("    Extracts CV data from DOCX format")
        print()


from .cli_config import UserConfig, ExtractStage, AdjustStage, AdjusterConfig, ApplyStage, ParallelStage


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
        description="Extract CV data to JSON and optionally apply a DOCX template.\n\n"
                    "All parameters use key=value format (e.g., source=file.docx, name=adjuster-name).",
        epilog="""
Examples:
  Extract DOCX file to JSON only:
    python -m cvextract.cli \\
      --extract source=cv.docx \\
      --target output/

  Extract and apply a template:
    python -m cvextract.cli \\
      --extract source=cv.docx \\
      --apply template=template.docx \\
      --target output/

  Extract, adjust for a company, and apply:
    python -m cvextract.cli \\
      --extract source=cv.docx \\
      --adjust name=openai-company-research customer-url=https://example.com \\
      --apply template=template.docx \\
      --target output/

  Adjust for a specific job posting:
    python -m cvextract.cli \\
      --extract source=cv.docx \\
      --adjust name=openai-job-specific job-url=https://example.com/careers/123 \\
      --apply template=template.docx \\
      --target output/

  Apply a template to existing JSON file:
    python -m cvextract.cli \\
      --apply template=template.docx data=extracted.json \\
      --target output/

  Process directory with parallel workers:
    python -m cvextract.cli \\
      --parallel input=/var/foo/cvs n=10 \\
      --extract \\
      --adjust name=openai-company-research customer-url=https://example.com \\
      --apply template=template.docx \\
      --target output/
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Stage-based arguments
    parser.add_argument("--extract", nargs='*', metavar="PARAM",
                        help="Extract stage: Extract CV data from DOCX to JSON. "
                             "Parameters: source=<file> (single DOCX file, not directory) [output=<path>]")
    parser.add_argument("--adjust", nargs='*', metavar="PARAM", action='append',
                        help="Adjust stage: Adjust CV data using named adjusters (can be specified multiple times for chaining). "
                             "Parameters: name=<adjuster-name> [adjuster-specific params] [data=<file>] [output=<path>] [openai-model=<model>] [dry-run]. "
                             "Use --list adjusters to see available adjusters.")
    parser.add_argument("--apply", nargs='*', metavar="PARAM",
                        help="Apply stage: Apply CV data to DOCX template. "
                             "Parameters: template=<path> [data=<file>] (single JSON file) [output=<path>]")
    parser.add_argument("--parallel", nargs='*', metavar="PARAM",
                        help="Parallel stage: Process entire directory of CV files in parallel. "
                             "Parameters: input=<directory> (required) [n=<number>] (default=1)")

    # Global arguments
    parser.add_argument("--list", choices=['adjusters', 'renderers', 'extractors'],
                        help="List available components: adjusters, renderers, or extractors")
    parser.add_argument("--target", help="Target output directory (required unless using --list)")
    parser.add_argument("--strict", action="store_true", 
                        help="Treat warnings as failure (non-zero exit code).")
    parser.add_argument("--debug", action="store_true", 
                        help="Verbose logs + stack traces on failure.")
    parser.add_argument("--log-file", 
                        help="Optional path to a log file. If set, all output is also written there.")
    
    args = parser.parse_args(argv)
    
    # Handle --list option
    if args.list:
        _handle_list_command(args.list)
        import sys
        sys.exit(0)
    
    # Validate target is provided when not using --list
    if not args.target:
        raise ValueError("--target is required when not using --list")
    
    # Check that at least one stage is specified
    using_stages = any([args.extract is not None, args.adjust is not None, args.apply is not None, args.parallel is not None])
    
    if not using_stages:
        raise ValueError("Must specify at least one stage flag (--extract, --adjust, --apply, or --parallel)")
    
    # Parse stage-based interface
    extract_stage = None
    adjust_stage = None
    apply_stage = None
    parallel_stage = None
    
    if args.parallel is not None:
        params = _parse_stage_params(args.parallel if args.parallel else [])
        if 'input' not in params:
            raise ValueError("--parallel requires 'input' parameter")
        
        n_workers = 1
        if 'n' in params:
            try:
                n_workers = int(params['n'])
                if n_workers < 1:
                    raise ValueError("--parallel parameter 'n' must be >= 1")
            except ValueError as e:
                raise ValueError(f"--parallel parameter 'n' must be a valid integer: {e}")
        
        parallel_stage = ParallelStage(
            input=Path(params['input']),
            n=n_workers,
        )
    
    if args.extract is not None:
        params = _parse_stage_params(args.extract if args.extract else [])
        # When parallel is specified, source is optional (will be injected per-file)
        if 'source' not in params and not parallel_stage:
            raise ValueError("--extract requires 'source' parameter")
        
        extract_stage = ExtractStage(
            source=Path(params['source']) if 'source' in params else Path('.'),  # Placeholder when parallel
            output=_resolve_output_path(params['output'], Path(args.target)) if 'output' in params else None,
        )
    
    if args.adjust is not None:
        # args.adjust is a list of lists (due to action='append')
        # Each element is a list of parameters for one adjuster invocation
        adjuster_configs = []
        data_path = None
        output_path = None
        dry_run = False
        
        for adjust_params_list in args.adjust:
            params = _parse_stage_params(adjust_params_list if adjust_params_list else [])
            
            # Extract common parameters (data, output, dry-run) from first adjuster
            if not adjuster_configs:
                if 'data' in params:
                    data_path = Path(params['data'])
                if 'output' in params:
                    output_path = _resolve_output_path(params['output'], Path(args.target))
                if 'dry-run' in params:
                    dry_run = True
            
            # Get adjuster name (required)
            adjuster_name = params.get('name')
            if not adjuster_name:
                raise ValueError("--adjust requires 'name' parameter to specify the adjuster")
            
            # Get OpenAI model if specified
            openai_model = params.get('openai-model')
            
            # Build adjuster-specific params (exclude common params)
            adjuster_params = {k: v for k, v in params.items() 
                             if k not in ('name', 'data', 'output', 'dry-run', 'openai-model')}
            
            adjuster_configs.append(AdjusterConfig(
                name=adjuster_name,
                params=adjuster_params,
                openai_model=openai_model
            ))
        
        if not adjuster_configs:
            raise ValueError("--adjust specified but no adjusters configured")
        
        adjust_stage = AdjustStage(
            adjusters=adjuster_configs,
            data=data_path,
            output=output_path,
            dry_run=dry_run,
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
        parallel=parallel_stage,
        target_dir=Path(args.target),
        strict=args.strict,
        debug=args.debug,
        log_file=args.log_file,
    )
