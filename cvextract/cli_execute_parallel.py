"""
CLI Parallel Processing Module.

Handles parallel processing of entire directories of CV files while maintaining
the single-file processing architecture.
"""

from __future__ import annotations

import traceback
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import replace
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

from .cli_config import UserConfig
from .cli_execute_single import execute_single
from .logging_utils import LOG
from .output_controller import get_output_controller
from .shared import UnitOfWork, emit_work_status

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

def _build_file_config(config: UserConfig, file_path: Path) -> UserConfig:
    extract = config.extract
    adjust = config.adjust
    render = config.render

    if config.extract:
        extract = replace(config.extract, source=file_path)
    elif config.render:
        render = replace(config.render, data=file_path)
    elif config.adjust:
        adjust = replace(config.adjust, data=file_path)

    return replace(
        config,
        extract=extract,
        adjust=adjust,
        render=render,
        parallel=None,
        suppress_summary=True,
        suppress_file_logging=True,
        input_dir=config.parallel.source if config.parallel else None,
    )

def _execute_file(file_path: Path, config: UserConfig) -> Tuple[int, Optional[UnitOfWork]]:
    controller = get_output_controller()
    file_config = _build_file_config(config, file_path)
    with controller.file_context(file_path):
        return execute_single(file_config)


def _process_future_result(
    future: Future[Tuple[int, Optional[UnitOfWork]]],
    file_path: Path,
    progress_str: str,
    controller,
    config: UserConfig,
) -> Tuple["_WorkStatus", Optional[str]]:
    log_fn = None
    log_args: tuple[str, ...] = ()
    summary_line = ""
    try:
        exit_code, work = future.result()
        if not work:
            raise ValueError("Expected UnitOfWork from execute_single")
        
        status = _derive_work_status(work)
        summary_message = emit_work_status(work)
        if summary_message.endswith(" | -"):
            summary_message = summary_message[:-4]
        summary_line = f"{progress_str} {summary_message}"

        log_fn = LOG.info
        log_args = (progress_str, summary_message)
        return status, str(file_path) if status == _WorkStatus.FAILED else None
    except Exception as e:
        summary_line = f"❌ {progress_str} {file_path.name} | Unexpected error: {str(e)}"

        log_fn = LOG.error
        log_args = (summary_line,)
        if config.debug:
            LOG.error(traceback.format_exc())
            
        return _WorkStatus.FAILED, str(file_path)
    finally:
        if log_fn:
            log_fn(*log_args)
            controller.flush_file(file_path, summary_line)

class _WorkStatus(str, Enum):
    FULL = "full"
    PARTIAL = "partial"
    FAILED = "failed"

def _derive_work_status(work: UnitOfWork) -> "_WorkStatus":
    if not work.has_no_errors():
        return _WorkStatus.FAILED
    if not work.has_no_warnings_or_errors():
        return _WorkStatus.PARTIAL
    return _WorkStatus.FULL

def _emit_parallel_summary(
    total_files: int,
    full_success_count: int,
    partial_success_count: int,
    failed_count: int,
    failed_files: List[str],
    config: UserConfig,
    controller,
) -> None:
    success_count = full_success_count + partial_success_count
    controller.direct_print("=" * 60)
    LOG.info("=" * 60)

    if partial_success_count > 0:
        summary_msg = (
            "Completed: %d/%d files succeeded (%d full, %d partial), %d failed"
            % (success_count, total_files, full_success_count, partial_success_count, failed_count)
        )
    else:
        summary_msg = (
            "Completed: %d/%d files succeeded, %d failed"
            % (success_count, total_files, failed_count)
        )
    controller.direct_print(summary_msg)
    LOG.info(summary_msg)

    if failed_files and config.debug:
        controller.direct_print("Failed files:")
        LOG.info("Failed files:")
        for failed_file in failed_files:
            controller.direct_print(f"  - {failed_file}")
            LOG.info("  - %s", failed_file)

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
            executor.submit(_execute_file, file_path, config): file_path
            for file_path in files
        }
        
        # Process results as they complete
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            completed_count += 1
            
            # Calculate progress percentage
            progress_pct = int((completed_count / total_files) * 100)
            progress_str = f"[{completed_count}/{total_files} | {progress_pct}%]"
            
            status, failed_file = _process_future_result(
                future,
                file_path,
                progress_str,
                controller,
                config,
            )
            if status == _WorkStatus.PARTIAL:
                partial_success_count += 1
            elif status == _WorkStatus.FULL:
                full_success_count += 1
            else:
                failed_count += 1
                if failed_file:
                    failed_files.append(failed_file)
    
    _emit_parallel_summary(
        total_files=len(files),
        full_success_count=full_success_count,
        partial_success_count=partial_success_count,
        failed_count=failed_count,
        failed_files=failed_files,
        config=config,
        controller=controller,
    )
    
    # Return exit code
    # Success even if some files failed (user request)
    return 0
