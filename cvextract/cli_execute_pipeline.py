"""
CLI Phase 3: Execute pipeline orchestration.
"""

from __future__ import annotations

from .cli_config import UserConfig
from .cli_execute_single import execute_single


def execute_pipeline(config: UserConfig) -> int:
    """
    Phase 3: Execute the pipeline based on user configuration.

    Orchestrates per-step execution while input validation and output
    directory setup happen in the prepare phase. Each step module
    computes its own input/output paths. Uses single-file execution
    or parallel execution based on configuration.

    Returns exit code (0 = success, 1 = failure).
    """
    # Check if parallel mode is enabled
    if config.parallel:
        from .cli_parallel import execute_parallel_pipeline
        return execute_parallel_pipeline(config)

    exit_code, _ = execute_single(config)
    return exit_code
