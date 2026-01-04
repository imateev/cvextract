"""
Tests for --debug-external flag functionality.

Validates that external provider logs are:
1. Suppressed by default in parallel mode
2. Captured when --debug-external is enabled
3. Routed through buffered output controller
4. Never duplicated or interleaved
"""

import logging
from pathlib import Path
import pytest

from cvextract.output_controller import (
    OutputController,
    VerbosityLevel,
    BufferingLogHandler,
    initialize_output_controller,
)
from cvextract.cli_gather import gather_user_requirements


class TestDebugExternalCLIArgument:
    """Tests for --debug-external CLI argument parsing."""

    def test_debug_external_flag_defaults_to_false(self):
        """When --debug-external is not provided, should default to False."""
        config = gather_user_requirements([
            '--extract', 'source=test.docx',
            '--target', 'output/'
        ])
        assert config.debug_external is False

    def test_debug_external_flag_can_be_enabled(self):
        """When --debug-external is provided, should be True."""
        config = gather_user_requirements([
            '--extract', 'source=test.docx',
            '--target', 'output/',
            '--debug-external'
        ])
        assert config.debug_external is True

    def test_debug_external_with_parallel_mode(self):
        """--debug-external should work with parallel mode."""
        config = gather_user_requirements([
            '--parallel', 'source=/test/dir', 'n=5',
            '--extract',
            '--target', 'output/',
            '--debug-external'
        ])
        assert config.debug_external is True
        assert config.parallel is not None


class TestExternalProviderLogSuppression:
    """Tests for external provider log suppression."""

    def test_external_logs_suppressed_by_default(self):
        """External provider loggers should be suppressed by default in parallel mode."""
        controller = OutputController(
            verbosity=VerbosityLevel.MINIMAL,
            enable_buffering=True,
            debug_external=False,
        )
        
        # Check that external loggers are suppressed
        openai_logger = logging.getLogger("openai")
        assert openai_logger.level == logging.CRITICAL + 1
        
        httpx_logger = logging.getLogger("httpx")
        assert httpx_logger.level == logging.CRITICAL + 1

    def test_external_logs_not_suppressed_when_debug_external_enabled(self):
        """External provider loggers should not be suppressed when debug_external is True."""
        # Clear any existing handlers on external loggers
        for logger_name in ['openai', 'httpx', 'httpcore']:
            logger = logging.getLogger(logger_name)
            logger.handlers.clear()
            logger.setLevel(logging.WARNING)  # Reset to default
        
        controller = OutputController(
            verbosity=VerbosityLevel.DEBUG,
            enable_buffering=True,
            debug_external=True,
        )
        
        # Check that external loggers are set to DEBUG
        openai_logger = logging.getLogger("openai")
        assert openai_logger.level == logging.DEBUG
        
        httpx_logger = logging.getLogger("httpx")
        assert httpx_logger.level == logging.DEBUG

    def test_buffering_handler_filters_external_logs_by_default(self):
        """BufferingLogHandler should filter external logs when debug_external is False."""
        handler = BufferingLogHandler(VerbosityLevel.DEBUG, debug_external=False)
        handler.setFormatter(logging.Formatter("%(message)s"))
        
        test_file = Path("/tmp/test.docx")
        handler.set_current_file(test_file)
        
        # Create an external provider log record
        external_record = logging.LogRecord(
            name="openai",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="OpenAI API call",
            args=(),
            exc_info=None,
        )
        
        # Emit the record
        handler.emit(external_record)
        
        # Buffer should not contain the external message
        buffer = handler._buffers.get(test_file)
        assert buffer is None or len(buffer.lines) == 0

    def test_buffering_handler_captures_external_logs_when_enabled(self):
        """BufferingLogHandler should capture external logs when debug_external is True."""
        handler = BufferingLogHandler(VerbosityLevel.DEBUG, debug_external=True)
        handler.setFormatter(logging.Formatter("%(message)s"))
        
        test_file = Path("/tmp/test.docx")
        handler.set_current_file(test_file)
        
        # Create an external provider log record
        external_record = logging.LogRecord(
            name="openai",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="OpenAI API call",
            args=(),
            exc_info=None,
        )
        
        # Emit the record
        handler.emit(external_record)
        
        # Buffer should contain the external message
        buffer = handler._buffers.get(test_file)
        assert buffer is not None
        assert len(buffer.lines) == 1
        assert "OpenAI API call" in buffer.lines[0]


