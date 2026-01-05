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
from .logging_utils import LOG, fmt_issues
from .output_controller import get_output_controller
from .adjusters.openai_company_research_adjuster import _url_to_cache_filename, _research_company_profile
import os


def scan_directory_for_files(directory: Path, file_pattern: str = "*.docx") -> List[Path]:
    """
    Recursively scan directory for files matching the given pattern.
    
    Args:
        directory: Directory to scan
        file_pattern: Glob pattern for files to match (e.g., "*.docx", "*.txt")
    
    Returns:
        List of Path objects for all matching files found
    """
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    if not directory.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")
    
    files = []
    for file in directory.rglob(file_pattern):
        if file.is_file():
            # Skip temporary Word files (start with ~$)
            if not file.name.startswith("~$"):
                files.append(file)
    
    return sorted(files)


def scan_directory_for_docx(directory: Path) -> List[Path]:
    """
    Recursively scan directory for all .docx files.
    
    DEPRECATED: Use scan_directory_for_files() instead.
    Kept for backward compatibility.
    
    Args:
        directory: Directory to scan
    
    Returns:
        List of Path objects for all .docx files found
    """
    return scan_directory_for_files(directory, "*.docx")


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


def process_single_file_wrapper(file_path: Path, config: UserConfig) -> Tuple[bool, str, int, bool]:
    """
    Wrapper to process a single file through the existing pipeline.
    
    Args:
        file_path: Path to the file to process
        config: User configuration with parallel settings
    
    Returns:
        Tuple of (success: bool, message: str, exit_code: int, has_warnings: bool)
    """
    # Get output controller and establish file context
    controller = get_output_controller()
    
    try:
        with controller.file_context(file_path):
            # Create a new config for this specific file
            file_config = UserConfig(
                target_dir=config.target_dir,
                extract=ExtractStage(
                    source=file_path,
                    output=config.extract.output if config.extract else None,
                    name=config.extract.name if config.extract else "private-internal-extractor"
                ) if config.extract else None,
                adjust=config.adjust,
                apply=config.apply,
                parallel=None,  # No nested parallel processing
                verbosity=config.verbosity,
                log_file=config.log_file,
                suppress_summary=True,  # Suppress summary in parallel mode
                suppress_file_logging=True,  # Suppress per-file status logging (we log in parallel wrapper with progress)
                input_dir=config.parallel.source  # Pass the root input directory for relative path calculation
            )
            
            # Execute the pipeline for this file
            exit_code = execute_pipeline(file_config)
            warning_message = ""
            if file_config.last_warnings:
                warning_message = fmt_issues([], file_config.last_warnings)
            
            has_warnings = bool(file_config.last_warnings)

            if exit_code == 0:
                return (True, warning_message, exit_code, has_warnings)
            else:
                return (False, "pipeline execution failed", exit_code, False)
            
    except Exception as e:
        error_msg = str(e)
        if config.debug:
            error_msg = traceback.format_exc()
        return (False, error_msg, 1, False)


def execute_parallel_pipeline(config: UserConfig) -> int:
    """
    Execute pipeline in parallel mode, processing entire directory of files.
    
    Args:
        config: User configuration with parallel settings
    
    Returns:
        Exit code (0 = all success, 1 = one or more failed)
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
    
    # Scan for files matching the pattern
    try:
        files = scan_directory_for_files(input_dir, config.parallel.file_type)
    except Exception as e:
        LOG.error("Failed to scan directory: %s", e)
        if config.debug:
            LOG.error(traceback.format_exc())
        return 1
    
    if not files:
        LOG.error("No files matching pattern '%s' found in directory: %s", 
                  config.parallel.file_type, input_dir)
        return 1
    
    # Perform upfront research if adjust is configured
    if config.adjust and config.adjust.adjusters:
        # Research is performed and cached for reuse by individual file processing
        _perform_upfront_research(config)
    
    # Log start of parallel processing
    n_workers = config.parallel.n
    total_files = len(files)
    controller = get_output_controller()
    controller.direct_print(f"Processing {total_files} files matching '{config.parallel.file_type}' with {n_workers} parallel workers")
    
    # Track results - categorize as fully successful, partial (warnings), or failed
    full_success_count = 0
    partial_success_count = 0  # Files with warnings but no errors
    failed_count = 0
    failed_files = []
    completed_count = 0  # Track completed files for progress
    
    # Process files in parallel (but logging is serialized)
    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        # Submit all tasks
        future_to_file = {
            executor.submit(process_single_file_wrapper, file_path, config): file_path
            for file_path in files
        }
        
        # Process results as they complete
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            completed_count += 1
            
            # Calculate progress percentage
            progress_pct = int((completed_count / total_files) * 100)
            progress_str = f"[{completed_count}/{total_files} | {progress_pct}%]"
            
            try:
                success, message, exit_code, has_warnings = future.result()
                
                # Determine status icons (same as in cli_execute.py)
                if success and has_warnings:
                    status_icon = "⚠️ "
                    partial_success_count += 1
                elif success and exit_code == 0:
                    status_icon = "✅"
                    full_success_count += 1
                else:
                    status_icon = "❌"
                    failed_count += 1
                    failed_files.append(str(file_path))
                
                # Build summary line for atomic flush
                if message:
                    summary_line = f"{status_icon} {progress_str} {file_path.name} | {message}"
                    # Log with original format for tests and file logging
                    LOG.info("%s %s %s | %s", status_icon, progress_str, file_path.name, message)
                else:
                    summary_line = f"{status_icon} {progress_str} {file_path.name}"
                    # Log with original format for tests and file logging
                    LOG.info("%s %s %s", status_icon, progress_str, file_path.name)
                
                # Flush output atomically for this file (console only)
                controller.flush_file(file_path, summary_line)
                    
            except Exception as e:
                error_summary = f"❌ {progress_str} {file_path.name} | Unexpected error: {str(e)}"
                # Log the error message
                LOG.error(error_summary)
                # Flush output atomically for this file
                controller.flush_file(file_path, error_summary)
                if config.debug:
                    LOG.error(traceback.format_exc())
                failed_count += 1
                failed_files.append(str(file_path))
    
    # Log summary
    total_files = len(files)
    success_count = full_success_count + partial_success_count
    controller.direct_print("=" * 60)
    LOG.info("=" * 60)
    
    if partial_success_count > 0:
        summary_msg = f"Completed: {success_count}/{total_files} files succeeded ({full_success_count} full, {partial_success_count} partial), {failed_count} failed"
        controller.direct_print(summary_msg)
        LOG.info(summary_msg)
    else:
        summary_msg = f"Completed: {success_count}/{total_files} files succeeded, {failed_count} failed"
        controller.direct_print(summary_msg)
        LOG.info(summary_msg)
    
    # Only show failed files list in debug mode or log file
    if failed_files and config.debug:
        controller.direct_print("Failed files:")
        LOG.info("Failed files:")
        for failed_file in failed_files:
            controller.direct_print(f"  - {failed_file}")
            LOG.info("  - %s", failed_file)
    
    # Return exit code
    # Success even if some files failed (user request)
    return 0
