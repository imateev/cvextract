"""
Logging helpers for cvextract.

Defines the package logger and simple utilities for configuring
console and optional file logging.
"""

from __future__ import annotations

import logging
from typing import List, Optional

LOG = logging.getLogger("cvextract")

def setup_logging(debug: bool, log_file: Optional[str] = None) -> None:
    level = logging.DEBUG if debug else logging.INFO

    handlers: List[logging.Handler] = []

    # Console output
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
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

    logging.basicConfig(level=level, handlers=handlers)

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