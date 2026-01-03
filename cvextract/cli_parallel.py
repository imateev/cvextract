"""
CLI Parallel Processing Module.

Handles parallel processing of entire directories of CV files while maintaining
the single-file processing architecture.
"""

from __future__ import annotations

import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple, Optional

from .cli_config import UserConfig, ExtractStage
from .cli_execute import execute_pipeline
from .logging_utils import LOG
from .adjusters.openai_company_research_adjuster import _url_to_cache_filename, _research_company_profile
import os


def scan_directory_for_docx(directory: Path) -> List[Path]:
    """
    Recursively scan directory for all .docx files.
    
    Args:
        directory: Directory to scan
    
    Returns:
        List of Path objects for all .docx files found
    """
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    if not directory.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")
    
    docx_files = []
    for docx_file in directory.rglob("*.docx"):
        if docx_file.is_file():
            # Skip temporary Word files (start with ~$)
            if not docx_file.name.startswith("~$"):
                docx_files.append(docx_file)
    
    return sorted(docx_files)


def _perform_upfront_research(config: UserConfig) -> Optional[Path]:
    """
    Perform company research once upfront before parallel processing.
    
    Args:
        config: User configuration
    
    Returns:
        Path to the research cache file, or None if research failed or not needed
    """
    if not config.adjust or not config.adjust.adjusters:
        return None
    
    # Only perform research for openai-company-research adjuster
    company_research_adjuster = None
    for adjuster_config in config.adjust.adjusters:
        if adjuster_config.name == "openai-company-research":
            company_research_adjuster = adjuster_config
            break
    
    if not company_research_adjuster or 'customer-url' not in company_research_adjuster.params:
        return None
    
    customer_url = company_research_adjuster.params['customer-url']
    
    # Get API key and model
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        LOG.warning("OPENAI_API_KEY not set, skipping upfront research")
        return None
    
    model = company_research_adjuster.openai_model or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
    
    # Create research cache directory
    research_dir = config.target_dir / "research_data"
    research_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine cache file path
    cache_filename = _url_to_cache_filename(customer_url)
    cache_path = research_dir / cache_filename
    
    # Perform research (will use cache if it exists)
    LOG.info("Performing upfront company research for: %s", customer_url)
    research_data = _research_company_profile(
        customer_url,
        api_key,
        model,
        cache_path
    )
    
    if research_data:
        LOG.info("Company research completed and cached at: %s", cache_path)
        return cache_path
    else:
        LOG.warning("Company research failed, proceeding without adjustment")
        return None


def process_single_file_wrapper(file_path: Path, config: UserConfig) -> Tuple[bool, str, int]:
    """
    Wrapper to process a single file through the existing pipeline.
    
    Args:
        file_path: Path to the DOCX file to process
        config: User configuration with parallel settings
    
    Returns:
        Tuple of (success: bool, message: str, exit_code: int)
    """
    try:
        # Create a new config for this specific file
        file_config = UserConfig(
            target_dir=config.target_dir,
            extract=ExtractStage(
                source=file_path,
                output=config.extract.output if config.extract else None
            ) if config.extract else None,
            adjust=config.adjust,
            apply=config.apply,
            parallel=None,  # No nested parallel processing
            strict=config.strict,
            debug=config.debug,
            log_file=config.log_file,
            suppress_summary=True,  # Suppress summary in parallel mode
            input_dir=config.parallel.source  # Pass the root input directory for relative path calculation
        )
        
        # Execute the pipeline for this file
        # Each file will log its status line, but not the summary
        exit_code = execute_pipeline(file_config)
        
        if exit_code == 0:
            return (True, "", exit_code)
        elif exit_code == 2:
            return (True, "warnings (strict mode)", exit_code)
        else:
            return (False, "pipeline execution failed", exit_code)
            
    except Exception as e:
        error_msg = str(e)
        if config.debug:
            error_msg = traceback.format_exc()
        return (False, error_msg, 1)


def execute_parallel_pipeline(config: UserConfig) -> int:
    """
    Execute pipeline in parallel mode, processing entire directory of files.
    
    Args:
        config: User configuration with parallel settings
    
    Returns:
        Exit code (0 = all success, 1 = one or more failed, 2 = strict mode warnings)
    """
    if not config.parallel:
        raise ValueError("execute_parallel_pipeline called without parallel configuration")
    
    # Validate input directory
    input_dir = config.parallel.source
    if not input_dir.exists():
        LOG.error("Input directory not found: %s", input_dir)
        return 1
    
    if not input_dir.is_dir():
        LOG.error("Input path is not a directory: %s", input_dir)
        return 1
    
    # Scan for DOCX files
    try:
        docx_files = scan_directory_for_docx(input_dir)
    except Exception as e:
        LOG.error("Failed to scan directory: %s", e)
        if config.debug:
            LOG.error(traceback.format_exc())
        return 1
    
    if not docx_files:
        LOG.error("No .docx files found in directory: %s", input_dir)
        return 1
    
    # Perform upfront research if adjust is configured
    if config.adjust and config.adjust.adjusters:
        # Research is performed and cached for reuse by individual file processing
        _perform_upfront_research(config)
    
    # Log start of parallel processing
    n_workers = config.parallel.n
    LOG.info("Processing %d files with %d parallel workers", len(docx_files), n_workers)
    
    # Track results - categorize as fully successful, partial (warnings), or failed
    full_success_count = 0
    partial_success_count = 0  # Files with warnings but no errors
    failed_count = 0
    failed_files = []
    
    # Process files in parallel (but logging is serialized)
    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        # Submit all tasks
        future_to_file = {
            executor.submit(process_single_file_wrapper, file_path, config): file_path
            for file_path in docx_files
        }
        
        # Process results as they complete
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                success, message, exit_code = future.result()
                if success:
                    if exit_code == 2 or "warning" in message.lower():
                        # Partial success - has warnings
                        partial_success_count += 1
                    else:
                        # Full success - no errors or warnings
                        full_success_count += 1
                else:
                    failed_count += 1
                    failed_files.append(str(file_path))
            except Exception as e:
                LOG.error("✗ %s | Unexpected error: %s", file_path.name, str(e))
                if config.debug:
                    LOG.error(traceback.format_exc())
                failed_count += 1
                failed_files.append(str(file_path))
    
    # Log summary
    total_files = len(docx_files)
    success_count = full_success_count + partial_success_count
    LOG.info("=" * 60)
    if partial_success_count > 0:
        LOG.info("Completed: %d/%d files succeeded (%d full, %d partial), %d failed", 
                 success_count, total_files, full_success_count, partial_success_count, failed_count)
    else:
        LOG.info("Completed: %d/%d files succeeded, %d failed", success_count, total_files, failed_count)
    
    # Only show failed files list in debug mode or log file
    if failed_files and config.debug:
        LOG.info("Failed files:")
        for failed_file in failed_files:
            LOG.info("  - %s", failed_file)
    
    # Return exit code - only fail in strict mode with warnings, not for file failures
    if config.strict and partial_success_count > 0:
        LOG.error("Strict mode enabled: warnings treated as failure.")
        return 2
    else:
        # Success even if some files failed (user request)
        return 0
