"""
Base interface for CV extractors.

Defines the contract for pluggable CV extraction implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict


class CVExtractor(ABC):
    """
    Abstract base class for CV extractors.
    
    Implementations of this interface can extract structured CV data
    from various input formats and return a standardized dictionary
    conforming to the CV schema.
    """

    @abstractmethod
    def extract(self, source: Path) -> Dict[str, Any]:
        """
        Extract structured CV data from the given source.

        Args:
            source: Path to the source document/file to extract from

        Returns:
            A dictionary containing the extracted CV data with the following structure:
            {
                "identity": {
                    "title": str,
                    "full_name": str,
                    "first_name": str,
                    "last_name": str
                },
                "sidebar": {
                    "languages": List[str],
                    "tools": List[str],
                    "certifications": List[str],
                    "industries": List[str],
                    "spoken_languages": List[str],
                    "academic_background": List[str]
                },
                "overview": str,
                "experiences": [
                    {
                        "heading": str,
                        "description": str,
                        "bullets": List[str],
                        "environment": List[str] | None
                    }
                ]
            }

        Raises:
            FileNotFoundError: If the source file does not exist
            Exception: For extraction-specific errors
        """
        pass
