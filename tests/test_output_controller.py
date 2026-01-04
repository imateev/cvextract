"""
Tests for output_controller module.

Validates per-file buffering, atomic flush, and verbosity filtering.
"""

import io
import logging
from pathlib import Path
import pytest
import sys
import threading

from cvextract.output_controller import (
    OutputController,
    VerbosityLevel,
    BufferingLogHandler,
    initialize_output_controller,
    get_output_controller,
)


def test_output_controller_initialization():
    """Test basic output controller initialization."""
    controller = OutputController(
        verbosity=VerbosityLevel.MINIMAL,
        enable_buffering=False,
    )
    assert controller.verbosity == VerbosityLevel.MINIMAL
    assert controller.enable_buffering is False
    assert controller._handler is None


def test_output_controller_with_buffering():
    """Test output controller with buffering enabled."""
    controller = OutputController(
        verbosity=VerbosityLevel.MINIMAL,
        enable_buffering=True,
    )
    assert controller.verbosity == VerbosityLevel.MINIMAL
    assert controller.enable_buffering is True
    assert controller._handler is not None
    assert isinstance(controller._handler, BufferingLogHandler)


def test_buffering_handler_filters_minimal():
    """Test that buffering handler filters output in minimal mode."""
    handler = BufferingLogHandler(VerbosityLevel.MINIMAL)
    
    # In minimal mode, should not output buffered content
    record = logging.LogRecord(
        name="cvextract",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    
    # Set file context
    test_file = Path("/tmp/test.docx")
    handler.set_current_file(test_file)
    
    # Emit the record - should be buffered but filtered out
    handler.emit(record)
    
    # In minimal mode, _should_output returns False
    assert not handler._should_output(record)


def test_buffering_handler_allows_verbose():
    """Test that buffering handler allows output in verbose mode."""
    handler = BufferingLogHandler(VerbosityLevel.VERBOSE)
    
    # In verbose mode, should buffer INFO and above
    record = logging.LogRecord(
        name="cvextract",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    
    # Should output in verbose mode
    assert handler._should_output(record)
    
    # But not DEBUG
    debug_record = logging.LogRecord(
        name="cvextract",
        level=logging.DEBUG,
        pathname="",
        lineno=0,
        msg="Debug message",
        args=(),
        exc_info=None,
    )
    assert not handler._should_output(debug_record)


def test_buffering_handler_allows_debug():
    """Test that buffering handler allows all output in debug mode."""
    handler = BufferingLogHandler(VerbosityLevel.DEBUG)
    
    # In debug mode, should output everything
    debug_record = logging.LogRecord(
        name="cvextract",
        level=logging.DEBUG,
        pathname="",
        lineno=0,
        msg="Debug message",
        args=(),
        exc_info=None,
    )
    assert handler._should_output(debug_record)
    
    info_record = logging.LogRecord(
        name="cvextract",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Info message",
        args=(),
        exc_info=None,
    )
    assert handler._should_output(info_record)


def test_file_context():
    """Test file context management."""
    controller = OutputController(
        verbosity=VerbosityLevel.MINIMAL,
        enable_buffering=True,
    )
    
    test_file = Path("/tmp/test.docx")
    
    with controller.file_context(test_file):
        # Handler should have current file set
        assert controller._handler._thread_local.current_file == test_file
    
    # After exiting context, should be None
    assert controller._handler._thread_local.current_file is None


def test_flush_file_minimal(capsys):
    """Test flush_file in minimal mode outputs only summary."""
    controller = OutputController(
        verbosity=VerbosityLevel.MINIMAL,
        enable_buffering=True,
    )
    
    test_file = Path("/tmp/test.docx")
    summary_line = "✅ [1/1 | 100%] test.docx"
    
    # Set file context and emit some logs (which will be filtered)
    with controller.file_context(test_file):
        logger = logging.getLogger("cvextract")
        logger.info("This should be buffered but not output in minimal mode")
    
    # Flush the file
    controller.flush_file(test_file, summary_line)
    
    # Capture output
    captured = capsys.readouterr()
    
    # Should only contain summary line
    assert summary_line in captured.out
    assert "This should be buffered" not in captured.out


def test_flush_file_verbose(capsys):
    """Test flush_file in verbose mode outputs buffered content."""
    # Clear any existing handlers on cvextract logger
    logger = logging.getLogger("cvextract")
    original_handlers = logger.handlers.copy()
    original_level = logger.level
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)  # Ensure logger accepts all messages
    
    controller = OutputController(
        verbosity=VerbosityLevel.VERBOSE,
        enable_buffering=True,
    )
    
    test_file = Path("/tmp/test.docx")
    summary_line = "✅ [1/1 | 100%] test.docx"
    
    # Set file context and emit some logs
    with controller.file_context(test_file):
        logger.info("Processing file")
        logger.info("Extraction complete")
    
    # Flush the file
    controller.flush_file(test_file, summary_line)
    
    # Capture output
    captured = capsys.readouterr()
    
    # Should contain both buffered content and summary
    assert "Processing file" in captured.out
    assert "Extraction complete" in captured.out
    assert summary_line in captured.out
    
    # Restore original handlers and level
    logger.handlers = original_handlers
    logger.setLevel(original_level)


def test_direct_print(capsys):
    """Test direct_print bypasses buffering."""
    controller = OutputController(
        verbosity=VerbosityLevel.MINIMAL,
        enable_buffering=True,
    )
    
    message = "Direct output message"
    controller.direct_print(message)
    
    captured = capsys.readouterr()
    assert message in captured.out


def test_global_controller_initialization():
    """Test global controller initialization."""
    controller = initialize_output_controller(
        verbosity=VerbosityLevel.VERBOSE,
        enable_buffering=True,
    )
    
    assert controller is not None
    assert controller.verbosity == VerbosityLevel.VERBOSE
    assert controller.enable_buffering is True
    
    # Get controller should return the same instance
    controller2 = get_output_controller()
    assert controller2 is controller


def test_third_party_logger_suppression():
    """Test that third-party loggers are suppressed in minimal mode."""
    controller = OutputController(
        verbosity=VerbosityLevel.MINIMAL,
        enable_buffering=True,
    )
    
    # Check that third-party loggers are set to CRITICAL+1
    openai_logger = logging.getLogger("openai")
    assert openai_logger.level == logging.CRITICAL + 1
    
    httpx_logger = logging.getLogger("httpx")
    assert httpx_logger.level == logging.CRITICAL + 1


def test_buffering_handler_filters_third_party():
    """Test that buffering handler filters third-party library output."""
    handler = BufferingLogHandler(VerbosityLevel.MINIMAL)
    handler.setFormatter(logging.Formatter("%(message)s"))
    
    test_file = Path("/tmp/test.docx")
    handler.set_current_file(test_file)
    
    # Third-party log record
    third_party_record = logging.LogRecord(
        name="openai",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="OpenAI API call",
        args=(),
        exc_info=None,
    )
    
    # Emit the record
    handler.emit(third_party_record)
    
    # Buffer should not contain the third-party message
    buffer = handler._buffers.get(test_file)
    assert buffer is None or len(buffer.lines) == 0


def test_buffering_removes_root_console_handlers():
    """Test that root console handlers are removed when buffering is enabled."""
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers.copy()
    original_level = root_logger.level

    stdout_handler = logging.StreamHandler(sys.stdout)
    buffer_handler = logging.StreamHandler(io.StringIO())
    root_logger.addHandler(stdout_handler)
    root_logger.addHandler(buffer_handler)

    try:
        OutputController(
            verbosity=VerbosityLevel.MINIMAL,
            enable_buffering=True,
        )

        assert stdout_handler not in root_logger.handlers
        assert buffer_handler in root_logger.handlers
    finally:
        root_logger.handlers = original_handlers
        root_logger.setLevel(original_level)
