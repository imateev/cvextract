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
"""

from __future__ import annotations

import io
import logging
import sys
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, TextIO


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
        self._buffers: dict[Path, FileOutputBuffer] = {}
        self._lock = threading.Lock()
        self._current_file: Optional[Path] = None
        self._thread_local = threading.local()
    
    @contextmanager
    def file_context(self, file_path: Path):
        """
        Context manager for processing a file.
        
        All output emitted within this context is associated with the file
        and buffered if buffering is enabled.
        
        Args:
            file_path: Path of the file being processed
        """
        # Store file path in thread-local storage
        previous_file = getattr(self._thread_local, 'current_file', None)
        self._thread_local.current_file = file_path
        
        try:
            # Create buffer if buffering is enabled
            if self.enable_buffering:
                with self._lock:
                    if file_path not in self._buffers:
                        self._buffers[file_path] = FileOutputBuffer(file_path)
            yield
        finally:
            # Restore previous file context
            self._thread_local.current_file = previous_file
    
    def log(self, level: str, message: str, *args, **kwargs) -> None:
        """
        Log a message through the controller.
        
        Args:
            level: Log level (info, warning, error, debug)
            message: Message format string
            *args: Format arguments
            **kwargs: Additional keyword arguments
        """
        # Format the message
        if args:
            try:
                formatted_message = message % args
            except (TypeError, ValueError):
                formatted_message = message
        else:
            formatted_message = message
        
        # Apply verbosity filtering
        if not self._should_output(level):
            return
        
        # Get current file context
        current_file = getattr(self._thread_local, 'current_file', None)
        
        # Add to buffer if buffering is enabled and we have a file context
        if self.enable_buffering and current_file:
            with self._lock:
                if current_file in self._buffers:
                    self._buffers[current_file].add_line(formatted_message)
            return
        
        # Otherwise, output immediately to console
        self._write_to_console(level, formatted_message)
    
    def flush_file(self, file_path: Path, summary_line: str) -> None:
        """
        Flush buffered output for a file atomically.
        
        In minimal mode, only the summary line is output.
        In verbose/debug mode, all buffered output is followed by the summary.
        
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
    
    def _should_output(self, level: str) -> bool:
        """
        Determine if a message at the given level should be output.
        
        Args:
            level: Log level (info, warning, error, debug)
        
        Returns:
            True if the message should be output
        """
        level_lower = level.lower()
        
        if self.verbosity == VerbosityLevel.MINIMAL:
            # In minimal mode, suppress most output when buffering
            # (buffered output is discarded, only summary is shown)
            if self.enable_buffering:
                return False
            # When not buffering (single file mode), allow errors and warnings
            return level_lower in ('error', 'warning')
        
        elif self.verbosity == VerbosityLevel.VERBOSE:
            # In verbose mode, show info, warning, error (suppress debug)
            return level_lower in ('info', 'warning', 'error')
        
        else:  # DEBUG
            # In debug mode, show everything
            return True
    
    def _write_to_console(self, level: str, message: str) -> None:
        """
        Write a message directly to the console.
        
        Args:
            level: Log level
            message: Formatted message
        """
        # Use logging to maintain consistent format
        logger = logging.getLogger("cvextract")
        level_lower = level.lower()
        
        if level_lower == 'debug':
            logger.debug(message)
        elif level_lower == 'info':
            logger.info(message)
        elif level_lower == 'warning':
            logger.warning(message)
        elif level_lower == 'error':
            logger.error(message)
        else:
            logger.info(message)
    
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


@contextmanager
def suppress_third_party_output(verbosity: VerbosityLevel):
    """
    Context manager to suppress third-party library output.
    
    Captures and suppresses stdout/stderr and third-party logging
    based on verbosity level.
    
    Args:
        verbosity: Current verbosity level
    """
    if verbosity == VerbosityLevel.MINIMAL:
        # Suppress all third-party output in minimal mode
        
        # Save original stdout/stderr
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        
        # Redirect to null
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        
        # Suppress third-party library loggers
        third_party_loggers = [
            'openai',
            'httpx',
            'httpcore',
            'requests',
            'urllib3',
        ]
        
        original_levels = {}
        for logger_name in third_party_loggers:
            logger = logging.getLogger(logger_name)
            original_levels[logger_name] = logger.level
            logger.setLevel(logging.CRITICAL + 1)  # Effectively silence
        
        try:
            yield
        finally:
            # Restore stdout/stderr
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            
            # Restore logger levels
            for logger_name, level in original_levels.items():
                logging.getLogger(logger_name).setLevel(level)
    else:
        # In verbose/debug mode, allow third-party output
        yield
