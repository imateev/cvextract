"""
Base interface for CV renderers.

Defines the contract for pluggable CV rendering implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict


class CVRenderer(ABC):
    """
    Abstract base class for CV renderers.
    
    Implementations of this interface can render CV data to various output formats
    using different templates or rendering engines.
    """

    @abstractmethod
    def render(self, cv_data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
        """
        Render CV data to an output file using the specified template.

        Args:
            cv_data: Dictionary containing the CV data conforming to cv_schema.json
                Structure:
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
                            "environment": Optional[List[str]]
                        }
                    ]
                }
            template_path: Path to the template file to use for rendering
            output_path: Path where the rendered output should be saved

        Returns:
            Path to the rendered output file

        Raises:
            FileNotFoundError: If the template file does not exist
            Exception: For rendering-specific errors
        """
        pass
