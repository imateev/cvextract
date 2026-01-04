"""Tests for logging utilities."""

import logging
from pathlib import Path
from cvextract.logging_utils import fmt_issues, setup_logging, LOG


class TestIssueFormatting:
    """Tests for issue formatting function."""

    def test_format_with_no_issues_returns_dash(self):
        """When there are no errors or warnings, should return '-'."""
        result = fmt_issues([], [])
        assert result == "-"

    def test_format_with_only_errors_includes_errors_list(self):
        """When only errors exist, should format error list without warnings."""
        result = fmt_issues(["error1", "error2"], [])
        assert "errors: error1, error2" in result
        assert "warnings:" not in result

    def test_format_with_only_warnings_includes_warnings_list(self):
        """When only warnings exist, should format warnings list without errors."""
        result = fmt_issues([], ["warn1", "warn2"])
        assert "warnings: warn1, warn2" in result
        assert "errors:" not in result

    def test_format_with_both_errors_and_warnings_includes_both(self):
        """When both errors and warnings exist, should format both lists."""
        result = fmt_issues(["error1"], ["warn1"])
        assert "errors: error1" in result
        assert "warnings: warn1" in result


class TestLoggingSetup:
    """Tests for logging configuration."""

    def test_setup_with_info_level_adds_handlers(self):
        """When verbosity is 1, should configure logging at INFO level."""
        setup_logging(verbosity=1)
        assert len(logging.root.handlers) > 0

    def test_setup_with_debug_level_adds_handlers(self):
        """When verbosity is 2, should configure logging at DEBUG level."""
        setup_logging(verbosity=2)
        assert len(logging.root.handlers) > 0

    def test_setup_with_file_creates_log_file(self, tmp_path: Path):
        """When log_file is provided, should create file and write logs to it."""
        LOG.handlers.clear()
        
        log_file = tmp_path / "test.log"
        setup_logging(verbosity=0, log_file=log_file)
        
        LOG.info("test message")
        
        assert log_file.exists()
