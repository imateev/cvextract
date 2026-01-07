"""
DOCX-based CV extractor implementation.

Extracts structured CV data from Word .docx files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .base import CVExtractor
from .body_parser import parse_cv_from_docx_body
from .sidebar_parser import extract_all_header_paragraphs, split_identity_and_sidebar


class DocxCVExtractor(CVExtractor):
    """
    CV extractor for Microsoft Word .docx files.

    This implementation:
    - Parses Word documents as ZIP archives
    - Extracts header/sidebar content from text boxes
    - Parses the main body for overview and experience sections
    - Returns structured data conforming to the CV schema
    """

    def extract(self, source: Path) -> Dict[str, Any]:
        """
        Extract structured CV data from a .docx file.

        Args:
            source: Path to the .docx file

        Returns:
            Dictionary with extracted CV data (identity, sidebar, overview, experiences)

        Raises:
            FileNotFoundError: If the .docx file does not exist
            Exception: For parsing or extraction errors
        """
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        if not source.is_file() or source.suffix.lower() != ".docx":
            raise ValueError(f"Source must be a .docx file: {source}")

        # Extract body content (overview and experiences)
        overview, experiences = parse_cv_from_docx_body(source)

        # Extract header content (identity and sidebar)
        header_paragraphs = extract_all_header_paragraphs(source)
        identity, sidebar = split_identity_and_sidebar(header_paragraphs)

        return {
            "identity": identity.as_dict(),
            "sidebar": sidebar,
            "overview": overview,
            "experiences": experiences,
        }
