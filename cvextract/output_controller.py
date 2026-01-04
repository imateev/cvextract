"""
Centralized, deterministic console output controller.

Provides per-file output isolation, atomic flush semantics, and
third-party output suppression for parallel execution.

Key features:
- Per-file output buffering (no interleaving)
- Atomic flush when file processing completes
- Verbosity-based filtering (minimal, verbose, debug)
- Third-party library output capture/suppression
- Thread-safe operation
- Works as a logging handler to avoid changing business logic
"""

from __future__ import annotations

import logging
import sys
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional


class VerbosityLevel(Enum):
    """Output verbosity levels."""
    MINIMAL = "minimal"  # One line per file with icons, no third-party output
    VERBOSE = "verbose"  # Grouped per-file output with warnings and major steps
    DEBUG = "debug"      # Full output including third-party logs


@dataclass
class FileOutputBuffer:
    """Buffer for output associated with a single file."""
    file_path: Path
    lines: List[str] = field(default_factory=list)
    
    def add_line(self, line: str) -> None:
        """Add a line to the buffer."""
        self.lines.append(line)
    
    def get_output(self) -> str:
        """Get all buffered output as a single string."""
        return "\n".join(self.lines) if self.lines else ""


class BufferingLogHandler(logging.Handler):
    """
    Custom logging handler that buffers log messages per file.
    
    Used in parallel mode to capture output for each file separately
    and emit it atomically when the file completes processing.
    """
    
    def __init__(self, verbosity: VerbosityLevel):
        super().__init__()
        self.verbosity = verbosity
        self._buffers: dict[Path, FileOutputBuffer] = {}
        self._lock = threading.Lock()
        self._thread_local = threading.local()
    
    def set_current_file(self, file_path: Optional[Path]) -> None:
        """Set the current file being processed in this thread."""
        self._thread_local.current_file = file_path
        
        if file_path and file_path not in self._buffers:
            with self._lock:
                if file_path not in self._buffers:
                    self._buffers[file_path] = FileOutputBuffer(file_path)
    
    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record."""
        try:
            # Skip output from third-party libraries in minimal mode
            if self.verbosity == VerbosityLevel.MINIMAL:
                if record.name.startswith(('openai', 'httpx', 'httpcore', 'urllib3', 'requests')):
                    return
            
            # Get current file context
            current_file = getattr(self._thread_local, 'current_file', None)
            
            if current_file is None:
                # No file context, skip (will be handled by other handlers)
                return
            
            # Format the message
            message = self.format(record)
            
            # Apply verbosity filtering
            if not self._should_output(record):
                return
            
            # Add to buffer
            with self._lock:
                if current_file in self._buffers:
                    self._buffers[current_file].add_line(message)
        
        except Exception:
            self.handleError(record)
    
    def _should_output(self, record: logging.LogRecord) -> bool:
        """Determine if a record should be output based on verbosity."""
        if self.verbosity == VerbosityLevel.MINIMAL:
            # In minimal mode, buffer is discarded anyway, so suppress most output
            return False
        elif self.verbosity == VerbosityLevel.VERBOSE:
            # In verbose mode, show info, warning, error (suppress debug)
            return record.levelno >= logging.INFO
        else:  # DEBUG
            # In debug mode, show everything
            return True
    
    def flush_file(self, file_path: Path, summary_line: str) -> None:
        """
        Flush buffered output for a file atomically.
        
        Args:
            file_path: Path of the file to flush
            summary_line: One-line summary to output
        """
        with self._lock:
            buffer = self._buffers.get(file_path)
            
            if self.verbosity == VerbosityLevel.MINIMAL:
                # Minimal mode: only output summary line
                print(summary_line, flush=True)
            elif buffer and buffer.lines:
                # Verbose/Debug mode: output all buffered content
                output = buffer.get_output()
                if output:
                    print(output, flush=True)
                # Then output summary line
                print(summary_line, flush=True)
            else:
                # No buffered content, just output summary
                print(summary_line, flush=True)
            
            # Clean up buffer
            if file_path in self._buffers:
                del self._buffers[file_path]


class OutputController:
    """
    Centralized controller for all console output.
    
    Ensures deterministic, non-interleaved output in parallel execution
    by buffering output per file and flushing atomically when complete.
    """
    
    def __init__(
        self,
        verbosity: VerbosityLevel = VerbosityLevel.MINIMAL,
        enable_buffering: bool = False,
    ):
        """
        Initialize the output controller.
        
        Args:
            verbosity: Output verbosity level
            enable_buffering: Enable per-file buffering (for parallel mode)
        """
        self.verbosity = verbosity
        self.enable_buffering = enable_buffering
        self._handler: Optional[BufferingLogHandler] = None
        self._removed_console_handlers: List[logging.Handler] = []
        
        if enable_buffering:
            # Create and install buffering handler
            self._handler = BufferingLogHandler(verbosity)
            self._handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
            
            # Get cvextract logger
            logger = logging.getLogger("cvextract")
            
            # Remove console handlers to prevent double output
            # (buffering controller will handle console output)
            for handler in logger.handlers[:]:
                if isinstance(handler, logging.StreamHandler) and handler.stream in (sys.stdout, sys.stderr):
                    logger.removeHandler(handler)
                    self._removed_console_handlers.append(handler)

            # Remove root console handlers to prevent propagation bypassing buffering.
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                if isinstance(handler, logging.StreamHandler) and handler.stream in (sys.stdout, sys.stderr):
                    root_logger.removeHandler(handler)
                    self._removed_console_handlers.append(handler)
            
            # Install buffering handler
            logger.addHandler(self._handler)
            
            # Also suppress third-party loggers in minimal mode
            if verbosity == VerbosityLevel.MINIMAL:
                self._suppress_third_party_loggers()
    
    def _suppress_third_party_loggers(self) -> None:
        """Suppress third-party library loggers."""
        third_party_loggers = [
            'openai',
            'httpx',
            'httpcore',
            'requests',
            'urllib3',
        ]
        
        for logger_name in third_party_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.CRITICAL + 1)  # Effectively silence
    
    @contextmanager
    def file_context(self, file_path: Path):
        """
        Context manager for processing a file.
        
        All output emitted within this context is associated with the file
        and buffered if buffering is enabled.
        
        Args:
            file_path: Path of the file being processed
        """
        if self._handler:
            self._handler.set_current_file(file_path)
        
        try:
            yield
        finally:
            if self._handler:
                self._handler.set_current_file(None)
    
    def flush_file(self, file_path: Path, summary_line: str) -> None:
        """
        Flush buffered output for a file atomically.
        
        Args:
            file_path: Path of the file to flush
            summary_line: One-line summary to output
        """
        if self._handler:
            self._handler.flush_file(file_path, summary_line)
        else:
            # No buffering, just print summary
            print(summary_line, flush=True)
    
    def direct_print(self, message: str) -> None:
        """
        Print a message directly without buffering or filtering.
        
        Used for immediate output like progress indicators or summaries.
        
        Args:
            message: Message to print
        """
        print(message, flush=True)


# Global output controller instance
_controller: Optional[OutputController] = None
_controller_lock = threading.Lock()


def get_output_controller() -> OutputController:
    """
    Get the global output controller instance.
    
    Returns:
        The global OutputController instance
    """
    global _controller
    if _controller is None:
        with _controller_lock:
            if _controller is None:
                _controller = OutputController()
    return _controller


def initialize_output_controller(
    verbosity: VerbosityLevel = VerbosityLevel.MINIMAL,
    enable_buffering: bool = False,
) -> OutputController:
    """
    Initialize the global output controller.
    
    Args:
        verbosity: Output verbosity level
        enable_buffering: Enable per-file buffering
    
    Returns:
        The initialized OutputController instance
    """
    global _controller
    with _controller_lock:
        _controller = OutputController(
            verbosity=verbosity,
            enable_buffering=enable_buffering,
        )
    return _controller
