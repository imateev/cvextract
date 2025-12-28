#!/usr/bin/env python3
"""
Command-line interface for cvextract.

Three-phase architecture:
1. Gather user requirements (parse args) -> UserConfig
2. Prepare execution environment (validate, create dirs)
3. Execute pipeline (run operations with explicit paths)
"""

from __future__ import annotations

import argparse
import json
import traceback
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional

from .logging_utils import LOG, setup_logging, fmt_issues
from .pipeline_helpers import (
    infer_source_root,
    safe_relpath,
    extract_single,
    render_and_verify,
    get_status_icons,
    categorize_result,
)
from .ml_adjustment import adjust_for_customer, _url_to_cache_filename


# ------------------------- Data Structures -------------------------


class ExecutionMode(Enum):
    """Execution modes that explicitly describe what operations to perform."""
    
    EXTRACT = "extract"
    EXTRACT_RENDER = "extract-render"
    EXTRACT_ADJUST = "extract-adjust"
    EXTRACT_ADJUST_RENDER = "extract-adjust-render"
    RENDER = "render"
    ADJUST = "adjust"
    ADJUST_RENDER = "adjust-render"
    
    @property
    def needs_extraction(self) -> bool:
        """Whether this mode requires extracting data from DOCX."""
        return self in (
            ExecutionMode.EXTRACT,
            ExecutionMode.EXTRACT_RENDER,
            ExecutionMode.EXTRACT_ADJUST,
            ExecutionMode.EXTRACT_ADJUST_RENDER,
        )
    
    @property
    def needs_adjustment(self) -> bool:
        """Whether this mode requires adjusting data for customer."""
        return self in (
            ExecutionMode.EXTRACT_ADJUST,
            ExecutionMode.EXTRACT_ADJUST_RENDER,
            ExecutionMode.ADJUST,
            ExecutionMode.ADJUST_RENDER,
        )
    
    @property
    def needs_rendering(self) -> bool:
        """Whether this mode requires rendering to DOCX."""
        return self in (
            ExecutionMode.EXTRACT_RENDER,
            ExecutionMode.EXTRACT_ADJUST_RENDER,
            ExecutionMode.RENDER,
            ExecutionMode.ADJUST_RENDER,
        )
    
    @property
    def should_compare(self) -> bool:
        """Whether this mode should run comparison verification (only if no adjustment)."""
        return self.needs_rendering and not self.needs_adjustment


@dataclass
class UserConfig:
    """Configuration gathered from user input."""
    
    mode: ExecutionMode
    source: Path
    template: Optional[Path]
    target_dir: Path
    
    # Adjustment settings
    adjust_url: Optional[str] = None
    openai_model: Optional[str] = None
    adjust_dry_run: bool = False
    
    # Execution settings
    strict: bool = False
    debug: bool = False
    log_file: Optional[str] = None

# ------------------------- Phase 1: Gather User Requirements -------------------------


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


# ------------------------- Phase 2: Prepare Execution Environment -------------------------


def _collect_inputs(src: Path, mode: ExecutionMode, template_path: Optional[Path]) -> List[Path]:
    """Collect input files based on source path and execution mode."""
    if src.is_file():
        return [src]

    if not src.is_dir():
        raise FileNotFoundError(f"Path not found or not a file/folder: {src}")

    # For extraction modes, collect DOCX files (excluding template)
    if mode.needs_extraction:
        return [
            p for p in src.rglob("*.docx")
            if p.is_file()
            and (template_path is None or p.resolve() != template_path.resolve())
        ]

    # For render-only modes, collect JSON files
    return [p for p in src.rglob("*.json") if p.is_file()]


