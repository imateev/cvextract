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
    
    This class is immutable - all update methods return new instances.
    
    Attributes:
        file_path: Path to the workflow input file
        extracted_json_path: Path to extracted JSON (set by extract stage)
        adjusted_json_path: Path to adjusted JSON (set by adjust stage)
        rendered_docx_path: Path to rendered DOCX (set by apply stage)
        metadata: Dictionary for future extensibility
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
        Get the most recent JSON path in the pipeline.
        
        Returns adjusted_json_path if set, otherwise extracted_json_path.
        This allows downstream stages to work with the latest JSON output.
        
        Returns:
            Path to the current JSON file, or None if no extraction has occurred
        """
        if self.adjusted_json_path is not None:
            return self.adjusted_json_path
        return self.extracted_json_path
    
    def with_extracted_json(self, json_path: Path) -> RunInput:
        """
        Create a new RunInput with extracted JSON path set.
        
        Args:
            json_path: Path to the extracted JSON file
            
        Returns:
            New RunInput instance with extracted_json_path set
        """
        return replace(self, extracted_json_path=json_path)
    
    def with_adjusted_json(self, json_path: Path) -> RunInput:
        """
        Create a new RunInput with adjusted JSON path set.
        
        Args:
            json_path: Path to the adjusted JSON file
            
        Returns:
            New RunInput instance with adjusted_json_path set
        """
        return replace(self, adjusted_json_path=json_path)
    
    def with_rendered_docx(self, docx_path: Path) -> RunInput:
        """
        Create a new RunInput with rendered DOCX path set.
        
        Args:
            docx_path: Path to the rendered DOCX file
            
        Returns:
            New RunInput instance with rendered_docx_path set
        """
        return replace(self, rendered_docx_path=docx_path)
    
    def with_metadata(self, **kwargs) -> RunInput:
        """
        Create a new RunInput with additional metadata.
        
        Args:
            **kwargs: Key-value pairs to add to metadata
            
        Returns:
            New RunInput instance with updated metadata
        """
        new_metadata = {**self.metadata, **kwargs}
        return replace(self, metadata=new_metadata)
