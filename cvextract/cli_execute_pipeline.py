"""
CLI Phase 3: Execute pipeline orchestration.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from .cli_config import UserConfig
from .cli_execute_single import execute_single
from .logging_utils import LOG


def _build_rerun_config(config: UserConfig, file_path: Path) -> UserConfig:
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
        input_dir=None,
    )


def execute_pipeline(config: UserConfig) -> int:
    """
    Phase 3: Execute the pipeline based on user configuration.

    Orchestrates per-step execution while input validation and output
    directory setup happen in the prepare phase. Each step module
    computes its own input/output paths. Uses single-file execution
    or parallel execution based on configuration.

    Returns exit code (0 = success, 1 = failure).
    """
    if config.rerun_failed:
        from .cli_execute_parallel import _load_failed_list, _write_failed_list

        try:
            files = _load_failed_list(config.rerun_failed)
        except Exception as e:
            LOG.error("Failed to read rerun list: %s", e)
            return 1
        if not files:
            LOG.error("No files found in rerun list: %s", config.rerun_failed)
            return 1

        if config.parallel:
            from .cli_execute_parallel import _execute_parallel_pipeline

            source_label = f"from failed list '{config.rerun_failed}'"
            return _execute_parallel_pipeline(files, config, source_label=source_label)

        failed_files = []
        for file_path in files:
            file_config = _build_rerun_config(config, file_path)
            exit_code, work = execute_single(file_config)
            if exit_code != 0 or not work or not work.has_no_errors():
                failed_files.append(str(file_path))

        if config.log_failed:
            _write_failed_list(config.log_failed, failed_files)

        return 1 if failed_files else 0

    # Check if parallel mode is enabled
    if config.parallel:
        from .cli_execute_parallel import execute_parallel_pipeline

        return execute_parallel_pipeline(config)

    exit_code, _ = execute_single(config)
    return exit_code
