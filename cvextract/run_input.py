"""
Run input object for internal pipeline processing.

This module defines the RunInput dataclass that encapsulates the workflow
input file path and positions for future metadata enrichment.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class RunInput:
    """
    Internal representation of a workflow input file.
    
    Encapsulates the file path and positions for future metadata enrichment
    (e.g., timestamps, source context, per-file options) without changing
    the public CLI interface.
    
    This class is immutable. Use the with_* methods to create updated copies.
    
    Attributes:
        file_path: Path to the workflow input file
        extracted_json_path: Path to extracted JSON (set by extract stage)
        adjusted_json_path: Path to adjusted JSON (set by adjust stage)
        rendered_docx_path: Path to rendered DOCX (set by apply stage)
        metadata: Additional metadata for future extensibility
    """
    file_path: Path
    extracted_json_path: Optional[Path] = None
    adjusted_json_path: Optional[Path] = None
    rendered_docx_path: Optional[Path] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_path(cls, path: Path) -> RunInput:
        """
        Construct a RunInput from a Path object.
        
        Args:
            path: Path to the workflow input file
            
        Returns:
            RunInput instance
        """
        return cls(file_path=path)
    
    def get_current_json_path(self) -> Optional[Path]:
        """
        Get the current JSON path for this run.
        
        Prefers adjusted_json_path if set, otherwise returns extracted_json_path.
        
        Returns:
            Path to the current JSON file, or None if no JSON has been produced yet
        """
        return self.adjusted_json_path if self.adjusted_json_path else self.extracted_json_path
    
    def with_extracted_json(self, path: Path) -> RunInput:
        """
        Create a new RunInput with extracted_json_path set.
        
        Args:
            path: Path to the extracted JSON file
            
        Returns:
            New RunInput instance with extracted_json_path set
        """
        return replace(self, extracted_json_path=path)
    
    def with_adjusted_json(self, path: Path) -> RunInput:
        """
        Create a new RunInput with adjusted_json_path set.
        
        Args:
            path: Path to the adjusted JSON file
            
        Returns:
            New RunInput instance with adjusted_json_path set
        """
        return replace(self, adjusted_json_path=path)
    
    def with_rendered_docx(self, path: Path) -> RunInput:
        """
        Create a new RunInput with rendered_docx_path set.
        
        Args:
            path: Path to the rendered DOCX file
            
        Returns:
            New RunInput instance with rendered_docx_path set
        """
        return replace(self, rendered_docx_path=path)
