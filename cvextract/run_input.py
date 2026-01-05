"""
Run input object for internal pipeline processing.

This module defines the RunInput dataclass that encapsulates the workflow
input file path and positions for future metadata enrichment.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class RunInput:
    """
    Internal representation of a workflow input file.
    
    Encapsulates the file path and positions for future metadata enrichment
    (e.g., timestamps, source context, per-file options) without changing
    the public CLI interface.
    
    Attributes:
        file_path: Path to the workflow input file
    """
    file_path: Path
    
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