class TestExternalProviderHandlerSetup:
    """Tests for external provider handler setup."""

    def test_external_handlers_added_when_debug_external_true(self):
        """External provider loggers should have buffering handler when debug_external is True."""
        # Clear any existing handlers on external loggers
        for logger_name in ['openai', 'httpx']:
            logger = logging.getLogger(logger_name)
            logger.handlers.clear()
            logger.propagate = True  # Reset to default
        
        controller = OutputController(
            verbosity=VerbosityLevel.DEBUG,
            enable_buffering=True,
            debug_external=True,
        )
        
        # Check that external loggers have the buffering handler
        openai_logger = logging.getLogger("openai")
        assert controller._handler in openai_logger.handlers
        assert openai_logger.propagate is False  # Should not propagate to avoid duplication

    def test_external_handlers_not_added_when_debug_external_false(self):
        """External provider loggers should not have buffering handler when debug_external is False."""
        # Clear any existing handlers on external loggers
        for logger_name in ['openai', 'httpx']:
            logger = logging.getLogger(logger_name)
            logger.handlers.clear()
        
        controller = OutputController(
            verbosity=VerbosityLevel.DEBUG,
            enable_buffering=True,
            debug_external=False,
        )
        
        # Check that external loggers do not have the buffering handler
        openai_logger = logging.getLogger("openai")
        assert controller._handler not in openai_logger.handlers


class TestOutputControllerInitialization:
    """Tests for output controller initialization with debug_external."""

    def test_initialize_controller_with_debug_external(self):
        """initialize_output_controller should accept debug_external parameter."""
        controller = initialize_output_controller(
            verbosity=VerbosityLevel.DEBUG,
            enable_buffering=True,
            debug_external=True,
        )
        
        assert controller is not None
        assert controller.debug_external is True
        assert controller.enable_buffering is True

    def test_initialize_controller_debug_external_defaults_to_false(self):
        """initialize_output_controller should default debug_external to False."""
        controller = initialize_output_controller(
            verbosity=VerbosityLevel.DEBUG,
            enable_buffering=True,
        )
        
        assert controller is not None
        assert controller.debug_external is False


class TestIntegration:
    """Integration tests for debug_external functionality."""

    def test_external_logs_captured_in_verbose_mode_with_debug_external(self, capsys):
        """External logs should be captured in verbose mode when debug_external is True."""
        # Clear any existing handlers
        logger = logging.getLogger("cvextract")
        openai_logger = logging.getLogger("openai")
        logger.handlers.clear()
        openai_logger.handlers.clear()
        openai_logger.propagate = True  # Reset
        logger.setLevel(logging.DEBUG)
        
        controller = OutputController(
            verbosity=VerbosityLevel.VERBOSE,
            enable_buffering=True,
            debug_external=True,
        )
        
        test_file = Path("/tmp/test.docx")
        
        with controller.file_context(test_file):
            # Simulate external provider log
            openai_logger.info("External provider message")
        
        # Flush the file
        controller.flush_file(test_file, "✅ test.docx")
        
        captured = capsys.readouterr()
        # Should contain the external provider message
        assert "External provider message" in captured.out

    def test_external_logs_not_captured_without_debug_external(self, capsys):
        """External logs should not be captured when debug_external is False."""
        # Clear any existing handlers
        logger = logging.getLogger("cvextract")
        openai_logger = logging.getLogger("openai")
        logger.handlers.clear()
        openai_logger.handlers.clear()
        logger.setLevel(logging.DEBUG)
        
        controller = OutputController(
            verbosity=VerbosityLevel.VERBOSE,
            enable_buffering=True,
            debug_external=False,
        )
        
        test_file = Path("/tmp/test.docx")
        
        with controller.file_context(test_file):
            # Simulate external provider log (should be suppressed)
            openai_logger.info("External provider message")
        
        # Flush the file
        controller.flush_file(test_file, "✅ test.docx")
        
        captured = capsys.readouterr()
        # Should NOT contain the external provider message
        assert "External provider message" not in captured.out
