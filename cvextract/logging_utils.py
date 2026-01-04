"""
Logging helpers for cvextract.

Defines the package logger and simple utilities for configuring
console and optional file logging.
"""

from __future__ import annotations

import logging
from typing import List, Optional

LOG = logging.getLogger("cvextract")

# Verbosity levels
VERBOSITY_QUIET = 0    # Minimal output (default)
VERBOSITY_NORMAL = 1   # Standard output with status icons
VERBOSITY_VERBOSE = 2  # Detailed debug output

def setup_logging(debug: bool, log_file: Optional[str] = None, verbosity: int = VERBOSITY_QUIET) -> None:
    """
    Setup logging with verbosity control.
    
    Args:
        debug: Legacy debug flag (overrides verbosity to VERBOSITY_VERBOSE)
        log_file: Optional log file path
        verbosity: Verbosity level (0=quiet, 1=normal, 2=verbose)
    """
    # Debug flag overrides verbosity
    if debug:
        verbosity = VERBOSITY_VERBOSE
    
    # Map verbosity to log level
    if verbosity >= VERBOSITY_VERBOSE:
        level = logging.DEBUG
    elif verbosity >= VERBOSITY_NORMAL:
        level = logging.INFO
    else:
        level = logging.WARNING  # Quiet mode: only warnings and errors

    handlers: List[logging.Handler] = []

    # Console output
    console = logging.StreamHandler()
    console.setLevel(level)
    
    # Simpler format for normal/verbose modes
    if verbosity >= VERBOSITY_NORMAL:
        console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    else:
        # Minimal format for quiet mode - no prefix
        console.setFormatter(logging.Formatter("%(message)s"))
    
    handlers.append(console)

    # Optional file output
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)  # always full detail in file
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        handlers.append(file_handler)

    logging.basicConfig(level=level, handlers=handlers, force=True)
    
    # Suppress noisy third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

def fmt_issues(errors: List[str], warnings: List[str]) -> str:
    """
    Compact error/warning string for the one-line-per-file log.
    """
    parts: List[str] = []
    if errors:
        parts.append("errors: " + ", ".join(errors))
    if warnings:
        parts.append("warnings: " + ", ".join(warnings))
    return " | ".join(parts) if parts else "-"