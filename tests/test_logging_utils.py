"""Tests for logging utilities."""

import pytest
import logging
from pathlib import Path
from cvextract.logging_utils import fmt_issues, setup_logging, LOG


def test_fmt_issues_no_errors_or_warnings():
    """Test formatting with no issues."""
    result = fmt_issues([], [])
    assert result == "-"


def test_fmt_issues_only_errors():
    """Test formatting with only errors."""
    result = fmt_issues(["error1", "error2"], [])
    assert "errors: error1, error2" in result
    assert "warnings:" not in result


def test_fmt_issues_only_warnings():
    """Test formatting with only warnings."""
    result = fmt_issues([], ["warn1", "warn2"])
    assert "warnings: warn1, warn2" in result
    assert "errors:" not in result


def test_fmt_issues_both_errors_and_warnings():
    """Test formatting with both errors and warnings."""
    result = fmt_issues(["error1"], ["warn1"])
    assert "errors: error1" in result
    assert "warnings: warn1" in result


def test_setup_logging_info_level():
    """Test logging setup at INFO level."""
    # basicConfig is cumulative, so we just verify handlers are added
    setup_logging(debug=False)
    assert len(logging.root.handlers) > 0


def test_setup_logging_debug_level():
    """Test logging setup at DEBUG level."""
    setup_logging(debug=True)
    assert len(logging.root.handlers) > 0


def test_setup_logging_with_file(tmp_path: Path):
    """Test logging setup with file handler."""
    # Clear existing handlers
    LOG.handlers.clear()
    
    log_file = tmp_path / "test.log"
    setup_logging(debug=False, log_file=log_file)
    
    # Log something
    LOG.info("test message")
    
    # File should be created
    assert log_file.exists()