def prepare_execution_environment(config: UserConfig) -> UserConfig:
    """
    Phase 2: Validate inputs and prepare execution environment.
    
    - Validates template exists and is .docx
    - Creates target directory
    - Collects input files
    - No execution yet
    
    Returns the same config (for chaining).
    """
    # Validate template (required for modes that need rendering)
    if config.mode.needs_rendering or config.mode.needs_extraction:
        if config.template is None:
            LOG.error("Template is required for this mode")
            raise ValueError("Template is required")
        
        if not config.template.is_file() or config.template.suffix.lower() != ".docx":
            LOG.error("Template not found or not a .docx: %s", config.template)
            raise ValueError(f"Invalid template: {config.template}")

    # Validate target directory
    config.target_dir.mkdir(parents=True, exist_ok=True)
    if not config.target_dir.is_dir():
        LOG.error("Target is not a directory: %s", config.target_dir)
        raise ValueError(f"Target is not a directory: {config.target_dir}")

    return config


# ------------------------- Phase 3: Execute Pipeline -------------------------


def execute_pipeline(config: UserConfig) -> int:
    """
    Phase 3: Execute the pipeline based on user configuration.
    
    All path decisions are made here explicitly. Subsystems receive
    explicit input/output paths.
    
    Returns exit code (0 = success, 1 = failure, 2 = strict mode warnings).
    """
    # Collect inputs
    try:
        inputs = _collect_inputs(config.source, config.mode, config.template)
    except Exception as e:
        LOG.error(str(e))
        if config.debug:
            LOG.error(traceback.format_exc())
        return 1

    if not inputs:
        LOG.error("No matching input files found.")
        return 1

    # Infer source root for preserving directory structure
    source_root = infer_source_root(inputs)
    
    # Create output directories based on mode
    json_dir = config.target_dir / "structured_data"
    documents_dir = config.target_dir / "documents"
    research_dir = config.target_dir / "research_data"
    verification_dir = config.target_dir / "verification_structured_data"
    
    if config.mode.needs_extraction or config.mode == ExecutionMode.ADJUST:
        json_dir.mkdir(parents=True, exist_ok=True)
    
    if config.mode.needs_rendering:
        documents_dir.mkdir(parents=True, exist_ok=True)
    
    if config.mode.needs_adjustment:
        research_dir.mkdir(parents=True, exist_ok=True)

    # Process each input file
    fully_ok = partial_ok = failed = 0
    had_warning = False

    for input_file in inputs:
        # Determine relative path for preserving directory structure
        rel_name = safe_relpath(input_file, source_root)
        rel_parent = input_file.parent.resolve().relative_to(source_root)
        
        # Initialize result tracking
        extract_ok = True
        extract_errs: List[str] = []
        extract_warns: List[str] = []
        apply_ok: Optional[bool] = None
        compare_ok: Optional[bool] = None
        apply_warns: List[str] = []
        
        # Step 1: Extract (if needed)
        if config.mode.needs_extraction:
            if input_file.suffix.lower() != ".docx":
                continue
            
            out_json = json_dir / rel_parent / f"{input_file.stem}.json"
            out_json.parent.mkdir(parents=True, exist_ok=True)
            
            extract_ok, extract_errs, extract_warns = extract_single(input_file, out_json, config.debug)
            if extract_warns:
                had_warning = True
            
            # If extraction failed and we need to render, skip rendering
            if not extract_ok and config.mode.needs_rendering:
                x_icon, a_icon, c_icon = get_status_icons(extract_ok, bool(extract_warns), None, None)
                LOG.info("%s%s%s %s | %s", x_icon, a_icon, c_icon, rel_name, 
                         fmt_issues(extract_errs, extract_warns))
                
                full, part, fail = categorize_result(extract_ok, bool(extract_warns), None)
                fully_ok += full
                partial_ok += part
                failed += fail
                continue
        else:
            # For non-extraction modes, use the input JSON directly
            if input_file.suffix.lower() != ".json":
                continue
            out_json = input_file
        
        # Step 2: Adjust (if needed)
        render_json = out_json
        if config.mode.needs_adjustment and config.adjust_url:
            try:
                with out_json.open("r", encoding="utf-8") as f:
                    original = json.load(f)
                
                # Pass cache_path for research results (company-specific, not CV-specific)
                research_cache_dir = research_dir / rel_parent
                research_cache_dir.mkdir(parents=True, exist_ok=True)
                research_cache = research_cache_dir / _url_to_cache_filename(config.adjust_url)
                
                adjusted = adjust_for_customer(
                    original, 
                    config.adjust_url, 
                    model=config.openai_model, 
                    cache_path=research_cache
                )
                
                # Save adjusted JSON
                if config.mode.needs_extraction:
                    adjusted_json = out_json.with_name(out_json.stem + ".adjusted.json")
                else:
                    # For apply modes, save in documents dir
                    out_docx_dir = documents_dir / rel_parent
                    out_docx_dir.mkdir(parents=True, exist_ok=True)
                    adjusted_json = out_docx_dir / (input_file.stem + ".adjusted.json")
                
                adjusted_json.parent.mkdir(parents=True, exist_ok=True)
                with adjusted_json.open("w", encoding="utf-8") as wf:
                    json.dump(adjusted, wf, ensure_ascii=False, indent=2)
                
                render_json = adjusted_json
            except Exception as e:
                # If adjust fails, proceed with original JSON
                if config.debug:
                    LOG.error("Adjustment failed: %s", traceback.format_exc())
                render_json = out_json
        
        # Step 3: Render (if needed and not dry-run)
        if config.mode.needs_rendering and not config.adjust_dry_run:
            out_docx_dir = documents_dir / rel_parent
            out_docx_dir.mkdir(parents=True, exist_ok=True)
            
            # Explicit output path for rendered DOCX
            output_docx = out_docx_dir / f"{input_file.stem}_NEW.docx"
            
            verify_dir = verification_dir / rel_parent
            
            apply_ok, render_errs, apply_warns, compare_ok = render_and_verify(
                json_path=render_json,
                template_path=config.template,
                output_docx=output_docx,  # Explicit path
                debug=config.debug,
                skip_compare=not config.mode.should_compare,
                roundtrip_dir=verify_dir,
            )
            
            if apply_warns:
                had_warning = True
            
            extract_errs = render_errs
        
        # Log result
        combined_warns = (extract_warns or []) + (apply_warns or [])
        x_icon, a_icon, c_icon = get_status_icons(extract_ok, bool(combined_warns), apply_ok, compare_ok)
        LOG.info("%s%s%s %s | %s", x_icon, a_icon, c_icon, rel_name, 
                 fmt_issues(extract_errs, combined_warns))
        
        # Categorize result
        full, part, fail = categorize_result(extract_ok, bool(combined_warns), apply_ok)
        fully_ok += full
        partial_ok += part
        failed += fail
    
    # Log summary
    total = fully_ok + partial_ok + failed
    
    if config.mode.needs_extraction and config.mode.needs_rendering:
        LOG.info(
            "📊 Extract+Apply summary: %d fully successful, %d partially successful, %d failed (total %d). JSON: %s | DOCX: %s",
            fully_ok, partial_ok, failed, total, json_dir, documents_dir
        )
    elif config.mode.needs_extraction:
        LOG.info(
            "📊 Extract summary: %d fully successful, %d partially successful, %d failed (total %d). JSON in: %s",
            fully_ok, partial_ok, failed, total, json_dir
        )
    else:
        LOG.info(
            "📊 Apply summary: %d successful, %d failed (total %d). Output in: %s",
            fully_ok, failed, total, documents_dir
        )
    
    # Return exit code
    if config.strict and had_warning:
        LOG.error("Strict mode enabled: warnings treated as failure.")
        return 2
    
    if failed == 0 and partial_ok == 0:
        return 0
    
    return 1


# ------------------------- Main Entry Point -------------------------


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main CLI entry point with three-phase architecture.
    
    Phase 1: Gather user requirements (parse args)
    Phase 2: Prepare execution environment (validate, setup)
    Phase 3: Execute pipeline (run operations)
    """
    # Phase 1: Gather requirements
    config = gather_user_requirements(argv)
    
    # Setup logging (side effect necessary for all phases)
    if config.log_file:
        Path(config.log_file).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    setup_logging(config.debug, log_file=config.log_file)
    
    try:
        # Phase 2: Prepare environment
        config = prepare_execution_environment(config)
        
        # Phase 3: Execute
        return execute_pipeline(config)
    except Exception as e:
        LOG.error(str(e))
        if config.debug:
            LOG.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
