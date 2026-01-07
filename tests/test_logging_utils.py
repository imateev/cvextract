"""Tests for logging utilities."""

import logging
from pathlib import Path

from cvextract.cli_config import UserConfig
from cvextract.logging_utils import LOG, fmt_issues, setup_logging
from cvextract.shared import StepName, StepStatus, UnitOfWork


class TestIssueFormatting:
    """Tests for issue formatting function."""

    def test_format_with_no_issues_returns_dash(self):
        """When there are no errors or warnings, should return '-'."""
        work = UnitOfWork(
            config=UserConfig(target_dir=Path(".")),
            input=Path("input.json"),
            output=Path("output.json"),
        )
        result = fmt_issues(work, StepName.Extract)
        assert result == "-"

    def test_format_with_only_errors_includes_errors_list(self):
        """When only errors exist, should format error list without warnings."""
        work = UnitOfWork(
            config=UserConfig(target_dir=Path(".")),
            input=Path("input.json"),
            output=Path("output.json"),
        )
        work.step_statuses[StepName.Extract] = StepStatus(
            step=StepName.Extract,
            errors=["error1", "error2"],
        )
        result = fmt_issues(work, StepName.Extract)
        assert "errors: error1, error2" in result
        assert "warnings:" not in result

    def test_format_with_only_warnings_includes_warnings_list(self):
        """When only warnings exist, should format warnings list without errors."""
        work = UnitOfWork(
            config=UserConfig(target_dir=Path(".")),
            input=Path("input.json"),
            output=Path("output.json"),
        )
        work.step_statuses[StepName.Extract] = StepStatus(
            step=StepName.Extract,
            warnings=["warn1", "warn2"],
        )
        result = fmt_issues(work, StepName.Extract)
        assert "warnings: warn1, warn2" in result
        assert "errors:" not in result

    def test_format_with_both_errors_and_warnings_includes_both(self):
        """When both errors and warnings exist, should format both lists."""
        work = UnitOfWork(
            config=UserConfig(target_dir=Path(".")),
            input=Path("input.json"),
            output=Path("output.json"),
        )
        work.step_statuses[StepName.Extract] = StepStatus(
            step=StepName.Extract,
            errors=["error1"],
            warnings=["warn1"],
        )
        result = fmt_issues(work, StepName.Extract)
        assert "errors: error1" in result
        assert "warnings: warn1" in result


class TestLoggingSetup:
    """Tests for logging configuration."""

    def test_setup_with_info_level_adds_handlers(self):
        """When debug is False, should configure logging at INFO level."""
        setup_logging(debug=False)
        assert len(logging.root.handlers) > 0

    def test_setup_with_debug_level_adds_handlers(self):
        """When debug is True, should configure logging at DEBUG level."""
        setup_logging(debug=True)
        assert len(logging.root.handlers) > 0

    def test_setup_with_file_creates_log_file(self, tmp_path: Path):
        """When log_file is provided, should create file and write logs to it."""
        LOG.handlers.clear()

        log_file = tmp_path / "test.log"
        setup_logging(debug=False, log_file=log_file)

        LOG.info("test message")

        assert log_file.exists()
