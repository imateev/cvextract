"""
Run input object for internal pipeline processing.

This module defines the RunInput dataclass that encapsulates the complete
per-file workflow state including all input and output paths, as well as
any errors and warnings encountered during processing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class RunInput:
    """
    Internal representation of a complete per-file workflow state.
    
    Encapsulates all file paths required and produced by the workflow,
    with each stage reading its required inputs from RunInput and recording
    its outputs back into it. Also tracks errors and warnings for diagnostics.
    
    Each RunInput instance is created per input file and is used exclusively
    for work related to that file.
    
    Attributes:
        file_path: Path to the original workflow input file
        extracted_json_path: Path to extracted JSON output (set by extract stage)
        adjusted_json_path: Path to adjusted JSON output (set by adjust stage)
        rendered_output_path: Path to final rendered document (set by render stage)
        errors: List of error messages encountered during processing
        warnings: List of warning messages encountered during processing
    """
    file_path: Path
    extracted_json_path: Optional[Path] = None
    adjusted_json_path: Optional[Path] = None
    rendered_output_path: Optional[Path] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @classmethod
    def from_path(cls, path: Path) -> RunInput:
        """
        Construct a RunInput from a Path object.
        
        Args:
            path: Path to the workflow input file
            
        Returns:
            RunInput instance with only file_path set
        """
        return cls(file_path=path)
    
    def add_error(self, error: str) -> None:
        """
        Add an error message to this run.
        
        Args:
            error: Error message to record
        """
        self.errors.append(error)
    
    def add_warning(self, warning: str) -> None:
        """
        Add a warning message to this run.
        
        Args:
            warning: Warning message to record
        """
        self.warnings.append(warning)
    
    def has_errors(self) -> bool:
        """Check if any errors have been recorded."""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if any warnings have been recorded."""
        return len(self.warnings) > 0
